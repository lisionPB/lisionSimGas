# -*- coding: utf-8 -*-
"""
Created on Mon Jan 16 18:51:37 2023

v 2.2.1 (Max Counter for close all)

@author: paulb
"""


# PyQt5 - Bibliotheken für Threading und Signals
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QTimer

import time


class SecSetup(QObject):
    """
    Klasse zur Verwaltung von Messkomponenten
    
    Verwende _zuweisen_Port(self, name, p) um Messkomponenten hinzuzufügen
    Verwende _connect_Ports(self) um Verbindung zu Ports herzusstellen
    Verwende _start_MessSchleife(self) um Messschleife zu starten
    """
    
    DEFAULT_SCAN_INTERVAL = 250
    
    SEC_CONNECT_STATUS_NONE = -1     # Verbindung zu keinem COM-Port aufgebaut
    SEC_CONNECT_STATUS_OK = 1        # Verbindungen zu allen Ports hergestellt.
       
    CMD_TABLE = ["MOx","FP?","TE?","HU?"]
    
    _sig_NewSecData = pyqtSignal(dict)
    _sig_SEC_SetupConnect = pyqtSignal()
    sig_SEC_ConnectFinished = pyqtSignal(int)
    
    def __init__(self, ms):
        super().__init__()
        
        self._sms = ms
        self._smsPort = "11"
        
        self._secConnectStatus = self.SEC_CONNECT_STATUS_NONE
        
        # Verbinde Receiver für neue Daten
        # self._sig_NewSecData.connect(self.dm.append_RawData) 
        
        self.cmdSwitch = 0
        self.cmdOpen = 0
        self.data = {"FP?":0, "TE?":0, "HU?":0}
        
        ##############
        # Status
        
        self._sms_Open = False
        
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
        
        ####
        
        self.htc = SEC_ConnectThread(self)
        self._sig_SEC_SetupConnect.connect(self.htc.start)
        self._update_SECSetupInProcess = False
        
        ###
        
        self.terminated = False

        
    def _connect_sec(self, port):
        self._sms._set_Port(port)
        self._smsPort = port
        if(not self._update_SECSetupInProcess):
            self._sig_SEC_SetupConnect.emit()

            
    def _start_MessSchleife(self):
        self._threadMessLoop.start()
        
                
        
    def _read_Messwerte(self):
        

        # Versuche Verbindung neu aufzubauen, wenn Fehler vorliegt:
        if(self._secConnectStatus != self.SEC_CONNECT_STATUS_OK):
            self._connect_sec(self._smsPort)
        
        if(self._secConnectStatus == self.SEC_CONNECT_STATUS_OK):
            
            # Sende Befehl, der an der Reihe ist.
            if(self.cmdSwitch == 0):
                # Setze Ventil Open / Closed abhängig von
                if(self.cmdOpen):
                    self._sms._set_MO_open()
                else:
                    self._sms._set_MO_closed()
                self._sms_Open = self.cmdOpen
            
            else:
                cmd = self.CMD_TABLE[self.cmdSwitch]
                msg = self._sms._read(cmd)
                val = "---"
                try:
                    val = float(msg)
                except:
                    pass
                self.data[cmd] = val

                if(msg == None):
                    # Fehler beim Auslesen des Messwertes
                    print ("SEC: Fehler beim Auslesen des Messwertes!")
                    self._secConnectStatus = self.SEC_CONNECT_STATUS_NONE
                    
            self.cmdSwitch = (self.cmdSwitch + 1) % 4

            return self.data                
        
        return None                 
    
           


    def get_Messwerte(self):
        return self.data



    def set_sms_open(self, open):
        self.cmdOpen = open



    def _close_secSetup(self):
                
        # Ports schließen
        cnt = 0
        allClosed = False
        while(not allClosed and cnt < 10):
            print ("Closing SEC Setup ...")
            if(not self._sms._close()):
                allClosed = False
                cnt += 1
                time.sleep(0.1)
            else:
                allClosed = True
            
        # Update Thread beenden    
        self._worker._stop_worker()
        
        self.terminated = True
        print("SEC-Setup closed")
            
            
            
            
###########################################################################################################
# 
# Helferklassen           

class SEC_UpdateWorker(QObject):
    """
    Enthält den Haupttask zum Update des Sec
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
        
            print ("connect SEC")
    
            self.hws._update_SECSetupInProcess = True         
            
            self.hws._secConnectStatus = SecSetup.SEC_CONNECT_STATUS_NONE # Noch kein COM-Port wurde verbunden      

            if(self.hws._sms._connect() == True):
                self.hws._secConnectStatus = SecSetup.SEC_CONNECT_STATUS_OK # Alle COM-Ports wurden verbunden

            self.hws._update_SECSetupInProcess = False
            
            if(self.hws._secConnectStatus != lastStatus):
                self.hws.sig_SEC_ConnectFinished.emit(self.hws._secConnectStatus)
            
            
