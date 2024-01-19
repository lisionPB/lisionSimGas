# -*- coding: utf-8 -*-
"""
Created on Tue Sep 13 11:22:45 2022

@author: Paul Benz

v2.4 (Channel Labels)

Last changed: 26.05.2023

"""
import time
from datetime import datetime


from PyQt5.QtCore import pyqtSignal, QObject

import csvDataLogger as dl

class DataManager(QObject):
    """
    Verwaltet Messdaten in Zeitreihen in Dicts
    
    Verwende sig_newDataReceived(dict) um auf die Ankunft neuer Daten im Datenmanager zu reagieren.

    Args:
        dict: channelNames
    """
    
    # DataReceived Signal
    sig_newDataReceived = pyqtSignal([dict])
    
    TIME_LABEL = "Zeitstempel" # [s]
    
 
 
    def __init__(self, channelNames=""):
        super().__init__()
        print ("Init Data Manager")
        
        self.counter = 0
        
        self.__channelNames = channelNames # Die für die Prüfung ausgewählten Kanäle
        self.__channelLabels = dict()
        self.__init_Structure__()
        self.__startTime = time.time()
        
                
        ###############
        # Aufzeichnung von Messdaten
        self.recordDataFlag = False
        self.dataRecordPath = ""
        
        
    def __init_Structure__(self):
        self.__data = dict()
        
        # Zeit
        lt = list()
        self.__data[self.TIME_LABEL] = lt
                
        for n in self.__channelNames:
            l = list()
            self.__data[n] = l
        
    
    def get_currentTime(self):
        """Generiere Zeitstempel
        """
        t = time.time()
        return t - self.__startTime
    
        
    def append_RawData(self, data):
        """
        Fügt die Rohdaten der Datenstruktur hinzu. Die Zeit wird automatisch Verwaltet.
        
        @Param:
            - data: dict mit ChannelNames als keys
        """
        
        
        # Hole für jeden Kanal die Daten aus data
        for cn in self.__channelNames:
            if(not cn in data or data[cn] == "BUSY"):
                print ("Datenframe unvollständig ( " + cn  + " )!")
                data[cn] = self.replace_incompleteData(cn)
                
            self.__data.get(cn).append(data[cn])
                    
        # Generiere Zeitstempel des Dateneingangs		
        t = self.get_currentTime()
        self.__data.get(self.TIME_LABEL).append(t) 
                            
                            
        # Füge für spätere Verwendung den Zeitstempel zum Datensatz hinzu.
        data[self.TIME_LABEL] = t
        self.counter += 1

        # print(str(len(data)) + "/" + str(len(self.__data)))

        self.sig_newDataReceived.emit(data)
        
        self.record_Data()
            
    
    def set_channelNames(self, channelNames):
        """
        Setzt die Kanalnamen und reinitialisiert die Datenstruktur mit den neuen Kanalbezeichnungen.
        """
        self.__channelNames = channelNames
        self.__init_Structure__()
        
        
    def set_channelLabels(self, channelLabels):
        """
        Setzt die Label für die Kanäle, welche über get_channelNames abgerufen werden können. 

        Args:
            channelLabels (_type_): dict()
        """
        self.__channelLabels = channelLabels
        
        
    def replace_incompleteData(self, cn):
        val = 0
        if(len(self.__data[cn]) > 0):
            val = self.get_LastData()[cn]
        return val

  
  
  
    def get_channelNames(self):
        return self.__channelNames
    
    
 
    def get_channelLabels(self):
        out = self.__channelLabels
        for i in range (len(self.__channelNames)):
            if(not self.__channelNames[i] in out):
                out[self.__channelNames[i]] = self.__channelNames[i] 
        return out
 
 
 
    def get_DataDict(self):
        return self.__data
    
 
 
 
    def get_LastData(self):
        last = dict()
        for k in self.__data:
            if(len(self.__data[k]) > 0):
                last[k] = self.__data[k][-1]
            else:
                print(k)
                
        if(len(last) == len(self.__data)):
            return last		
        
        return None
 
    def get_LastTime(self):
        last = self.get_LastData()
        if (last != None):
            return last[self.TIME_LABEL]
        return None
 
 
    def get_Data(self, key):
        return self.__data[key]
 
 
    def reset(self):
        chNames = list(self.__data.keys())[1:]
    
        self.__data.clear()
        self.set_channelNames(chNames)
        self.__startTime = time.time()
  
  
  
    def get_CurrentCount(self):
        self.counter
  
  
  
###################################################
# Aufzeichnung von Messdaten

    def start_recordData(self):
        """
        Startet die Aufzeichnung von Messdaten
        """
        self.recordDataFlag = True      
        
        # Setze Dateipfad aus Aktueller Uhrzeit zusammen.       
        dt = datetime.now()
        dtString = dt.now().strftime('%d-%m-%Y-%H-%M-%S')
        self.dataRecordPath = "dataLogs/Flussmessung_" + dtString + ".csv"
        
        # Erstellt die Log-Datei
        dl.open_log(self, self.dataRecordPath)
        


    def record_Data(self):
        """
        Aufzeichnung der Messwerte aus DataManager
        """
        if(self.recordDataFlag):
            dl.log_csvDataLine(self, self.dataRecordPath)
            
            
            
    def stop_recordData(self):
        """
        Stopt die Aufzeichnung der Messwerte
        """
        self.recordDataFlag = False
        print ("Data saved as " + self.dataRecordPath)
