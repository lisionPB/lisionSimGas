#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 23.03.2024
# Automatisch generierte Datei für die Modbus-Kopplung via Ethernet
# zu einem WAGO750 Feldbus-Controller auf Grundlage einer '.config'-Datei.
# Config-Datei    : SimGas.config
# Erstellt durch  : createEA.py
# Software-Version: 15.02.2024

import os
from pymodbus.client import ModbusTcpClient

class SimGasEA(object):
    """
    WAGO-I/O-SYSTEM 750
    750-362, 750-362/0000-0001
    FC Modbus TCP; G4 (BootP)
    Feldbuskoppler Modbus TCP; 4. Generation (BootP)
    """  
    
    def __init__(self, host='127.25.50.10', **args):
        """
        Initalroutine. 
        """
        self.__host = host
        # Zustand der digitalen Ausgaenge intern speichern
        self.__dout = [False for x in range(0, 8)]
  
        # Initialen Verbindungsversuch starten
        self.__client = None
        self.connect()
        
        self._sensors = {}
        self._sensorsMGS = {}
        

        
    def connect(self):
        try:
            # Starte den Client für die Verbindung zum Server
            
            host = ModbusTcpClient(self.__host)
                       
            self.__client = host
            
            # Setze alle Ausgangsinformationen auf einen initialen Wert gemaess der Config-Datei
            
            # Schließe alle mag ventile
            for i in range(3):
                self.writeDigitalOutput(i, False)
            
            print("Verbindung zu SimGasEA hergestellt\n")
            
            return True

        except:
            print("Verbindungsversuch zu SimGasEA fehlgeschlagen")    
            return False
        
        return False
        
    
    
    def setSensorBereiche(self, sensors):
        self._sensors = sensors
    
    
    def setMGSSensorBereiche(self, mgsSensors):
        self._sensorsMGS = mgsSensors
    
    

    
    
    def writeDigitalOutput(self, chId, val):
    
        if(self.__client):
            try:
                ans = self.__client.write_coil(chId, val).value
                if isinstance(ans, bool):
                    self.__dout[chId] = ans
                    return ans
                
            except Exception as e:
                print (e)
                print("Fehler beim Ansteuern des Magnetventils " + str(chId))
    
        return None


    def isDigitalOutputSet(self, chId):
        return self.__dout[chId]
    
    
    def GASFLOWACTIVE(self, __state=None):
        """
        LED zur Anzeige, ob Gas fließt (Digitaler Ausgang)
        """
        if(self.__client):
            if __state == None:
                return self.__dout[1]
            else:
                ans = self.__client.write_coil(3, __state).value
                if isinstance(ans, bool):
                    self.__dout[3] = ans
                    return ans
        return None
    
    
    
    def STOERUNG(self, __state=None):
        """
        LED zur Anzeige, ob Gas fließt (Digitaler Ausgang)
        """
        if(self.__client):
            if __state == None:
                return self.__dout[1]
            else:
                ans = self.__client.write_coil(4, __state).value
                if isinstance(ans, bool):
                    self.__dout[4] = ans
                    return ans
        return None
    

    def readAnalogInputVordruck(self, idstr):
        
        if(self.__client):
            # Lesen des Wertes von der Analogkarte
            ans = self.__client.read_input_registers(int(self._sensors[idstr]["addr"][0]))
            val = ans.getRegister(0)
            # 0 - max bar Messbereich
            fac = (float(self._sensors[idstr]["max"]) - float(self._sensors[idstr]["min"])) / 2047
            # Vorzeichen ermitteln
            sig = 1 if (val & 32768) == 0 else -1
            # Vorzeichen entfernen
            val = val & 32767
            # Liegt ein Fehler vor?
            err = False if (val & 3) == 0 else True
            # Zahl ermitteln
            val = ((val >> 4) * fac + float(self._sensors[idstr]["min"]) ) * sig
            # Rückgabe eines Messwertfehlers. err=False => Wert ist gültig!
            return  err, val
        return None        
    
    
    def readAnalogInputMGSBox(self, idstr):
        if(self.__client):
            # print(f"idstr: {idstr}")
            # Lesen des Wertes von der Analogkarte
            ans = self.__client.read_input_registers(int(self._sensorsMGS[idstr]["addr"][0]))
            val = ans.getRegister(0)
            # 0 - max bar Messbereich
            fac = (float(self._sensorsMGS[idstr]["max"]) - float(self._sensorsMGS[idstr]["min"])) / 2047
            # Vorzeichen ermitteln
            sig = 1 if (val & 32768) == 0 else -1
            # Vorzeichen entfernen
            val = val & 32767
            # Liegt ein Fehler vor?
            err = False if (val & 3) == 0 else True
            # Zahl ermitteln
            val = ((val >> 4) * fac + float(self._sensorsMGS[idstr]["min"]) ) * sig
            # Rückgabe eines Messwertfehlers. err=False => Wert ist gültig!
            return  err, val
        return None 
        
        
        

    def getClient(self):
        return self.__client
    
    

# -------------------------------------------------------------------------
# Hauptebene
# -------------------------------------------------------------------------

if __name__ == '__main__':
    
    # ----------------------------------------------------------------------
    # Applikationsebene (Hier nur für Testzwecke!)
    # ----------------------------------------------------------------------
    
    # Einbinden der Klasse aus der externen Bibliothek
    from SimGasEA import SimGasEA
    
    import time
    
    # Der Koppler hat die "echte" IP-Adresse: '192.168.2.236'
    # Achtung: Die IP-Adresse ist vom jeweiligen Netzwerk abhänig!
    koppler_1 = SimGasEA('172.20.20.2')
    
    # Der Zugriff auf die E/A-Ebene erfolgt mit den "symbolischen Namen", die durch
    # die jeweilige 'Config'-Datei vorgegeben wurden. Kenntnisse über Modbus oder sonstige
    # 'Besonderheiten' sind nicht erforderlich.

    sensorIds = [
        "MGS-Box 1 - Out 1",
        "MGS-Box 1 - Out 2",
        "MGS-Box 2 - Out 1",
        "MGS-Box 2 - Out 2"
    ]

    for i in range (100):
        for j in range (8):
            koppler_1.readAnalogInputMGSBox(sensorIds[j])

        time.sleep(1)

