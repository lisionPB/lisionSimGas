# author: Paul Benz
# 13.01.2025

import os
import time
import datetime
from pymodbus.client import ModbusTcpClient

from PyQt5.QtCore import QObject, pyqtSignal

SENSOR_NAMES = {
    0: "4..20 mA",
    1: "BT-4",
    2: "DF-7010",
    3: "DF-7100",
    4: "DF-7500",
    5: "DF-8201",
    6: "DF8250",
    7: "DF-8510",
    8: "DF-8603",
    9: "DF-9200",
    10: "DF-9500",
    11: "DF-9500C",
    12: "GD10",
    13: "RG-3LCD",
    14: "SafEye",
    15: "Ultima X",
    16: "Ultima XE",
    17: "Ultima XIR",
    18: "FlameGard",
    19: "500S",
    20: "D-7010",
    21: "D-7100",
    22: "D-715 K",
    23: "D-7152 K",
    24: "D-7711 K",
    25: "Serie 47K-ST",
    26: "Serie 47K-HT",
    27: "Serie 47K-PRP",
    28: "PrimaX",
    29: "PrimaX IR",
    30: "Ultima 52",
    31: "Ultima 5H",
    32: "Ultima 5E",
    33: "Flamegard 5 MSIRH",
    34: "Flamegard 5 MSIR",
    35: "Flamegard 5 UVIR",
    36: "Flamegard 5 UVIRH",
    37: "Flamegard 5 UVIRH2",
    38: "Flamegard 5 UVIRE",
    39: "UltraSonic IS-5",
    40: "UltraSonic EX-5",
    41: "Ultima OPIR-5"
}

MODBUS_ADR_SENSOR_OFFSET_VALUE = -1
MODBUS_ADR_SENSOR_OFFSET_STATUS = 0
MODBUS_ADR_SENSOR_OFFSET_HEAD = 1
MODBUS_ADR_DEVICESTATUS = 3

DEV_STATUS = "STATUS"
CH_ALARM_1 = "ALARM_1"
CH_ALARM_2 = "ALARM_2"

class GasGardEA(QObject):
    """
    # GasGard XL ...
    """  
    
    sig_sensorNamesReceived = pyqtSignal()
    
    def __init__(self, host='172.20.30.2', **args):
        
        super().__init__()
        
        self.__host = host
        self.__client = None
        self._sensors = {}
        
        # Initialen Verbindungsversuch starten
        # self.connect()
        
        
    def connect(self):
        try:
            # Starte den Client für die Verbindung zum Server
            host = ModbusTcpClient(self.__host)
                        
            self.__client = host
            # print(self.__client.is_active())
            # Initiales Test-Lesen
              
            if(self.checkDeviceConnected()):  
                print("Verbindung zu GasGard hergestellt!")
                
                # read sensor names
                for s in self._sensors:
                    self._sensors[s]["type"] = self.getChannelSensorName(self._sensors[s]["channel"])
                self.sig_sensorNamesReceived.emit() # -> Anzeige in Widget
                
                return True

        except:
            print("Verbindungsversuch zu GasGard fehlgeschlagen!") 
        
        return False

    
    def close(self):
        if(self.__client != None):
            self.__client.close()


    def checkDeviceConnected(self): 
        try:
            addr = MODBUS_ADR_DEVICESTATUS
            rr = self.__client.read_holding_registers(address=addr, slave=1)
        except Exception as exc:
            raise exc
        
        if rr.isError():
            print("Fehler beim Verbindungsaufbau zu GasGard!")
            raise Exception("Verbindung zu GasGard konnte nicht hergestellt werden!")
            return False
        
        return True


    def setSensorBereiche(self, sensors):
        self._sensors = sensors



    def checkDeviceStatus(self):
        if(self.__client):
            rr = None
            try:
                rr = self.__client.read_holding_registers(address=MODBUS_ADR_DEVICESTATUS)
                # print(rr.encode())
            except Exception as exc:
                raise exc
            if rr.isError():
                raise Exception("ERR: Lesen der digitalen Eingänge")
                print("read test - error: rr: " + str(rr.encode()) )
                return None
            return rr
            
            
    def checkChannelStatus(self, channel):
        if(self.__client):
            rr = None
            try:
                rr = self.__client.read_holding_registers(address= 10*channel + MODBUS_ADR_SENSOR_OFFSET_STATUS)    
            except Exception as exc:
                raise exc
            if rr.isError():
                raise Exception("ERR: Lesen der digitalen Eingänge")
                print("channel test - error: rr: " + str(rr.encode()) )
                return None
            return rr
        else:
            print("gasGardEA: Keine Verbindung!")
            
            
            
    def getChannelSensorName(self, channel):
        if(self.__client):
            rr = None
            try:
                addr = (10*channel) + MODBUS_ADR_SENSOR_OFFSET_HEAD
                rr = self.__client.read_holding_registers(address=addr)
                return SENSOR_NAMES[rr.registers[0]]
            except Exception as exc:
                raise exc
            if rr.isError():
                raise Exception("ERR: Lesen der digitalen Eingänge")
                print("channel test - error: rr: " + str(rr.encode()) )
                return None
            return rr
        else:
            print("gasGardEA: readSensorNames: Keine Verbindung!")


    def getChannelSensorValue(self, channel):
        if(self.__client):
            rr = None
            try:
                addr = (10*channel) + MODBUS_ADR_SENSOR_OFFSET_VALUE
                rr = self.__client.read_holding_registers(address=addr)
            except Exception as exc:
                raise exc
            if rr.isError():
                raise Exception("ERR: Lesen der digitalen Eingänge")
                print("channel value - error: rr: " + str(rr.encode()) )
                return None
            return rr.registers
        else:
            print("gasGardEA: Keine Verbindung!")
            
            

    def readAll(self):
        """
        Einlesen ALLER Holding Register.
        returns device_status, channel_status, channel_values
        """
        
        device_status = None
        sensors_status = None
        sensors_values = None
        
        if(self.__client):
            r = self.__client.read_holding_registers(address=0, count=89)

            if r.isError():
                print("ERR: Lesen der digitalen Eingänge")

            else:
                try:
                    rr = r.registers
                    
                    device_status = {}
                    sensors_status = {}
                    sensors_values = {}
                    
                    # device
                    device_status[DEV_STATUS] = rr[3]
                    
                    for s in list(self._sensors.keys()):
                        sensors_status[s] = {}
                        ch = self._sensors[s]["channel"]
                        # alarme
                        sensors_status[s][CH_ALARM_1] = rr[(10*ch) + MODBUS_ADR_SENSOR_OFFSET_STATUS] & 1
                        sensors_status[s][CH_ALARM_2] = rr[(10*ch) + MODBUS_ADR_SENSOR_OFFSET_STATUS] & 2
                        # values
                        rawVal = rr[(10*ch) + MODBUS_ADR_SENSOR_OFFSET_VALUE]
                        sensors_values[s] = rawVal if rawVal < 32768 else rawVal - 65536
                    
                except Exception as exc:
                    print("Fehler beim Lesen der GasGard Sensoren")
                    raise exc 
        
            return device_status, sensors_status, sensors_values
        
    

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
    ggEA = GasGardEA('172.20.30.2')

    ggEA.connect()

    # Testausgabe

    # print(ggEA.getChannelSensorName(1))
    # print(ggEA.getChannelSensorValue(1))
    print(ggEA.readAll())

    # print(str(datetime.datetime.now()) + ": " + str(ggEA.checkChannelStatus(1).registers))

    #    
    # Dauertest
    #while(True):
    #    print(str(datetime.datetime.now()) + ": " + str(ggEA.checkChannelStatus(1).registers))
    #    time.sleep(1.0)
