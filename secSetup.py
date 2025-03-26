# -*- coding: utf-8 -*-
"""
Created on Mon Jan 16 18:51:37 2023

v 2.2.1 (Max Counter for close all)

@author: paulb
"""


# PyQt5 - Bibliotheken für Threading und Signals
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QTimer

import time
import math
import json

class SecSetup(QObject):
    """
    Klasse zur Verwaltung von Messkomponenten
    
    Verwende _zuweisen_Port(self, name, p) um Messkomponenten hinzuzufügen
    Verwende _connect_Ports(self) um Verbindung zu Ports herzusstellen
    Verwende _start_MessSchleife(self) um Messschleife zu starten
    """
    
    
    TIMEOUT_DISABLE_MSG = 10     # Timeout für Verbindungsherstellung vor Deaktivierung [s]
    
    DEFAULT_SCAN_INTERVAL = 250
    
    SEC_CONNECT_STATUS_NONE = -1     # Verbindung zu keinem COM-Port aufgebaut
    SEC_CONNECT_STATUS_OK = 1        # Verbindungen zu allen Ports hergestellt.
       
    CONFIG_FILE_SENSOREN = "config_sensors.json"
    CONFIG_FILE_SENSOREN_MGS = "config_mgs.json"
    CONFIG_FILE_ZUSCHALTGRENZEN = "config_zuschaltgrenzen.json"
    
    _sig_NewSecData = pyqtSignal(dict)
    _sig_SEC_SetupConnect = pyqtSignal()
    sig_SEC_ConnectFinished = pyqtSignal(int)
    _sig_disableMGS = pyqtSignal(int)
    
    sig_closeConnection = pyqtSignal()
    
    
    def __init__(self, sgEA):
        super().__init__()
                
        self._sgEA = sgEA   
        
        self._secConnectStatus = self.SEC_CONNECT_STATUS_NONE
        
        
        # Übergeben der Sensormessbereiche
        self._sgEA.setSensorBereiche(self._load_sensorConfig(self.CONFIG_FILE_SENSOREN))
        self._sgEA.setMGSSensorBereiche(self._load_sensorConfig(self.CONFIG_FILE_SENSOREN_MGS))
        
        # Zuschaltsicherheitsbereiche für Flaschendruck
        self.zuschaltGrenzwerte = self.load_zuschaltungsGrenzwertConfig(self.CONFIG_FILE_ZUSCHALTGRENZEN)
        
        # Init Flaschendruck Data
        self.dataGas = {}
        self.zuschaltung = {}
        for f in self._sgEA._sensors:
            self.dataGas[f] = {"FP" : None, "TP" : None}
            self.zuschaltung[f] = False
            
            
        # Init MGS Boxen Data
        
        self.mgsConnectStartTime = {}
        self.enableMGSBoxen = {} 
        self.dataMGS = {}
        for s in self._sgEA._sensorsMGS:
            self.dataMGS[s] = 0
            self.mgsConnectStartTime[self._sgEA._sensorsMGS[s]["box"]] = time.time()
            self.enableMGSBoxen[self._sgEA._sensorsMGS[s]["box"]] = True
        

        
        ##############
        # Status
        # Magnet Switches
        self._sms_open = {}
        for s in self._sgEA._sensors:
            self._sms_open[s] = False

        
        ##############
        # Messschleife
        
        self._interval = self.DEFAULT_SCAN_INTERVAL
        
        self._threadMessLoop = QThread()
        self._worker = SEC_UpdateWorker(self, self._interval)
        self._worker.moveToThread(self._threadMessLoop)
        
        self._threadMessLoop.started.connect(self._worker._start_worker)
        self._worker._sig_finished.connect(self._threadMessLoop.quit)
        self._worker._sig_finished.connect(self._worker.deleteLater)
        self._threadMessLoop.finished.connect(self._threadMessLoop.deleteLater)
        
        self.sig_closeConnection.connect(self._worker._stop_worker)
                        
        ####
        
        self.htc = SEC_ConnectThread(self)
        self._sig_SEC_SetupConnect.connect(self.htc.start)
        self._update_SECSetupInProcess = False
        
        ####
        
        self.closing = False


    def _load_sensorConfig(self, confFileURL):
        """
        Liest Sensor-Konfiguration aus json-File
        """
        # TODO: Ausnahmebehandlung, wenn Config File nicht gefunden wurde oder File ungültiges Format hat!
        
        # Gas Vordruck Sensoren
        f = open(confFileURL)
        conf = json.load(f)
        
        # Auslesen der Messbereiche der Sensoren
        sensors = conf           
        f.close()
        
        return sensors



    def save_sensorConfig(self):    
           
        # Gas Flaschen Sensorik
        with open(self.CONFIG_FILE_SENSOREN, "w") as outfile:
            json.dump(self._sgEA._sensors, outfile, indent=4)
            
        # MGS Boxen Sensorik
        with open(self.CONFIG_FILE_SENSOREN_MGS, "w") as outfile:
            json.dump(self._sgEA._sensorsMGS, outfile, indent=4)
            
        print ("SEC Sensor-Konfiguration gespeichert.")


    def load_zuschaltungsGrenzwertConfig(self, configFileURL):
        f = open(configFileURL)
        conf = json.load(f)
              
        f.close()
        
        return conf
    
    
    def save_zuschaltungsGrenzwertConfig(self):
        # Gas Flaschen Grenzwerte
        with open(self.CONFIG_FILE_ZUSCHALTGRENZEN, "w") as outfile:
            json.dump(self.zuschaltGrenzwerte, outfile, indent=4)
            
        print ("Konfiguration der Zuschalt-Grenzwerte gespeichert.")
        
            
    def _start_MessSchleife(self):
        if(self._secConnectStatus == self.SEC_CONNECT_STATUS_OK):
            self._threadMessLoop.start()
        else:
            print ("Warte auf Verbindung zur SEC-Harware...")    

                    
    def _connect_sec(self):
        if(not self._update_SECSetupInProcess):
            self._sig_SEC_SetupConnect.emit()
            
                
        
    def _read_Messwerte(self):
        data = {}
        data.update(self.__read_Vordruck())
        data.update(self.__read_MGSBoxen())
        
        if(len(data) > 0):
            self._sig_NewSecData.emit(data)

            

    def __read_Vordruck(self):
        
        data = {}
        
        # Versuche Verbindung neu aufzubauen, wenn Fehler vorliegt:
        if(self._secConnectStatus != self.SEC_CONNECT_STATUS_OK):
            self._connect_sec()           
                
        if(self._secConnectStatus == self.SEC_CONNECT_STATUS_OK):
            
            # Vordruck
            try:
                                
                ###
                for f in self.dataGas:
                    err2, fp = self._sgEA.readAnalogInputVordruck(f)
                    self.dataGas[f]["FP"] = fp
                    data[f] = fp
                    
                    # Berechnung GasTemp:
                    if(type(fp) != None and fp != 0):
                        self.dataGas[f]["TP"] = 987.0 / ( 6.2886 - math.log10(fp*100) ) - 273.15
                
                    if(err2):
                        raise Exception("Fehler beim Auslesen des Vordrucks")
                    
                
            except Exception as e:
                # Fehler beim Auslesen des Messwertes
                print (e)
                print ("SEC: Fehler beim Auslesen des Gasvordrucks !")
                self._secConnectStatus = self.SEC_CONNECT_STATUS_NONE
                
        return data
                
                
                            

    def __read_MGSBoxen(self):
        
        data = {}
        
        # Versuche Verbindung neu aufzubauen, wenn Fehler vorliegt:
        if(self._secConnectStatus != self.SEC_CONNECT_STATUS_OK):
            self._connect_sec()
                
                
                
        if(self._secConnectStatus == self.SEC_CONNECT_STATUS_OK):
            
            # MGS Messboxen
                                
            ###
            try:
                for f in self.dataMGS:
                    # print(f"f: {f}")
                    err, val = self._sgEA.readAnalogInputMGSBox(f)
                    self.dataMGS[f] = val
                    data[f] = val
                    
                    #print(f)
                    #print(self._sgEA._sensorsMGS[f]["box"])
                    #print(self.enableMGSBoxen[self._sgEA._sensorsMGS[f]["box"]])      
                    
                    if(err and (self.enableMGSBoxen[self._sgEA._sensorsMGS[f]["box"]] == True)):
                        print("Fehler beim Auslesen von " + str(f) )
                        if(time.time() - self.mgsConnectStartTime[self._sgEA._sensorsMGS[f]["box"]] > self.TIMEOUT_DISABLE_MSG):
                            self.enableMGSBoxen[self._sgEA._sensorsMGS[f]["box"]] = False
                            print("MGS Box " + str(self._sgEA._sensorsMGS[f]["box"]) + " antwortet nicht und wird deaktiviert.")
                            self._sig_disableMGS.emit(self._sgEA._sensorsMGS[f]["box"])
                    else:
                        if(self.enableMGSBoxen[self._sgEA._sensorsMGS[f]["box"]] == True):
                            # MGS Box bleibt enabled
                            self.mgsConnectStartTime[self._sgEA._sensorsMGS[f]["box"]] = time.time()
                    
                
            except Exception as e:
                # Fehler beim Auslesen des Messwertes
                print (e)
                print ("SEC: Fehler beim Auslesen der MGS Boxen !")
                # self._secConnectStatus = self.SEC_CONNECT_STATUS_NONE
                
        return data


    def set_sms_zuschaltung(self, name, _open):
        """
        Setzt die geplante Zuschaltung für ein Gasflasche

        Args:
            name (str): as in self._sgEA._sensors
            _open (bool): True: open, False: close
        """
        
        self.zuschaltung[name] = _open


    def clear_sms_zuschaltungen(self):
        for s in self.zuschaltung:
            self.zuschaltung[s] = False


    def write_sms_zuschaltungen(self):
        """
        Überträgt die geplante Zuschaltung der Gasflaschen an die Magnetventile
        """
        for s in self.zuschaltung:
            self.set_sms_open(s, self.zuschaltung[s])


    def set_sms_open(self, name, _open):
        """
            name: wie in self.sgEA._sensors
            open (bool): True: Open, False: Closed 
        """
        self._sgEA.writeDigitalOutput(self._sgEA._sensors[name]["ventilNr"], _open)
        self._sms_open[name] = self._sgEA.isDigitalOutputSet(self._sgEA._sensors[name]["ventilNr"])
    
    
    def is_sms_open_any(self):
        for s in self._sms_open:
            if(self._sms_open[s]):
                return True
        return False
      
            
    def checkFlaschenZuschaltung(self, name, checkEigendruck=True, checkDiffDruck=True):
        """
        @return: 0: OK, 1: Eigendruck zu niedrig, 2: Differenzdruck zu groß , -1: Keine Daten vorhanden
        """
        
        # Keine Daten vorhanden
        if(not self.dataGas[name]["FP"]):
            return -1
        
        if(checkEigendruck):
            # Eigendruck
            if(self.dataGas[name]["FP"] < self.zuschaltGrenzwerte["DRUCK_MIN"]):
                return 1
        
        if(checkDiffDruck):
            # Differenzdruck 
            for s in self.dataGas:
                if(self.zuschaltung[s]):
                    if (abs(self.dataGas[s]["FP"] - self.dataGas[name]["FP"]) > self.zuschaltGrenzwerte["DIFF_MAX"]):
                        return 2    
        
        return 0
    
        
    def set_gasFlowLED(self, activ):
        self._sgEA.GASFLOWACTIVE(int(activ))



    def _close_secSetup(self):
    
        self.closing = True
    
        # close Mag Vents            
        for s in self._sgEA._sensors:
            self.set_sms_open(s, False)
    
        # Update Thread beenden    
        self.sig_closeConnection.emit()
        
        self.terminated = True
        print("SEC-Setup closed")
            
            
            
            
###########################################################################################################
# 
# Helferklassen           

class SEC_UpdateWorker(QObject):
    """
    Enthält den Haupttask zum Update des SEC-Setup
    """
    _sig_finished = pyqtSignal()
    _sig_progress = pyqtSignal(int)
    
    def __init__(self, secSetup, interval):
        super(SEC_UpdateWorker, self).__init__()
        self._secSetup = secSetup
        self._interval = interval
        self._processing = False
        self._timer = QTimer()

        
    def _start_worker(self):
        self._start_timer()
        
        
    def _stop_worker(self):
        self._timer.stop()
        self._sig_finished.emit()
        
        
    def _set_interval(self, interval):
        self._timer.disconnect()
        self._interval = interval
        
        
    def _start_timer(self):
        self._timer = QTimer()
        self._timer.setInterval(self._interval)
        self._timer.timeout.connect(self._dataUpdate)
        self._timer.start()
        

    def _dataUpdate(self):
        """
        Wenn Sensor vorhanden, wird Messung getriggert und Daten aktualisiert.
        """
        
        # Trigger Messung nur, wenn nicht gerade schon Messung läuft und HW nicht im Testmode ist.          
        if(not self._processing):
            self._processing = True		
            
            # Triggert Auslesen der Messwerte
            self._secSetup._read_Messwerte()
                
            self._processing = False




class SEC_ConnectThread(QThread):
    
    _sig_finished = pyqtSignal()
    
    
    def __init__(self, secSetup):
        QThread.__init__(self)
        self.hws = secSetup
           
        
    def run(self):
                
        lastStatus = self.hws._secConnectStatus
                
        if(not self.hws._update_SECSetupInProcess):
        
            print ("Verbinde SEC-Setup ...")
    
            self.hws._update_SECSetupInProcess = True         
            
            self.hws._secConnectStatus = SecSetup.SEC_CONNECT_STATUS_NONE # Noch kein COM-Port wurde verbunden      

            if(self.hws._sgEA.connect() == True):
                self.hws._secConnectStatus = SecSetup.SEC_CONNECT_STATUS_OK # Alle COM-Ports wurden verbunden

            self.hws._update_SECSetupInProcess = False
            
            if(self.hws._secConnectStatus != lastStatus):
                self.hws.sig_SEC_ConnectFinished.emit(self.hws._secConnectStatus)
                
            # Neuen Verbindungsversuch starten, wenn vorheriger fehlschlägt
            if(self.hws._secConnectStatus != SecSetup.SEC_CONNECT_STATUS_OK and not self.hws.closing):
                self.hws._sig_SEC_SetupConnect.emit()