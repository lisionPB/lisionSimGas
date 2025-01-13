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
        self.__dout = [False for x in range(0, 2)]
  
        # Initialen Verbindungsversuch starten
        self.__client = None
        self.connect()
        
        self._sensors = {}
        

        
    def connect(self):
        try:
            # Starte den Client für die Verbindung zum Server
            
            host = ModbusTcpClient(self.__host)
            
            #TODO: Check, ob Verbindungsaufbau erfolgreich                
            self.__client = host
            
            # Setze alle Ausgangsinformationen auf einen initialen Wert gemaess der Config-Datei
            self.MAGVENT(0)
            
            print("Verbindung zu SimGasEA hergestellt\n")
            
            return True

        except:
            print("Verbindungsversuch zu SimGasEA fehlgeschlagen")    
            return False
        
        return False
        
    
    def setSensorBereiche(self, sensors):
        self._sensors = sensors
    

    def __readDigitalInput(self):
        """
        Einlesen aller digitalen Eingaenge.
        """
        if(self.__client):
            try:
                return self.__client.read_coils(0, 2)
            except:
                print("ERR: Lesen der digitalen Eingänge")
                return []
        return None


    def MAGVENT(self, __state=None):
        """
        Hauptventil für den Gasfluss (Digitaler Ausgang)
        """
        if(self.__client):
            try:
                if __state == None:
                    return self.__dout[0]
                else:
                    ans = self.__client.write_coil(0, __state).value
                    if isinstance(ans, bool):
                        self.__dout[0] = ans
                        return ans
                    
            except Exception as e:
                print (e)
                print("Fehler beim Ansteuern des Magnetventils")
    
        return None
            
    
    def GASFLOWACTIVE(self, __state=None):
        """
        LED zur Anzeige, ob Gas fließt (Digitaler Ausgang)
        """
        if(self.__client):
            if __state == None:
                return self.__dout[1]
            else:
                ans = self.__client.write_coil(1, __state).value
                if isinstance(ans, bool):
                    self.__dout[1] = ans
                    return ans
        return None
           
            
    def VORDRUCK(self):
        """
        Druck in der Gasflasche (Analoger Eingang 2 Byte)
        """
        if(self.__client):
            # Lesen des Wertes von der Analogkarte
            ans = self.__client.read_input_registers(0)
            val = ans.getRegister(0)
            # 0 - 16 bar Messbereich
            fac = 16 / 2047
            # Vorzeichen ermitteln
            sig = 1 if (val & 32768) == 0 else -1
            # Vorzeichen entfernen
            val = val & 32767
            # Liegt ein Fehler vor?
            err = False if (val & 3) == 0 else True
            # Zahl ermitteln
            val = (val >> 4) * fac * sig
            # Rückgabe eines Messwertfehlers. err=False => Wert ist gültig!
            return  err, val
        return None


    def VORDRUCK_ID(self, idstr):
        """
        Druck in der Gasflasche mit id idstr (Analoger Eingang 2 Byte)
        """
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
    
    # Der Koppler hat die "echte" IP-Adresse: '192.168.2.236'
    # Achtung: Die IP-Adresse ist vom jeweiligen Netzwerk abhänig!
    koppler_1 = SimGasEA('172.29.55.101')
    
    # Der Zugriff auf die E/A-Ebene erfolgt mit den "symbolischen Namen", die durch
    # die jeweilige 'Config'-Datei vorgegeben wurden. Kenntnisse über Modbus oder sonstige
    # 'Besonderheiten' sind nicht erforderlich.

    # Setzen eines digitalen Ausgangs:
    koppler_1.MAGVENT(1)
    #
    # Löschen eines digitalen Ausgangs:
    #koppler_1.MAGVENT(0)
    #
    # Abfrage, ob der Ausgang gesetzt ist oder nicht:
    #print(koppler_1.MAGVENT())
    #
    #
    print(koppler_1.VORDRUCK())


