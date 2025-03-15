#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 29.09.2021

import time
import serial
import serial.tools.list_ports

# PyQt5 - Bibliotheken
from PyQt5.QtCore import QThread, pyqtSignal, QObject, QTimer

# Bronkhorst-Propar Driver
import propar



class Regler_Dvr(QObject):
    
    # DataReceived Signal
    sig_newMsgReceived = pyqtSignal(bytes)
    sig_newIntegral = pyqtSignal()
    
    # Close Connection Signal
    sig_closeConnection = pyqtSignal()
    
    ARBEITSBEREICH_PUFFER = 0.0 # Bereich in %, der von zusätzlch zur HW-Ober- und Untergrenze des Nenn-Arbeitsbereichs Abstand gehalten werden soll
    ARBEITSBEREICH_TOLERANZ = 0.2 # Relative tolerierte Abweichung des Sollwertes zu Grenzen des Arbeitsbereiches

    USE_BRONKHORST_TREIBER = True
    
    DEFAULT_COM_TAKT = 100
    

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
        
        
        self.__soll = 0     # [g/min]
        self.__wunschSoll = 0   # [g/min]
        self.__wunschSollValInt = 0
        self.sollIsValid = False
        self.__mess = 0     # [g/min]
        self.__lastMessZeit = 0  # [s]
        self.__menge = 0    # [g] 
        self.__counter = 0  # [g] aus Regler ausgelesen - noch nicht einsatzbereit!
        
        self.__ser = None
        self.connected = False
        self.busy = False

        self.__enabled = True
        
        self.__timings = {}
        self.__maxTiming = {'messen': 0, 'soll lesen': 0, 'soll schreiben': 0}
        
        
        ##############
        # Messschleife

        self._interval = self.DEFAULT_COM_TAKT
        
        self._threadMessLoop = QThread()
        self._worker = ReglerUpdateWorker(self, self._interval)
        self._worker.moveToThread(self._threadMessLoop)
        
        self._threadMessLoop.started.connect(self._worker._start_worker)
        self._worker._sig_finished.connect(self._threadMessLoop.quit)
        self._worker._sig_finished.connect(self._worker.deleteLater)
        self._threadMessLoop.finished.connect(self._threadMessLoop.deleteLater)
        
        self.sig_closeConnection.connect(self._worker._stop_worker)


    def _connect(self):
        
        if(self.USE_BRONKHORST_TREIBER):
        
            try:
                if(self.__instrument == None or self.connected == False): 
                    # print (str(self.__port) + ": Starte Verbindungsaufbau-Versuch!")
                                    
                    self.__instrument = propar.instrument(self.__port)      
                    
                    # Test: Lesen des Messwertes.
                    if(self._read_Messwert() == None):
                        raise Exception()
                    
                    print (str(self.__port) + ": Verbindung zum Port hergestellt!")      
                    self.connected = True      
                    return True
        
                else:   # Verbindung zum Port steht schon              
                    return True
                
                                
            except:
                print ("Verbindung zum Port " + str(self.__port) + " konnte nicht hergestellt werden!")

                if(self.__ser != None):
                    self.__ser.close()
                self.__ser = None
                self.connected = False
            
                return False  
        
        
        
    def _start_MessSchleife(self):
        self._threadMessLoop.start()
        
        
            
    def load_Kalibrierung(self, kalibrierung):
        if (type(kalibrierung) == list):
            if (len(kalibrierung) == 4):
                return kalibrierung    
                
        raise Exception("Ungültiges Format für die Regler-Kalibrierung!")
        
    
    def set_Kalibrierung(self, kalibrierung):
        # print (kalibrierung)
        self.__kalibrierung = self.load_Kalibrierung(kalibrierung)    
    
 
    def _close(self):

        # Update Thread beenden    
        self.sig_closeConnection.emit()
        #self._worker._stop_worker()
        
        if(self.USE_BRONKHORST_TREIBER):
            if(self.__instrument != None):
                self.__instrument.setpoint = 0
                self.connected = False
                print(self.__port + " closed")
                return True

            return False
        



    def set_Sollwert(self, sollwert):
        """Setzt den Sollwert, der beim entsprechenden COM-Takt geschrieben wird

        Args:
            sollwert (_type_): [g/min]
        """

        self.__wunschSoll = sollwert
        self.__wunschSollValInt = int(self.__wunschSoll / self.__arbeitsbereich[1] * 32000)
        # TODO: Überprüfung, Ob sollwert erfolgreich gesetzt
        return True

        
        
    def _set_SollwertValid(self, valid):
        self.sollIsValid = valid



# GESAMTDURCHFLUSSMASSE INTEGRATION

    def start_Integration(self):
        self.__lastMessZeit = time.time()
        self.__menge = 0.0
        

    def _integrate_Messwert(self, newMesswert):
        
        # print("integrate!")
        
        if(self.__lastMessZeit != 0):
            newMessZeit = time.time()
            dt = newMessZeit - self.__lastMessZeit
            self.__menge += (newMesswert + self.__mess) / 2.0 * (dt/60.0)
            self.__lastMessZeit = newMessZeit
            
            #if(self.__name == "R1"):
            #    print("integrierte Menge: " + str(self.__menge))
                
        self.sig_newIntegral.emit()
        
            
    def get_integrierteMenge(self):
        return self.__menge
    
    

# ABFRAGEN


    def _read_Messwert(self):
        
        if(self.USE_BRONKHORST_TREIBER):
            
            #print ("=========================================v")
            
            # Überprüfung, ob Verbindung zum Regler aufgebaut wurde
            if(self.__instrument == None):
                print(str(self.__port) + ": Fehler beim Lesen des Messwertes! Messwert kann nicht gelesen werden! Port ist nicht verbunden!")
                return None
                        
            if(not self.busy):
                self.busy = True
            
                if(self.__instrument != None):

                    ok = False
                    cnt = 0
                    while (ok == False and cnt < 1):
                        valPer = None
                        try:
                            startTimer = time.time()
                            
                            # Read Messwert
                            valInt = self.__instrument.measure # Dauert im Test max. 64ms
                            
                            # TODO: Counter auslesen in eigenen COM Slot!
                            # Read 
                            self.__counter = self.readParameter(122)
                                                        
                            
                            dauer = time.time() - startTimer
                            self.__timings["messen"] = dauer
                            if(dauer > self.__maxTiming["messen"]):
                                self.__maxTiming["messen"] = dauer
                            
                            
                            # Umrechnung des Messwertes in Prozent
                            valPer  = valInt / 32000.0 if valInt <= 41942 else (valInt - 65536) / 32000.0
                        
                            ok = True
                        except Exception as e:
                            print (e)
                            print(str(self.__port) + ": Fehler beim Lesen des Messwertes durch Verbindungsfehler!")
                            self.connected = False
                        
                        cnt = cnt + 1
                            
                
                # Umrechnung von Prozent in g/min        
                val = None
                if(valPer != None):
                    val = valPer * self.__arbeitsbereich[1]
                    # Anwendung der Kalibrierung
                    if(self.__useKalibrierung):
                        val = self.apply_Kalibrierung(val, self.__pVordruck, self.__TGas)
                
                
                # Integration (Muss vor self.__mess = val stehen, weil alter Messwert noch benötigt wird)
                if(val != None):
                    # self.connected = True   # Wenn gültiger Messwert ankommt connected auf True setzen
                    self._integrate_Messwert(val)                
                
                # print(val)
                self.__mess = val
                
                self.busy = False
                
                return val
            
            else:
                # busy-Flag noch auf True!
                print (str(self.__port) + ": war busy! Konnte Messwert nicht lesen")
                return "BUSY"        
                
            
            self.busy = False

            return None        

    
    def writeParameter(self, dde_nr, value):
        """Sendet Parameter mit DDE_NR an Regler

        Args:
            dde_nr (int): DDE_NR
            value : Wert. Typ abhängig von Parameter Nummer

        Returns: True, wenn Schreibvorgang erfolgreich. Sonst False.
        """
        if(self.__instrument != None):
            return self.__instrument.writeParameter(dde_nr, value)
        return False
    


    def readParameter(self, dde_nr):
        if(self.__instrument != None):
            return self.__instrument.readParameter(dde_nr)
        return False
    
    

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
                startTimer = time.time()
                valInt = self.__instrument.readParameter(9)   # Dauert im Test max. 64ms
                dauer = time.time() - startTimer
                self.__timings["soll lesen"] = dauer
                if(dauer > self.__maxTiming["soll lesen"]):
                    self.__maxTiming["soll lesen"] = dauer
                valPer = valInt / 32000.0
                
            except Exception as e:
                print (e)
                print(str(self.__port) + ": Fehler beim Lesen des Sollwertes!")
                self.connected = False
                
            # Umrechnung von Prozent in g/min
            val = None
            if(valPer != None):
                val = valPer * self.__arbeitsbereich[1]
                # Neuen bestätigten Sollwert speichern
                self.__soll = val
            
            # Überprüfen, ob Sollwert korrekt gesetz wurde
            # print ("Soll-Abgleich: " + str(valInt) + " : " + str(self.__wunschSollValInt))
            self.sollIsValid = valInt == self.__wunschSollValInt
            
            self.busy = False
            
                    
        # Ausgabe von Timings
        #print("Letzte Timings:")
        #print(self.__timings)
        #print("Schlechteste:")
        #print(self.__maxTiming)
        
            
        
        
###########################################################################################################
#
# BEFEHLE

    def _write_Sollwert(self):
        """
        @param: soll (float): stellwert in [g/min]
        """
        
        if(self.USE_BRONKHORST_TREIBER):
                    
            # Überprüfung, ob Verbindung zum Regler aufgebaut wurde
            if(self.__instrument == None):
                print(str(self.__port) + ": Fehler beim Setzen des Sollwertes! Sollwert kann nicht geschrieben werden! Port ist nicht verbunden!")
                return False
            
            soll = self.__wunschSoll
            
            # Überprüfung auf Grenzen des Sollwertes auf Arbeitsbereich
            if((soll < self.__arbeitsbereich[0] - self.__arbeitsbereich[0] * self.ARBEITSBEREICH_TOLERANZ or soll > self.__arbeitsbereich[1] + self.__arbeitsbereich[1] * self.ARBEITSBEREICH_TOLERANZ ) and soll != 0):
                print(str(self.__port) + ": Fehler beim Setzen des Sollwertes! Sollwert + " + str(soll) + " liegt nicht im Arbeitsbereich " + str(self.__arbeitsbereich) + " des Reglers!")
                return False
            
            
            # Umrechnung von g/min in Prozent des Arbeitsbereiches
            sollPer = soll / self.__arbeitsbereich[1]
            
            try:
                valInt = int(sollPer * 32000)
                                    
                ok = False
                cnt = 0
                while(not ok and cnt < 1):
                    
                    if(not self.busy):
                        self.busy = True
                        startTimer = time.time()
                        if(self.__instrument.writeParameter(9, valInt)):        # Dauert im Test max. 64ms
                            ok = True    
                        else:
                            cnt += 1
                        dauer = time.time() - startTimer
                        self.__timings["soll schreiben"] = dauer
                        if(dauer > self.__maxTiming["soll schreiben"]):
                            self.__maxTiming["soll schreiben"] = dauer
                            
                    if(not ok):
                        raise Exception("Maximale Anzahl Versuche den Sollwert zu schreiben erreicht.")
                            
            except Exception as e:
                print (e)
                print(str(self.__port) + ": Fehler beim Schreiben des Sollwertes! ! !")
                self.connected = False
                self.busy = False
                return False
            
            self.__soll = soll
            self.busy = False
            self.connected = True
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
    
    
    def get_soll_vorgabe(self):
        return self.__wunschSoll
    
    
    def get_ist(self):
        return self.__mess
    
    
    def get_cnt(self):
        return self.__counter
    
    
    def is_enabled(self):
        return self.__enabled
    
    
    def get_kalibrierung(self):
        return self.__kalibrierung




class ReglerUpdateWorker(QObject):
    """
    Enthält den Haupttask zum Update der Messungen
    """
    _sig_finished = pyqtSignal()
    _sig_progress = pyqtSignal(int)
    
    def __init__(self, regler, interval):
        super(ReglerUpdateWorker, self).__init__()
        self._regler = regler
        self._interval = interval
        self._readingData = False
        self._timer = QTimer()
        
        self._paused = False
        
        self._currentComTakt = -1
        
        
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
        self._timer.timeout.connect(self._executeComTakt)
        self._timer.start()
        
    def _set_paused(self, paused):
        self._paused = int(paused)


    def _executeComTakt(self):

        self._currentComTakt = (self._currentComTakt + 1) % 3

        if(self._currentComTakt == 0):
        # Messwert lesen
            self._regler._read_Messwert()
                
       
        elif(self._currentComTakt == 1):
        # Sollwert schreiben
            self._regler._write_Sollwert()

            
        elif(self._currentComTakt == 2):
        # Sollwert lesen (wird in __soll geschrieben, kann per get_AkzeptiertenSollwert() ausgelesen werden)
            self._regler._read_Sollwert()
            
            
        else:
            print("Achtung !!! Unbekannter COM-Takt!!!")




if __name__ == "__main__":
    
    pass

        