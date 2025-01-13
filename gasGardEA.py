# author: Paul Benz
# 13.01.2025

import os
from pymodbus.client import ModbusTcpClient

class GasGardEA(object):
    """
    # GasGard XL ...
    """  
    
    MODBUS_REG_DEVICESTATUS = 40003
    
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
            # print(self.__client.is_active())
            # Initiales Test-Lesen
            
            if(self.checkDeviceConnected()):
                print("Verbindung zu GasGard hergestellt!")
                return True

        except:
            print("Verbindungsversuch zu GasGard fehlgeschlagen!") 
        
        return False
    
    def close(self):
        self.__client.close()


    def checkDeviceConnected():
        try:
            rr = self.__client.read_holding_registers(address=MODBUS_REG_DEVICESTATUS)
            print(rr)
        except ModbusException as exc:
            #_logger.error(f"ERROR: exception in pymodbus {exc}")
            raise exc
        if rr.isError():
            print("Fehler beim Verbindungsaufbau zu GasGard!")
            #_logger.error("ERROR: pymodbus returned an error!")
            raise ModbusException("Verbindung zu GasGard konnte nicht hergestellt werden!")
            return False
        
        return True

    def setSensorBereiche(self, sensors):
        self._sensors = sensors
        

    def readAll(self):
        """
        Einlesen ALLER Sensoren.
        """
        if(self.__client):
            rr = None
            try:
                print(list(self._sensors.keys()))
                addr1 = self._sensors[self._sensors.keys[0]]
                print(addr1)               
                rr = self.__client.read_holding_registers(address=addr1, count=80)
                return self.__client.read_coils(0, 2)
            except ModbusException as exc:
                #_logger.error(f"ERROR: exception in pymodbus {exc}")
                raise exc
            if rr.isError():
                print("ERR: Lesen der digitalen Eingänge")
                #_logger.error("ERROR: pymodbus returned an error!")
                raise ModbusException("ERR: Lesen der digitalen Eingänge")
                return None
        
            return rr.bits
        
    

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
    print(ggEA.readAll())


