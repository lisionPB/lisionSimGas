import time
import serial
import serial.tools.list_ports

# PyQt5 - Bibliotheken
from PyQt5.QtCore import QThread, pyqtSignal, QObject

# TODOs:
# - Referenz auf ModBus-Schnittstelle als self.__instrument setzen
# - Referenz auf ModBus-Schnittstelle nutzen, um Messwerte auszulesen / zu setzen
# - Identifizierung von Schnittstelle über port (Ist das ein Dict-Key?)
#
# Idee: FELDBUSKOPPLER <-> SVENS Modul <-> ReglerTreiber
#|-> Svens Modul :  - Methode zum gebündelten Auslesen aller Werte -> Dictonary mit Labeln; 
#|                  - Triggert Auslesen aller Werte und meldet, wenn Messwerte Dict zum Auslesen bereit steht, 
#|                  - Übertragen einzelner Kommandos an Labeled Module
#|-> ReglrTreiber: Lesen Messwerte aus Dict von Svens Modul, Nutzt Svens Modul zur Übertragung von Kommandos


class Regler_Dvr_ModBus(QObject):
    
    # DataReceived Signal
    sig_newMsgReceived = pyqtSignal(bytes)
    
    ARBEITSBEREICH_PUFFER = 0.0 # Bereich in %, der von zusätzlch zur HW-Ober- und Untergrenze des Nenn-Arbeitsbereichs Abstand gehalten werden soll

    def __init__(self, name, arbeitsbereich, kalibrierung, modbusCtrl):
        """
        Args:
            port (str): Bsp: "PORT_R1"
            arbeitsbereich (list(float)): Bsp: [10, 100] [g/min]
        """
        
        super().__init__()
        
        self.__instrument = None
        self.__mbCtrl = modbusCtrl
        
        # Konfiguration
        self.__name = name
        self.__arbeitsbereich = arbeitsbereich
        
        # Kalibrierung
        self.__useKalibrierung = True
        self.__kalibrierung = self.load_Kalibrierung(kalibrierung)
        self.__pVordruck = 0.0
        self.__TGas = 0.0
        
        # Aktuelle Werte
        self.__soll = 0
        self.__mess = 0
        self.__zaehler = 0 
        
        # Verbindung
        self.__ser = None
        self.connected = False
        self.busy = False

        self.__enabled = True


    """
    def _connect(self):
        
        try:
            # Überprüfung, ob noch keine Verbindung besteht
            if(self.__instrument == None or self.connected == False): 
                print (str(self.__port) + ": Starte Verbindungsaufbau-Versuch!")
                                
                # Setze Referenz auf Hardware
                self.__instrument = propar.instrument(self.__port)       
                
                # Test: Lesen des Messwertes. Fehler, wenn kein Messwert verfügbar
                if(self._read_Messwert() == None):
                    raise Exception()
                
                # Setzen der Connected Flag
                self.connected = True      
                print (str(self.__port) + ": Verbindung zum Port hergestellt!") 
                              
            return True
            
                            
        except:
            print ("Verbindung zum Port " + str(self.__port) + " konnte nicht hergestellt werden!")

            if(self.__ser != None):
                self.__ser.close()
            self.__ser = None
            self.connected = False
        
            return False  
    """        
    
    
    def load_Kalibrierung(self, kalibrierung):
        if (type(kalibrierung) == list):
            if (len(kalibrierung) == 4):
                return kalibrierung    
                
        raise Exception("Ungültiges Format für die Regler-Kalibrierung!")
        
    
    
    def set_Kalibrierung(self, kalibrierung):
        self.__kalibrierung = self.load_Kalibrierung(kalibrierung)    
    
 
 
 
    def _close(self):
        
        # Prüfe, ob Verbindung besteht
        if(self.__instrument != None):
            
            # Schließe Regler
            self._set_Sollwert(0)
            # Setze Connect Flag
            self.connected = False
            
            print(self.__port + " closed")
            return True
        
        return False



# ABFRAGEN

    def _read_Messwert(self):
        """Holt aktuellen Messwert von modbusCtrl

        Returns:
            float: Aktueller Messwert des Reglers [g/min]
        """
        
        rohWertInt = self.__mbCtrl.getValue(self.__name + "_ist")
        
        if(not wert):
            print(str(self.__name) + ": Fehler beim Lesen des Messwertes! Messwert kann nicht gelesen werden! Regler ist nicht verbunden!")
            return None
        
        else:
            valPer  = rohWertInt / 32000.0 if rohWertInt <= 41942 else (rohWertInt - 65536) / 32000.0
                        
            # Umrechnung von Prozent in g/min        
            val = None
            if(valPer != None):
                val = valPer * self.__arbeitsbereich[1]
                
                # Anwendung der Kalibrierung
                if(self.__useKalibrierung):
                    val = self.apply_Kalibrierung(val, self.__pVordruck, self.__TGas)
            
            self.__mess = val
            
            return val
    
     
     
    
    def twos_complement(self, hexstr, bits):
        value = int(hexstr, bits)
        if (value & (1 << (bits - 1))):
            value -= 1 << bits
        return value
    
    

    def apply_Kalibrierung(self, val, pVordruck, TGas):
        return self.__kalibrierung[0] + (self.__kalibrierung[1] * val) + (self.__kalibrierung[2] * pVordruck) + (self.__kalibrierung[3] * TGas)       



    def _read_Sollwert(self):
        """
        Gibt den Stellwert in [g / min] zurück
        """   
        
        valPer = self.__mbCtrl.getValue(self.__name + "_soll") / 32000.0
        
        if(not valPer):
            print(str(self.__port) + ": Fehler beim Lesen des Sollwertes! Sollwert kann nicht gelesen werden! Port ist nicht verbunden!")
            return None
            
        # Umrechnung von Prozent in g/min
        val = None
        if(valPer != None):
            val = valPer * self.__arbeitsbereich[1]
        
        return val
        
        
###########################################################################################################
#
# BEFEHLE

    def _set_Sollwert(self, soll):
        """
        Inklusive Rücklesen des Sollwertes
        @param: soll (float): stellwert in [g/min]
        """
        
        # Überprüfung auf Grenzen des Sollwertes auf Arbeitsbereich
        if((soll < self.__arbeitsbereich[0] or soll > self.__arbeitsbereich[1]) and soll != 0):
            print(str(self.__port) + ": Fehler beim Setzen des Sollwertes! Sollwert + " + str(soll) + " liegt nicht im Arbeitsbereich " + str(self.__arbeitsbereich) + " des Reglers!")
            return False
        
        # Umrechnung von g/min in Prozent des Arbeitsbereiches
        sollPer = soll / self.__arbeitsbereich[1]
        
        valInt = int(sollPer * 32000)
        
        #print (valInt)
        self.__mbCtrl.setValue(self.__name + "_soll", valInt)
            
        = # TODO: Check Antwort !!!
        
        readSoll = round(self.__mbCtrl.getValue(self.__name + "_soll") / self.__arbeitsbereich[1] * 32000)
        
        if(readSoll == valInt):
            return True
        else:
            return False
                    
    
# Driver Setter

    def set_enabled(self, enabled):
        """Hat keine Auswirkungen auf Messungen! Einzig für spätere Verwendung benötigt.
        
        Args:
            enabled (_type_): Flag, ob Regler verwendet wird oder nicht.
        """
        self.__enabled = enabled
          

    def set_current_pVordruck(self, pVordruck):
        self.__pVordruck = pVordruck
        
        
    def set_current_TGas(self, TGas):
        self.__TGas = TGas

        


# Getter

    def get_name(self):
        return self.__name
    
        
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
            f.write(str(i) + " -> " + str(h) + " -> " +  str(Regler_Dvr_ModBus.twos_complement(None, h, 16)) + "\n")

        