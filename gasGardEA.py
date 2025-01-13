# author: Paul Benz
# 13.01.2025

import os
from pymodbus.client import ModbusTcpClient

class GasGardEA(object):
    """
    # GasGard XL ...
    """  
    
    def __init__(self, host='127.20.20.3', **args):
        self.__host = host
        self.__client = None
        self._sensors = {}
        # Initialen Verbindungsversuch starten
        self.connect()
        
        
    def connect(self):
        try:
            # Starte den Client für die Verbindung zum Server
            host = ModbusTcpClient(self.__host)
                        
            self.__client = host
            
            # Initiales Test-Lesen
            data = self.readDigitalInput()
            if(data != None):
                print("Verbindung zu GasGardEA hergestellt!")
                return True

        except:
            print("Verbindungsversuch zu GasGardEA fehlgeschlagen!") 
        
        return False


    def setSensorBereiche(self, sensors):
        self._sensors = sensors
        

    def readDigitalInput(self):
        """
        Einlesen aller Sensoren.
        """
        if(self.__client):
            try:
                return self.__client.read_coils(0, 2)
            except:
                print("ERR: Lesen der digitalen Eingänge")
                return []
        return None
        
    

# -------------------------------------------------------------------------
# Hauptebene
# -------------------------------------------------------------------------

if __name__ == '__main__':
    
    # ----------------------------------------------------------------------
    # Applikationsebene (Hier nur für Testzwecke!)
    # ----------------------------------------------------------------------
    
    # Einbinden der Klasse aus der externen Bibliothek
    from gasGardEA import GasGardEA
    
    # Achtung: Die IP-Adresse ist vom jeweiligen Netzwerk abhänig!
    ggEA = GasGardEA('172.20.20.3')

    # Testausgabe
    print(ggEA.readDigitalInput())


