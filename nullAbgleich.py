"""
Ablaufsteuerung zum Nullpunktabgleich der Regelstellglieder  
    
"""
import time
import regler_dvr as rdw

import propar

NULLABGLEICH_RUHEZEIT = 10.0  # [s]

STATE_ERROR = -1
STATE_IDLE = 0
STATE_INIT = 1
STATE_READY = 2
STATE_RUNNING = 3
STATE_DONE = 4



class NullAbgleich():
    """
    Ablaufsteuerung und Kommunikation (Senden der Befehle + Auslesen des Status) mit der Hardware.
    Basiert auf StateMachine
    """
    def __init__(self, r: rdw.Regler_Dvr):
        # Initi
        self._state = STATE_IDLE
        self._r = r
        
        
    # Zustandsabfragen
        
    def isRunning(self):
        return self._state != STATE_IDLE and self._state != STATE_DONE and self._state != STATE_ERROR
    
    
    def isIdle(self):
        return self._state == STATE_IDLE
    
    
    def isComplete(self):
        return self._state == STATE_DONE
    
    
    def isFailed(self):
        return self._state == STATE_ERROR
    
    
    ### 
    # Ablaufsteuerung
        
    def start(self):
        self._state = STATE_INIT
        
        
        
    def initCalibration(self):
        """
        Bereitet den Kalibrierungsvorgang vor
        1. Set fSetpoint to 0
        2. Unlock secured parameters -> Set InitReset to 64
        3. Enable calibration mode -> Set control mode to 9
        4. Reset calibration mode -> Set calibration mode to 0
        """        
        
        print("init...")
        
        #1.        
        if(not self._r.writeParameter(9, 0)):
            return self.abortInitCalibration(1)

        #2.
        if(not self._r.writeParameter(7, 64)):
            return self.abortInitCalibration(2)
        
        #3.
        if(not self._r.writeParameter(12, 9)):
            return self.abortInitCalibration(3)
                        
        #4.
        if(not self._r.writeParameter(58, 0)):
            return self.abortInitCalibration(4)

        
        self._state = STATE_READY
        return True
        
        
        
    
    def abortCalibrationOnError(self, step):        
        print (f"Abbruch der Initialisierung der Kalibrierung bei Schritt {step}")
        self._state = STATE_ERROR    
        return False
        
    
    
    
    def startCalibration(self):
        
        if(self._state == STATE_READY):
            print("start...")
            # Sende Start
            if(not self._r.writeParameter(58, 9)):
                return self.abortInitCalibration("'start calibration'")
            
            self._state = STATE_RUNNING    
    
    
    
    def updateCalibration(self):
        
        if(self._state == STATE_INIT):
            self.initCalibration()
            
        if(self._state == STATE_READY):
            self.startCalibration()
                       
        if(self._state == STATE_RUNNING):   
            self.checkCalibrationComplete()
        
        return self._state
    
    
    
    def checkCalibrationComplete(self):
        antwort = self._r.readParameter(58)
        # print (antwort)
        if(antwort == 0):
            # Lock secured params -> init reset to dec.82 (hex.52)
            self._r.writeParameter(7, 82)
            print ("Kalibrierung abgeschlossen.")
            self._state = STATE_DONE
        elif(antwort == 255):#
            print
            self._r.writeParameter(7, 82)
            print ("Kalibrierung fehlgeschlagen! Vorgang wiederholen!")
            self._state = STATE_ERROR            