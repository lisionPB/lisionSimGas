#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 29.09.2021

import time
import serial
import serial.tools.list_ports

# PyQt5 - Bibliotheken
from PyQt5.QtCore import QThread, pyqtSignal, QObject

# Bronkhorst-Propar Driver
import propar


class Regler_Dvr(QObject):
    
    # DataReceived Signal
    sig_newMsgReceived = pyqtSignal(bytes)
    
    ARBEITSBEREICH_PUFFER = 0.0 # Bereich in %, der von zusätzlch zur HW-Ober- und Untergrenze des Nenn-Arbeitsbereichs Abstand gehalten werden soll

    USE_BRONKHORST_TREIBER = True

    def __init__(self, name, port, arbeitsbereich, kalibrierung):
        """
        Args:
            port (str): Bsp: "COM1"
            arbeitsbereich (list(float)): Bsp: [10, 100] [g/min]
        """
        super().__init__()
        
        self.__instrument = None
        
        self.__name = name
        self.__port = port 
        self.__arbeitsbereich = arbeitsbereich
        
        self.__useKalibrierung = True
        self.__kalibrierung = self.load_Kalibrierung(kalibrierung)
        self.__pVordruck = 0.0
        self.__TGas = 0.0
        
        
        self.__soll = 0
        self.__mess = 0
        self.__zaehler = 0 
        
        self.__ser = None
        self.connected = False
        self.busy = False

        self.__enabled = True


    def _connect(self):
        
        if(self.USE_BRONKHORST_TREIBER):
        
            try:
                if(self.__instrument == None or self.connected == False): 
                    print (str(self.__port) + ": Starte Verbindungsaufbau-Versuch!")
                                    
                    print (self.__port)
                    self.__instrument = propar.instrument(self.__port)
                    # print (self.__instrument.address)
                    # print (self.__instrument.measure)
                    # print ("connection test ...")            
                    
                    # Test: Lesen des Messwertes.
                    if(self._read_Messwert() == None):
                        raise Exception()
                    
                    print (str(self.__port) + ": Verbindung zum Port hergestellt!")      
                    self.connected = True      
                    return True
        
                else:   # Verbindung zum Port steht schon und wird überprüft                
                    return True
                
                                
            except:
                print ("Verbindung zum Port " + str(self.__port) + " konnte nicht hergestellt werden!")

                if(self.__ser != None):
                    self.__ser.close()
                self.__ser = None
                self.connected = False
            
                return False  
        else:
            return self._connect_()
        

    def _connect_(self):
        try:
            if(self.__ser == None or self.connected == False): 
                print (str(self.__port) + ": Starte Verbindungsaufbau-Versuch!")
                                
                self.__ser = serial.Serial(
                    port=self.__port, 
                    baudrate = 38400, 
                    parity=serial.PARITY_NONE, 
                    stopbits=serial.STOPBITS_ONE, 
                    bytesize=serial.EIGHTBITS, 
                    timeout=1
                )
                
                # print ("connection test ...")            
                
                # Test: Lesen des Messwertes.
                if(self._read_Messwert() == None):
                    raise Exception()
                
                print (str(self.__port) + ": Verbindung zum Port hergestellt!")      
                self.connected = True      
                return True
    
            else:   # Verbindung zum Port steht schon und wird überprüft                
                return True
            
                            
        except:
            print ("Verbindung zum Port " + str(self.__port) + " konnte nicht hergestellt werden!")

            if(self.__ser != None):
                self.__ser.close()
            self.__ser = None
            self.connected = False
        
            return False  
                
    
    def load_Kalibrierung(self, kalibrierung):
        if (type(kalibrierung) == list):
            if (len(kalibrierung) == 4):
                return kalibrierung    
                
        raise Exception("Ungültiges Format für die Regler-Kalibrierung!")
        
    
    def set_Kalibrierung(self, kalibrierung):
        # print (kalibrierung)
        self.__kalibrierung = self.load_Kalibrierung(kalibrierung)    
    
 
    def _close(self):
        if(self.USE_BRONKHORST_TREIBER):
            if(self.__instrument != None):
                self.__instrument.setpoint = 0
                self.connected = False
                print(self.__port + " closed")
                return True
            return False
        else:
            return self._close_()
        

    def _close_(self):
        if(self.__ser != None):
            if(self.__ser.is_open):
                if(not self._set_Sollwert(0)):
                    print("Unable to close " + self.__port + "!")
                    return False
                self.__ser.close() 
                self.connected = False
                print(self.__port + " closed")
        return True

# ABFRAGEN


    def _read_Messwert(self):
        
        if(self.USE_BRONKHORST_TREIBER):
            
            #print ("=========================================v")
            
            # Überprüfung, ob Verbindung zum Regler aufgebaut wurde
            if(self.__instrument == None):
                print(str(self.__port) + ": Fehler beim Lesen des Messwertes! Messwert kann nicht gelesen werden! Port ist nicht verbunden!")
                return None
            
            #print (str(self.__port) + ": busy = " + str(self.busy))
            
            if(not self.busy):
                self.busy = True
            
                if(self.__instrument != None):
                    # print (str(self.__port) + ": lese Messwert...")
                    #print (str(self.__port) + " is open!")
                    ok = False
                    cnt = 0
                    while (ok == False and cnt < 3):
                        valPer = None
                        try:
                            valInt = self.__instrument.measure
                            # print(str(self.__port) + ": Read (int): " + str(valInt))
                            # Umrechnung des Messwertes in Prozent
                            # valPer = valInt/32000.0
                            valPer  = valInt / 32000.0 if valInt <= 41942 else (valInt - 65536) / 32000.0
                            
                            #print (valPer)
                            ok = True
                        except Exception as e:
                            print (e)
                            print(str(self.__port) + ": Fehler beim Lesen des Messwertes durch Verbindungsfehler!")
                            self.connected = False
                        
                        
                        cnt = cnt + 1
                        # print ("ok? " + str(ok))
                            
                
                #else:
                    # __ser == None oder not __ser. is_open!
                    #print (str(self.__port) + " is closed!")
                
                # Umrechnung von Prozent in g/min        
                val = None
                if(valPer != None):
                    val = valPer * self.__arbeitsbereich[1]
                    # print(self.__arbeitsbereich[1])
                    # Anwendung der Kalibrierung
                    if(self.__useKalibrierung):
                        #print ("Kalibrierung ...")
                        #alt = val
                        val = self.apply_Kalibrierung(val, self.__pVordruck, self.__TGas)
                        #print (str(alt) + " -> " + str(val))
                        
                
                self.__mess = val
                self.busy = False
                
                #print ("=========================================^")
                
                return val
            
            else:
                # busy-Flag noch auf True!
                print (str(self.__port) + ": war busy! Konnte Messwert nicht lesen")
                return "BUSY"        
                
            
            self.busy = False
            #print ("=========================================^")
            return None        
        
        else:
            return self._read_Messwert_()
            
    
    def _read_Messwert_(self):
        #print ("=========================================v")
        
        # Überprüfung, ob Verbindung zum Regler aufgebaut wurde
        if(self.__ser == None or not self.__ser.is_open):
            print(str(self.__port) + ": Fehler beim Lesen des Messwertes! Messwert kann nicht gelesen werden! Port ist nicht verbunden!")
            return None
        
        #print (str(self.__port) + ": busy = " + str(self.busy))
        
        if(not self.busy):
            self.busy = True
        
            if(self.__ser != None and self.__ser.is_open):
                # print (str(self.__port) + ": lese Messwert...")
                #print (str(self.__port) + " is open!")
                ok = False
                cnt = 0
                while (ok == False and cnt < 3):
                    valPer = None
                    try:
                        # print ("init read ...")
                        # print (self.__ser)
                        self.__ser.write(b':06030401210120\r\n') # Befehl zum Auslesen des Messwertes
                        time.sleep(0.01)
                        # print ("read ...")
                        msg = self.__ser.readline()
                        self.sig_newMsgReceived.emit(msg)
                        # Auslesen des Messwertes von Nachricht (letzte 2 Bytes vor \r\n)
                        # print (msg)
                        valStr = msg[11:15]
                        # print (valStr)
                        valInt = self.twos_complement(valStr, 16)
                        #print(valInt)
                        # Umrechnung des Messwertes in Prozent
                        valPer = valInt/32000.0
                        
                        if(valPer >= 1.0): 
                            print(str(self.__port) + ": Fehler beim Lesen des Messwertes: Ungültiger Messwert")
                            print(str(self.__port) + ": Antwort auf Messwertabfrage: " + str(msg))
                            self.busy = False
                            return None
                        
                        #print (valPer)
                        ok = True
                    except Exception as e:
                        print (e)
                        print(str(self.__port) + ": Fehler beim Lesen des Messwertes durch Verbindungsfehler!")
                        if(self.__ser != None):
                            self.__ser.close()
                        self.__ser = None
                        self.connected = False
                    
                    
                    cnt = cnt + 1
                    # print ("ok? " + str(ok))
                        
            
            #else:
                # __ser == None oder not __ser. is_open!
                #print (str(self.__port) + " is closed!")
            
            # Umrechnung von Prozent in g/min        
            val = None
            if(valPer != None):
                val = valPer * self.__arbeitsbereich[1]
                # print(self.__arbeitsbereich[1])
                # Anwendung der Kalibrierung
                if(self.__useKalibrierung):
                    #print ("Kalibrierung ...")
                    #alt = val
                    val = self.apply_Kalibrierung(val, self.__pVordruck, self.__TGas)
                    #print (str(alt) + " -> " + str(val))
                    
            
            self.__mess = val
            self.busy = False
            
            #print ("=========================================^")
            
            return val
        
        else:
            # busy-Flag noch auf True!
            print (str(self.__port) + ": war busy! Konnte Messwert nicht lesen")
            return "BUSY"        
            
        
        self.busy = False
        #print ("=========================================^")
        return None
    
    
    def twos_complement(self, hexstr, bits):
        value = int(hexstr, bits)
        if (value & (1 << (bits - 1))):
            value -= 1 << bits
        return value
        

    def set_current_pVordruck(self, pVordruck):
        self.__pVordruck = pVordruck
        
        
    def set_current_TGas(self, TGas):
        self.__TGas = TGas



    def apply_Kalibrierung(self, val, pVordruck, TGas):
        return self.__kalibrierung[0] + (self.__kalibrierung[1] * val) + (self.__kalibrierung[2] * pVordruck) + (self.__kalibrierung[3] * TGas)       


    def _read_Sollwert(self):
        """
        Gibt den Stellwert in [g / min] zurück
        """   
            
        if(self.USE_BRONKHORST_TREIBER):
            
            valPer = None
            
            # Überprüfung, ob Verbindung zum Regler aufgebaut wurde
            if(self.__instrument == None):
                print(str(self.__port) + ": Fehler beim Lesen des Sollwertes! Sollwert kann nicht gelesen werden! Port ist nicht verbunden!")
                return None
            
            try:
                self.busy = True
                valPer = self.__instrument.readParameter(9) / 32000.0
                # print(str(self.__port) + ": Read Sollwert:" + str(valPer))
                
            except Exception as e:
                print (e)
                print(str(self.__port) + ": Fehler beim Lesen des Sollwertes!")
                self.connected = False
                
            # Umrechnung von Prozent in g/min
            val = None
            if(valPer != None):
                val = valPer * self.__arbeitsbereich[1]
            
            self.busy = False
            return val
        
        else :
            return self._read_Sollwert_()
        

    def _read_Sollwert_(self):
        """
        Gibt den Stellwert in [g / min] zurück
        """   
        valPer = None
        
        # Überprüfung, ob Verbindung zum Regler aufgebaut wurde
        if(self.__ser == None or not self.__ser.is_open):
            print(str(self.__port) + ": Fehler beim Lesen des Sollwertes! Sollwert kann nicht gelesen werden! Port ist nicht verbunden!")
            return None
        
        try:
            self.busy = True
            self.__ser.write(b':06030401210121\r\n') # Befehl zum Auslesen des Sollwertes
            time.sleep(0.01)
            msg = self.__ser.readline()
            self.sig_newMsgReceived.emit(msg)
            # Auslesen des Sollwertes von Nachricht (letzte 2 Bytes vor \r\n)
            #print (msg)
            valStr = msg[11:15]
            valInt = int(valStr, 16)
            #print(valInt)
            # Umrechnung des Sollwertes in Prozent
            valPer = valInt/32000.0
            #print (valPer)
        except Exception as e:
            print (e)
            print(str(self.__port) + ": Fehler beim Lesen des Sollwertes!")
            if(self.__ser != None):
                self.__ser.close()
            self.__ser = None
            self.connected = False
            
        # Umrechnung von Prozent in g/min
        val = None
        if(valPer != None):
            val = valPer * self.__arbeitsbereich[1]
        
        self.busy = False
        return val
        
        
###########################################################################################################
#
# BEFEHLE

    def _set_Sollwert(self, soll):
        """
        Inklusive Rücklesen des Sollwertes
        @param: soll (float): stellwert in [g/min]
        """
        
        if(self.USE_BRONKHORST_TREIBER):
        
            # print ("set...")
            
            ###################
            # Ist nur zum Debuggen der Stellwert-Aufteilungsfunktion da !!!
            
            # self.__soll = soll
            ###################
            
            # Überprüfung, ob Verbindung zum Regler aufgebaut wurde
            if(self.__instrument == None):
                print(str(self.__port) + ": Fehler beim Setzen des Sollwertes! Sollwert kann nicht geschrieben werden! Port ist nicht verbunden!")
                return False
            
            # Überprüfung auf Grenzen des Sollwertes auf Arbeitsbereich
            if((soll < self.__arbeitsbereich[0] or soll > self.__arbeitsbereich[1]) and soll != 0):
                print(str(self.__port) + ": Fehler beim Setzen des Sollwertes! Sollwert + " + str(soll) + " liegt nicht im Arbeitsbereich " + str(self.__arbeitsbereich) + " des Reglers!")
                return False
            
            
            # Umrechnung von g/min in Prozent des Arbeitsbereiches
            sollPer = soll / self.__arbeitsbereich[1]
            
            try:
                valInt = int(sollPer * 32000)
                
                #print (valInt)
                self.__instrument.setpoint = valInt
                  
                ok = False
                cnt = 0
                # print (self.busy)
                while(not ok and cnt < 3):
                    
                    if(not self.busy):
                        self.busy = True
                        readSoll = round(self._read_Sollwert() / self.__arbeitsbereich[1] * 32000)
                        # print (str(readSoll) + "<->" + str(valInt))
                        
                        if(readSoll == valInt):
                            ok = True
                        else:
                            cnt += 1
                        
                if(not ok):
                    raise Exception()
                            
            except Exception as e:
                print (e)
                print(str(self.__port) + ": Fehler beim Schreiben des Sollwertes!")
                self.connected = False
                self.busy = False
                return False
            
            self.__soll = soll
            self.busy = False
            return True
    
        else:
            return self._set_Sollwert_(soll)
            
            

    def _set_Sollwert_(self, soll):
        """
        Inklusive Rücklesen des Sollwertes
        @param: soll (float): stellwert in [g/min]
        """
        
        # print ("set...")
        
        ###################
        # Ist nur zum Debuggen der Stellwert-Aufteilungsfunktion da !!!
        
        # self.__soll = soll
        ###################
        
        # Überprüfung, ob Verbindung zum Regler aufgebaut wurde
        if(self.__ser == None or not self.__ser.is_open):
            print(str(self.__port) + ": Fehler beim Setzen des Sollwertes! Sollwert kann nicht geschrieben werden! Port ist nicht verbunden!")
            return False
        
        # Überprüfung auf Grenzen des Sollwertes auf Arbeitsbereich
        if((soll < self.__arbeitsbereich[0] or soll > self.__arbeitsbereich[1]) and soll != 0):
            print(str(self.__port) + ": Fehler beim Setzen des Sollwertes! Sollwert + " + str(soll) + " liegt nicht im Arbeitsbereich " + str(self.__arbeitsbereich) + " des Reglers!")
            return False
        
        
        # Umrechnung von g/min in Prozent des Arbeitsbereiches
        sollPer = soll / self.__arbeitsbereich[1]
        
        try:
            valInt = int(sollPer * 32000)
            valHex = hex(valInt)[2:]
            
            # Fülle mit 0en auf
            valHexStr = str(valHex)
            for i in range (4-len(valHexStr)):
                valHexStr = "0" + valHexStr

            sendStr = ':0603010121' + str(valHexStr.upper()) + '\r\n'
            print (sendStr)
            sendBytes = sendStr.encode('UTF-8')
            #print (sendBytes)
                
            ok = False
            cnt = 0
            while(not ok and cnt < 10):
                
                if(not self.busy):
                    self.busy = True
                    # print ("send...")
                    self.__ser.write(sendBytes)
                    time.sleep(0.01)
                    # print ("read...")
                    result = self.__ser.readline()
                    self.sig_newMsgReceived.emit(result)
                    print ("R: " + str(result)) # sollte b':0403000005\r\n' sein
                    time.sleep(0.01)
                    self.busy = False
                    # print ("read soll ...")
                    # Überprüfe auf korrekte Übertragung
                    readSoll = round(self._read_Sollwert() / self.__arbeitsbereich[1] * 32000)
                    # print (str(readSoll) + "<->" + str(valInt))
                    # print ("soll: " + str(readSoll))
                    if(readSoll == valInt):
                        ok = True
                    else:
                        cnt += 1
                    
            if(not ok):
                raise Exception()
                        
        except Exception as e:
            print (e)
            print(str(self.__port) + ": Fehler beim Schreiben des Sollwertes!")
            if(self.__ser != None):
                self.__ser.close()
            self.__ser = None
            self.connected = False
            self.busy = False
            return False
        
        self.__soll = soll
        self.busy = False
        return True
    
# Setter

    def set_enabled(self, enabled):
        """Hat keine Auswirkungen auf Messungen! Einzig für spätere Verwendung benötigt.
        
        Args:
            enabled (_type_): Flag, ob Regler verwendet wird oder nicht.
        """
        self.__enabled = enabled

# Getter

    def get_name(self):
        return self.__name
    
    
    def get_port(self):
        return self.__port
       
        
    def get_arbeitsBereich(self):
        return self.__arbeitsbereich
    
    def get_arbeitsBereich_min(self):
        return self.__arbeitsbereich[0]
    
    def get_arbeitsBereich_max(self):
        return self.__arbeitsbereich[1]
    
    
    def get_arbeitsBereich_gepuffert(self):
        """
        Um ARBEITSBEREICH * 2 reduzierter Arbeitsbereich mit symmetrischem Puffer an den Enden, um Grenzbereiche zu vermeiden.

        Returns:
            list: 0: Untergrenze, 1: Obergrenze
        """
        puffer = (self.__arbeitsbereich[1] - self.__arbeitsbereich[0]) * self.ARBEITSBEREICH_PUFFER
        return [self.__arbeitsbereich[0] + puffer , self.__arbeitsbereich[1] - puffer]
    
    
    def get_soll(self):
        return self.__soll
    
    
    def get_soll_percentage(self):
        return self.__soll / self.__arbeitsbereich[1] * 100
    
    
    def get_ist(self):
        return self.__mess
    
    
    def is_enabled(self):
        return self.__enabled
    
    
    def get_kalibrierung(self):
        return self.__kalibrierung


if __name__ == "__main__":
    
    
    with open("hexTest.txt", "w") as f:
        for i in range (0, 65536, 1):
            h = hex(i)
            f.write(str(i) + " -> " + str(h) + " -> " +  str(Regler_Dvr.twos_complement(None, h, 16)) + "\n")

        