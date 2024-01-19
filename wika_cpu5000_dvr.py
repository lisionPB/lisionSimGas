#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 29.09.2021

import time
import serial
import serial.tools.list_ports

# PyQt5 - Bibliotheken
from PyQt5.QtCore import QThread, pyqtSignal


class WIKA_CPU_5000():
    
    FP_SCALE = 20.00
    
    def __init__(self, name):
        
        self.__port = None
        self.__name = name
        
        # Connection
        self.__ser = None
        self.connected = False
        self.busy = False

        # Status
        self._open = False


    def _set_Port(self, port):
        self.__port = port
    

    def _connect(self):
        if (self.__port != None):
            try:
                if(self.__ser == None or self.connected == False): 
                    print (str(self.__port) + "(" + self.__name  + "): Starte Verbindungsaufbau-Versuch!")
                                    
                    self.__ser = serial.Serial(
                        port=self.__port, 
                        baudrate = 9600, 
                        parity=serial.PARITY_NONE, 
                        stopbits=serial.STOPBITS_ONE, 
                        bytesize=serial.EIGHTBITS, 
                        timeout=1
                    )
                                
                    # Test: Lesen des Messwertes.
                    if(self._read_ID() == None):
                        raise Exception()
                    
                    print (str(self.__port) + "(" + self.__name  + "): Verbindung zum Port hergestellt!")      
                    self.connected = True      
                    return True
        
                else:   # Verbindung zum Port steht schon und wird überprüft                
                    return True
                
                                
            except:
                print ("Verbindung zum Port " + str(self.__port) + "(" + self.__name  + "): konnte nicht hergestellt werden!")

                if(self.__ser != None):
                    self.__ser.close()
                self.__ser = None
                self.connected = False
            
                return False  
        else:
            print ("Verbindung zu " + self.__name  + " konnte nicht hergestellt werden! COM-Port nicht gesetzt!")
            return False            



    def _close(self):
        # print ("Closing WIKA cpu5000 ... 1")
        if(self.__ser != None):
            # print ("Closing WIKA cpu5000 ... 2")
            if(self.__ser.is_open):        
                # print ("Closing WIKA cpu5000 ... 3")
                if(not self._set_MO_closed()):        
                    # print ("Closing WIKA cpu5000 ... 4")
                    print("Unable to close " + self.__port + "!")
                    return False
                else:        
                    # print ("Closing WIKA cpu5000 ... 5")
                    self.__ser.close() 
                    self.connected = False
                    print(self.__port + " (" + self.__name  + ") closed")
        return True
                

# ABFRAGEN
   
    
    def _read_ID(self):
        #print ("=========================================v")
        
        msg = None
        
        # Überprüfung, ob Verbindung zum Regler aufgebaut wurde
        if(self.__ser == None or not self.__ser.is_open):
            print(str(self.__port) + "(" + self.__name  + "): Fehler beim Lesen der ID! ID kann nicht gelesen werden! Port ist nicht verbunden!")
            return None
        
        #print (str(self.__port) + ": busy = " + str(self.busy))
        
        if(not self.busy):
            self.busy = True
        
            if(self.__ser != None and self.__ser.is_open):
                print (str(self.__port) + "(" + self.__name  + "): lese ID...")
                #print (str(self.__port) + " is open!")
                ok = False
                cnt = 0
                # 3 Versuche
                while (ok == False and cnt < 3):
                    try:
                        self.__ser.write(b'ID?\r')
                        time.sleep(0.01)
                        msg = self.__ser.readline().decode("utf-8")
                        print ("ID von " + str(self.__port) + "(" + self.__name  + "):" + msg)
                        ok = True
                    except Exception as e:
                        print (e)
                        print(str(self.__port) + "(" + self.__name  + "): Fehler beim Lesen der ID durch Verbindungsfehler!")
                        if(self.__ser != None):
                            self.__ser.close()
                        self.__ser = None
                        self.connected = False
                    
                    cnt = cnt + 1
                        
            self.busy = False
            
            return msg
        
        else:
            # busy-Flag noch auf True!
            print (str(self.__port) + "(" + self.__name  + ") war busy! Konnte ID nicht lesen")
            return "BUSY"        
            
        
        self.busy = False
        #print ("=========================================")
        return None




    def _read(self, cmd):
        """
        Gibt den Druck in [g / min] zurück
        """   
        msg = None
        
        # Überprüfung, ob Verbindung zum Regler aufgebaut wurde
        if(self.__ser == None or not self.__ser.is_open):
            port = ""
            if(self.__port != None):
                port = self.__port
                
            print(str(port) + "(" + self.__name  + "): Fehler beim Lesen! Port ist nicht verbunden!")
            return None
        
        try:
            self.busy = True
            #print (str(self.__port) + "(" + self.__name  + "): lese " + cmd + " ...")
            cmdSend = cmd + "\r"
            cmdBytes = bytes(cmdSend,'UTF-8')
            self.__ser.write(cmdBytes)
            time.sleep(0.01)
            msg = self.__ser.readline().decode("utf-8")
            #print(cmd + ": " + msg)

        except Exception as e:
            print (e)
            print(str(self.__port) + "(" + self.__name  + "): Fehler beim Lesen!")
            if(self.__ser != None):
                self.__ser.close()
            self.__ser = None
            self.connected = False
                    
        self.busy = False
        return msg
        
        
    
# BEFEHLE

    def _set_MO_open(self):
        
        # Überprüfung, ob Verbindung zum Regler aufgebaut wurde
        if(self.__ser == None or not self.__ser.is_open):
            print(str(self.__port) + "(" + self.__name  + "): Fehler beim Öffnen des Magnetschalters! Port ist nicht verbunden!")
            return False        
               
        try:
            ok = False
            cnt = 0
            while(not ok and cnt < 10):
                if(not self.busy):
                    self.busy = True
                    self.__ser.write(b"MO1\r")
                    time.sleep(0.01)
                    self.busy = False
                    ok = True
                else:
                    time.sleep(0.01)
                    cnt += 1
                    
            if(not ok):
                raise Exception()
                        
        except Exception as e:
            print (e)
            print(str(self.__port) + "(" + self.__name  + "): Fehler beim Öffnen des Magnetschalters!")
            if(self.__ser != None):
                self.__ser.close()
            self.__ser = None
            self.connected = False
            self.busy = False
            return False

        self.busy = False
        self._open = True
        return True
    
    


    def _set_MO_closed(self):
        
        # print ("Closing WIKA cpu5000 ... 6")
        
        # Überprüfung, ob Verbindung zum Regler aufgebaut wurde
        if(self.__ser == None or not self.__ser.is_open):
            print(str(self.__port) + "(" + self.__name  + "): Fehler beim Schließen des Magnetschalters! Port ist nicht verbunden!")
            return False        
               
        try:
            ok = False
            cnt = 0
            while(not ok and cnt < 10):
                if(not self.busy):
                    self.busy = True
                    self.__ser.write(b'MO0\r')
                    time.sleep(0.01)
                    self.busy = False
                    ok = True
                else:
                    time.sleep(0.01)
                    cnt += 1
                    
            if(not ok):
                raise Exception()
                        
        except Exception as e:
            print (e)
            print(str(self.__port) + "(" + self.__name  + "): Fehler beim Schließen des Magnetschalters!")
            if(self.__ser != None):
                self.__ser.close()
            self.__ser = None
            self.connected = False
            self.busy = False
            return False

        self.busy = False
        self._open = False
        return True