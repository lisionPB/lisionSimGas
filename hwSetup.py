# -*- coding: utf-8 -*-
"""
Created on Mon Jan 16 18:51:37 2023

v 2.3.1 (Max Counter for Close All)

@author: paulb
"""


# PyQt5 - Bibliotheken für Threading und Signals
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QTimer

import time
import datamanager as dmgr

import simulation

class HWSetup(QObject):
    """
    Klasse zur Verwaltung von Messkomponenten
    
    Verwende _zuweisen_Port(self, name, p) um Messkomponenten hinzuzufügen
    Verwende _connect_Ports(self) um Verbindung zu Ports herzusstellen
    Verwende _start_MessSchleife(self) um Messschleife zu starten
    """
    
    TEST_MODE = False    # True setzen, um Verbindungstests zur Hardware zu umgehen
    EMULATION = False    # True setzen, um Virtuelle Daten zum Testen der Anzeige zu generieren
    
    DEFAULT_SCAN_INTERVAL = 1000
    
    HW_CONNECT_STATUS_NONE = -1     # Verbindung zu keinem COM-Port aufgebaut
    HW_CONNECT_STATUS_FAILURE = 0   # Verbindugn zu mindestems 1 COM-Port erfolgreich
    HW_CONNECT_STATUS_OK = 1        # Verbindungen zu allen Ports hergestellt.
    
    _sig_NewData = pyqtSignal(dict)
    _sig_HWSetupConnect = pyqtSignal()
    sig_HWConnectFinished = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        
        self._testmode = self.TEST_MODE
        
        self._hwConnectStatus = self.HW_CONNECT_STATUS_FAILURE
        
        self._ports = {}
                
        # Lade Datenmanager
        self.dm = dmgr.DataManager(self._ports)
        
        # Verbinde Receiver für neue Daten
        self._sig_NewData.connect(self.dm.append_RawData) 
        
        
        ##############
        # Messschleife
        
        self._interval = self.DEFAULT_SCAN_INTERVAL
        
        self._threadMessLoop = QThread()
        self._worker = HWUpdateWorker(self, self._interval)
        self._worker.moveToThread(self._threadMessLoop)
        
        self._threadMessLoop.started.connect(self._worker._start_worker)
        self._worker._sig_finished.connect(self._threadMessLoop.quit)
        self._worker._sig_finished.connect(self._worker.deleteLater)
        self._threadMessLoop.finished.connect(self._threadMessLoop.deleteLater)
        
        ####
        
        self.htc = HW_ConnectThread(self)
        self._sig_HWSetupConnect.connect(self.htc.start)
        self._updateHWSetupInProcess = False
        
        ###
        
        self.terminated = False
        
        # Extern Data
        self.externData = dict()
    

    def _connect_Ports(self):
        if(not self._updateHWSetupInProcess):
            self._sig_HWSetupConnect.emit()

            
    def _start_MessSchleife(self):
        self._threadMessLoop.start()
        
                
        
    def _read_Messwerte(self):
        
        #print ("---------------------------------------------v")
        if(not self._testmode):
            # Versuche Verbindung neu aufzubauen, wenn Fehler vorliegt:
            if(self._hwConnectStatus != self.HW_CONNECT_STATUS_OK):
                self._connect_Ports()
        
        if(not self.EMULATION):
        
            if(self._hwConnectStatus == self.HW_CONNECT_STATUS_OK):
                
                # Lese Messwerte aus Ports aus
                disconnectCount = 0
                data = dict()
                for p in self._ports:
                    val = self._ports[p]._read_Messwert()
                    if(val == None):
                        # Fehler beim Auslesen des Messwertes
                        print (p + ": Fehler beim Auslesen des Messwertes: val=" + str(val))
                        self._hwConnectStatus = self.HW_CONNECT_STATUS_FAILURE
                        disconnectCount = disconnectCount + 1
                    elif(val == "BUSY"):
                        # Keine Aktuellen Daten, weil busy!
                        print (p + ": Fehler beim Auslesen des Messwertes: val=" + str(val))
                        data[p] = "BUSY"
                    else: 
                        data[p] = val
                        
                        
                if (disconnectCount == len(self._ports)):
                    # Von KEINEM Port konnten Messwerte ausgelesen werden
                    print ("Fehler beim Auslesen der Messdaten: data=" + str(data))
                    self._hwConnectStatus = self.HW_CONNECT_STATUS_NONE
                    
                    #print ("---------------------------------------------^")
                    return None
                
                #print ("---------------------------------------------^")
                
                return data
        
        else:
            return self._emulate_Messwerte()
                
        
        return None
            
    
    def set_externData(self, extData):
        self.externData = extData
    
    
    def _emulate_Messwerte(self):
        
        # Generiere Messwerte
        data = dict()
        for p in self._ports:
            #data[p] = simulation.sim_flussMessung_lin(self.dm.get_currentTime(), 0.01, 40)
            data[p] = simulation.sim_flussMessung_sin(self.dm.get_currentTime(), 1, 2, 10)
            
        return data
    
    
    
    def _zuweisen_Port(self, name, p):
        #print (self._ports)
        if(not name in self._ports):
            self._ports[name] = p  
        else:
            print ("Fehler bei der Zuweisung eines Ports: Port-Name bereits vergeben!")
                        

            
    def _close_hwSetup(self):
        
        allClosed = False
        
        # Ports schließen
        cnt = 0
        while(not allClosed and cnt < 10):
            print ("Closing HW Setup ...")
            allClosed = True
            for p in self._ports:
                print ("Closing: " + str(p))
                if(not self._ports[p]._close()):
                    allClosed = False
                    cnt += 1
                    break
            time.sleep(0.1)
            
        # Update Thread beenden    
        self._worker._stop_worker()
        
        self.terminated = True
        print("HW-Setup closed")
            
            
    
    def reset(self):
        self.dm.reset()
        
        
    def set_paused(self, paused):
        self._worker._set_paused(paused)
    
    
    def is_paused(self):
        return self._worker._paused
    

    def get_datamanager(self):
        return self.dm
    
    
    
###################################################
# Aufzeichnung von Messdaten

    def start_recordData(self):
        """
        Startet das externe Aufzeichnen von Messdaten in einer Log-Datei über den DataManager
        """
        
        self.dm.start_recordData()
                
            
            
    def stop_recordData(self):
        """
        Stoppt das externe Aufzeichnen von Messdaten in einer Log-Datei über den DataManager
        """
        
        self.dm.stop_recordData()

            
            
            
###########################################################################################################
# 
# Helferklassen           

class HWUpdateWorker(QObject):
    """
    Enthält den Haupttask zum Update der Messungen
    """
    _sig_finished = pyqtSignal()
    _sig_progress = pyqtSignal(int)
    
    def __init__(self, hwSetup, interval):
        super(HWUpdateWorker, self).__init__()
        self._hwSetup = hwSetup
        self._interval = interval
        self._readingData = False
        self._timer = QTimer()
        
        self._paused = False
        
        
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
        
    def _set_paused(self, paused):
        self._paused = int(paused)
        

    def _dataUpdate(self):
        """
        Wenn Sensor vorhanden, wird Messung getriggert und Daten aktualisiert.
        """
        
        # Trigger Messung nur, wenn nicht gerade schon Messung läuft und HW nicht im Testmode ist.          
        if(not self._readingData and not self._paused == 2):
            
            # Führe nach Befehl zum Pausieren letzte Messung durch
            if(self._paused == 1):
                self._paused = 2
                
            self._readingData = True		
            
            # Triggert Auslesen der Messwerte
            data = self._hwSetup._read_Messwerte()
    
            if(data != None):
                # Messung abgeschlossen
                self._readingData = False
                # Mappen der Daten auf Kanäle
                self._hwSetup._sig_NewData.emit(data)

                #print ("update HW: " + str(int(QThread().currentThread().currentThreadId())))
            else:
                print ("Data Update: Fehler beim Auslesen der Messungen!")
                self._readingData = False



class HW_ConnectThread(QThread):
    
    _sig_finished = pyqtSignal()
    
    def __init__(self, hwSetup):
        QThread.__init__(self)
        self.hws = hwSetup
        
    def run(self):
                
        lastStatus = self.hws._hwConnectStatus
                
        if(not self.hws._updateHWSetupInProcess):
        
            print ("connect HW")
    
            self.hws._updateHWSetupInProcess = True
                
            status = -1
            connected = 0
            self.hws._hwConnectStatus = HWSetup.HW_CONNECT_STATUS_NONE # Noch kein COM-Port wurde verbunden
            for p in self.hws._ports:
                #  print (self.hws._ports)
                if(self.hws._ports[p]._connect()):
                    connected += 1
                    self.hws._hwConnectStatus = HWSetup.HW_CONNECT_STATUS_FAILURE # Zumindest 1 COM-Port wurde verbunden
            if(connected == len(self.hws._ports)):
                self.hws._hwConnectStatus = HWSetup.HW_CONNECT_STATUS_OK # Alle COM-Ports wurden verbunden
                status = 1

            self.hws._updateHWSetupInProcess = False
            
            if(self.hws._hwConnectStatus != lastStatus):
                self.hws.sig_HWConnectFinished.emit(status)
            
            
