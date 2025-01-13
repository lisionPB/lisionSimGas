"""
@author: paulb
"""

# PyQt5 - Bibliotheken für Threading und Signals
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QTimer

import time
import math
import json

class GasGardSetup(QObject):
    """
    Klasse zur Verwaltung von Messkomponenten
    
    Verwende _zuweisen_Port(self, name, p) um Messkomponenten hinzuzufügen
    Verwende _connect_Ports(self) um Verbindung zu Ports herzusstellen
    Verwende _start_MessSchleife(self) um Messschleife zu starten
    """
    
    DEFAULT_SCAN_INTERVAL = 250
       
    CONFIG_FILE_SENSOREN = "config_gasgard.json"
    
    GG_CONNECT_STATUS_NONE = -1     # Verbindung zu keinem COM-Port aufgebaut
    GG_CONNECT_STATUS_OK = 1        # Verbindungen zu allen Ports hergestellt.
    
    _sig_NewSecData = pyqtSignal(dict)
    _sig_GG_SetupConnect = pyqtSignal()
    sig_GG_ConnectFinished = pyqtSignal(int)
    
    sig_closeConnection = pyqtSignal()
    
    
    def __init__(self, ggEA):
        super().__init__()
                
        self._ggEA = ggEA   
        
        self._ggConnectStatus = self.GG_CONNECT_STATUS_NONE
        
        # Übergeben der Sensormessbereiche
        self._ggEA.setSensorBereiche(self._load_sensorConfig(self.CONFIG_FILE_SENSOREN))
        
        # Init Flaschendruck Data
        self.dataGas = {}
        for f in self._ggEA._sensors:
            self.dataGas[f] = {'value': None}
        
        ##############
        # Messschleife
        
        self._interval = self.DEFAULT_SCAN_INTERVAL
        
        self._threadMessLoop = QThread()
        self._worker = GG_UpdateWorker(self, self._interval)
        self._worker.moveToThread(self._threadMessLoop)
        
        self._threadMessLoop.started.connect(self._worker._start_worker)
        self._worker._sig_finished.connect(self._threadMessLoop.quit)
        self._worker._sig_finished.connect(self._worker.deleteLater)
        self._threadMessLoop.finished.connect(self._threadMessLoop.deleteLater)
        
        self.sig_closeConnection.connect(self._worker._stop_worker)
                        
        ####
        
        self.hct = GG_ConnectThread(self)
        self._sig_GG_SetupConnect.connect(self.hct.start)
        self._update_GGSetupInProgress = False
        
        ####
        
        self.closing = False


    def _load_sensorConfig(self, confFileURL):
        """
        Liest Sensor-Konfiguration aus json-File
        """
        
        f = open(confFileURL)
        conf = json.load(f)
        
        # Auslesen der Messbereiche der Sensoren
        sensors = conf           
        f.close()
        
        return sensors


    def save_sensorConfig(self):       
        with open(self.CONFIG_FILE_SENSOREN, "w") as outfile:
            json.dump(self._ggEA._sensors, outfile, indent=4)
            
        print ("GasGard Sensor-Konfiguration gespeichert.")

        
            
    def _start_MessSchleife(self):
        if(self._ggConnectStatus == self.GG_CONNECT_STATUS_OK):
            self._threadMessLoop.start()
        else:
            print ("Warte auf Verbindung zur GasGard Harware...")    

                    
    def _connect_gg(self):
        if(not self._update_GGSetupInProgress):
            self._sig_GG_SetupConnect.emit()
            
                
        
    def _read_Messwerte(self):
        
        # Versuche Verbindung neu aufzubauen, wenn Fehler vorliegt:
        if(self._ggConnectStatus != self.GG_CONNECT_STATUS_OK):
            self._connect_gg()
                
        # Wenn Verbindung OK: Lesen der Sensoren
        if(self._ggConnectStatus == self.GG_CONNECT_STATUS_OK):
            # Vordruck
            
            try:
                
                ###
                vals = self._ggEA.readDigitalInput()
                print("ggs: read GG: " + str(vals))
                
                for f in self.dataGas:
                    self.dataGas[f]["value"] = vals
                
                if(err):
                    raise Exception("Fehler beim Auslesen der GasGard Sensoren!")
                
                
            except Exception as e:
                # Fehler beim Auslesen des Messwertes
                print (e)
                print ("GG: Fehler beim Auslesen des Messwertes!")
                self._ggConnectStatus = self.GG_CONNECT_STATUS_NONE
            
            val = "---"
            try:
                val = float(msg)
            except:
                pass
            self.data = val
            
            return self.data              
    
           


    def get_Messwerte(self):
        return self.data


    def _close_ggSetup(self):
    
        self.closing = True
    
        # Update Thread beenden    
        self.sig_closeConnection.emit()
        
        self.terminated = True
        print("Verbindung zu GasGard getrennt.")
            
            
            
            
###########################################################################################################
# 
# Helferklassen           

class GG_UpdateWorker(QObject):
    """
    Enthält den Haupttask zum Update des GasGard Setup
    """
    _sig_finished = pyqtSignal()
    _sig_progress = pyqtSignal(int)
    
    def __init__(self, ggSetup, interval):
        super(GG_UpdateWorker, self).__init__()
        self._ggSetup = ggSetup
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
            self._ggSetup._read_Messwerte()
                
            self._processing = False




class GG_ConnectThread(QThread):
    
    _sig_finished = pyqtSignal()
    
    def __init__(self, ggSetup):
        QThread.__init__(self)
        self.ggs = ggSetup
           
        
    def run(self):
                
        lastStatus = self.ggs._ggConnectStatus
                
        if(not self.ggs._update_ggSetupInProcess):
        
            print ("Verbinde GasGard Setup ...")
    
            self.ggs._update_GGSetupInProgress = True         
            
            self.ggs._ggConnectStatus = GasGardSetup.GG_CONNECT_STATUS_NONE # Noch kein COM-Port wurde verbunden      

            if(self.ggs._ggEA.connect() == True):
                self.ggs._ggConnectStatus = GasGardSetup.GG_CONNECT_STATUS_OK # Alle COM-Ports wurden verbunden

            self.ggs._update_GGSetupInProgress = False
            
            if(self.ggs._ggConnectStatus != lastStatus):
                self.ggs.sig_GG_ConnectFinished.emit(self.ggs._ggConnectStatus)
                
            # Neuen Verbindungsversuch starten, wenn vorheriger fehlschlägt
            if(self.ggs._ggConnectStatus != GasGardSetup.GG_CONNECT_STATUS_OK and not self.ggs.closing):
                self.ggs._sig_GG_SetupConnect.emit()