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
    
    def __init__(self, sgEA):
        super().__init__()
                
        self._sgEA = sgEA   
        
        self._secConnectStatus = self.SEC_CONNECT_STATUS_NONE
        
        self.cmdSwitch = 0
        self.cmdOpen = 0
        self.data = {"FP?":0, "TE?":0, "HU?":0}
        
        # Init Flaschendruck Data
        self.dataVordruck = {}
        for f in self._sgEA._sensorsNames:
            self.dataVordruck[f] = 0

        
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
        
        ####
        
        self.terminated = False

            
    def _start_MessSchleife(self):
        if(self._secConnectStatus == self.SEC_CONNECT_STATUS_OK):
            self._threadMessLoop.start()
        else:
            print ("Warte auf Verbindung zur SEC-Harware...")    

                    
    def _connect_sec(self):
        if(not self._update_SECSetupInProcess):
            self._sig_SEC_SetupConnect.emit()
            
                
        
    def _read_Messwerte(self):
        
        # Versuche Verbindung neu aufzubauen, wenn Fehler vorliegt:
        if(self._secConnectStatus != self.SEC_CONNECT_STATUS_OK):
            self._connect_sec()
                
                
        if(self._secConnectStatus == self.SEC_CONNECT_STATUS_OK):
            # Vordruck
            try:
                err, msg = self._sgEA.VORDRUCK()
                
                
                # TO BE TESTED
                for f in self.dataVordruck:
                    err2, msg2 = self._sgEA.VORDRUCK_ID(f)
                    
                ####
                    
                    
                if(err):
                    raise Exception("Fehler beim Auslesen des Vordrucks")
                
            except:
                # Fehler beim Auslesen des Messwertes
                print ("SEC: Fehler beim Auslesen des Messwertes!")
                self._secConnectStatus = self.SEC_CONNECT_STATUS_NONE
            
            val = "---"
            try:
                val = float(msg)
            except:
                pass
            self.data["FP?"] = val
            return self.data                 
    
           


    def get_Messwerte(self):
        return self.data



    def set_sms_open(self, open):
        self._sgEA.MAGVENT(int(open))
        self._sms_Open = self._sgEA.MAGVENT()
    
        
    def is_sms_open(self):
        return self._sms_Open
    
        
    def set_gasFlowLED(self, activ):
        self._sgEA.GASFLOWACTIVE(int(activ))



    def _close_secSetup(self):
    
        self.set_sms_open(False)
    
        # Update Thread beenden    
        self._worker._stop_worker()
        
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
            if(self.hws._secConnectStatus != SecSetup.SEC_CONNECT_STATUS_OK):
                self.hws._sig_SEC_SetupConnect.emit()