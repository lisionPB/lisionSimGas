from PyQt5.QtCore import QObject, pyqtSignal
    
import time

import reglerSetup
import gesamtSollwertRegler
import consoleWidget as cw
import datamanager as dm

import exportConfig

class Pruefung(QObject):
    """
    Ablaufsteuerung der Prüfung
    """
    
    PRUEF_STATE_FAILURE = -1
    PRUEF_STATE_SETUP = 0
    PRUEF_STATE_RUNNING = 2
    PRUEF_STATE_STARTING = 2.1
    PRUEF_STATE_ENDING = 2.2
    PRUEF_STATE_DONE = 3

    _sig_pruefCanceled = pyqtSignal()
    _sig_pruefFinalized = pyqtSignal()
    _sig_pruefEnded = pyqtSignal()
    _sig_recordingEnded = pyqtSignal()
    
    DEFAULT_ZEIT_START = 10000 # ms
    DEFAULT_ZEIT_ENDE =  10000 # ms
    
    def __init__(self, rs, sms, gesZeit, gesMenge, startZeit):
        """
        Initialisierung der Prüfung

        Args:
            rs (ReglerSetup): zugrunde liegende HW-Configuration
        """
        
        super().__init__()
        
        self._state = self.PRUEF_STATE_SETUP
        
        self._rs = rs
        self._sms = sms
        self._gsr = gesamtSollwertRegler.GesamtSollwertRegler(gesZeit, gesMenge, startZeit)
        
        # Verbindung: Neuer Messwert -> Update der Prüfung
        self._rs.sig_newIntegralData.connect(self.update_pruefung) 
        
        # Bestimme regelmäßigen Fluss, um Menge über Zeit zu erreichen
        fluss = gesMenge / gesZeit
        
        # Bestimme ReglerAuswahl
        self._reglerAuswahl = self._rs.calc_reglerAuswahl(fluss)
        self._rs.set_reglerAuswahl(self._reglerAuswahl)
        self._reglerAuswahlArbeitsBereichMax = self.calc_gesArbeitsBereichMax()
        exportConfig.Y_MAX_REGLER = int(self._reglerAuswahlArbeitsBereichMax * 1.05)
        
        self.__gesZeit = gesZeit
        self.__gesMenge = gesMenge
        
        self.__recordStartTime = None
        self.__startTime = 0
        self.__recordEndTime = None
        

    def start_aufzeichnung(self):
        self.__recordStartTime = time.time()
        self.__recordEndTime = None

        
    def prepare_pruefung(self):
        """
        Bereitet die Prüfung mit den gesetzten Einstellungen vor.
        Kein Starten des Timers bis zum Start der eigentlichen Prüfung !!! -> pruefWidget
        """
                    
        """
        # Prüfe, ob Sicherheitsmagnetventile manuell geöffnet wurde
        if(not self._sms.is_sms_open_any()):
            self._rs.protokoll.append(cw.ProtokollEintrag("Sicherheitsmagnetventil nicht geöffnet! Prüfung wird nicht gestartet!", typ=cw.ProtokollEintrag.TYPE_FAILURE))
            return False
        """
        
        # Prüfe auf gültige Reglerkonfiguration        
        if(not self._reglerAuswahlArbeitsBereichMax > 0):
            self._rs.protokoll.append(cw.ProtokollEintrag("Einströmung kann nicht gestartet werden! Prüfdurchfluss nicht im Arbeitsbereich!", typ=cw.ProtokollEintrag.TYPE_FAILURE))
            return False
 
            
        for p in self._rs._ports:
            self._rs._ports[p].start_Integration()
        self._gsr.start_Regler(self._reglerAuswahl, log=False)
        anteil = self._gsr.calc_stellwert(0, True) / self._reglerAuswahlArbeitsBereichMax

        if (anteil > 0):
            
            # Prüfung kann gestartet werden
            
            # Messungen starten
            self._rs.set_paused(False)
            # STATE auf RUNNING setzen
            self._state = self.PRUEF_STATE_STARTING
            
            return True
        
        return False
        
        
    def start_pruefung(self):
        """
        Starte die tatsächliche Prüfung (nach Vorlaufzeit):
        Startet den Gesamtsollwertregler
        
        """
        if(self._reglerAuswahlArbeitsBereichMax > 0):
            for p in self._rs._ports:
                self._rs._ports[p].start_Integration()
            stellwert = self._gsr.start_Regler(self._reglerAuswahl)
            
            # Erstes Setzen des Sollwertes            
            anteil = stellwert / self._reglerAuswahlArbeitsBereichMax
            
            if(anteil >= 0):
                # Reglerstellwerte müssen aktualisiert werden.
                if(not self._rs.set_GesamtSollWert(anteil, self._reglerAuswahl)):
                    self._rs.protokoll.append(cw.ProtokollEintrag("Fehler beim Setzen des Gesamtsollwertes! Prüfung wird nicht gestartet!", typ=cw.ProtokollEintrag.TYPE_FAILURE))
                    return False
            else:
                return False
            
            # Startzeit setzen
            self.__startTime = time.time()
            # Prüfstate setzen
            self._state = self.PRUEF_STATE_RUNNING
            
            return True
        
        else:
            # TODO: Ausgabe, dass Prüfung nicht gestartet werden kann, weil keine Reglerkonfig
            # print ("Prüfvorgaben können nicht mit Regler-Konfiguration abgebildet werden. Prüfung wird nicht gestartet!")
            self._rs.protokoll.append(cw.ProtokollEintrag("Prüfung konnte nicht gestartet werden. Prüfvorgaben können nicht mit Regler-Konfiguration abgebildet werden. Prüfung wird nicht gestartet!", typ=cw.ProtokollEintrag.TYPE_FAILURE))

        
        return False
        
        
        
        
        
    def cancel_pruefung(self):
        if(not self._rs.set_allClosed()):
            self._rs.protokoll.append(cw.ProtokollEintrag("ACHTUNG! Automatisches Schließen der Regler fehlgeschlagen!", typ=cw.ProtokollEintrag.TYPE_FAILURE))

        # Setze alle geplante Zuschaltungen der Flaschen auf False
        self._sms.clear_sms_zuschaltungen()
        # Schließe alle Ventile
        self._sms.write_sms_zuschaltungen()

        self._state = self.PRUEF_STATE_FAILURE        
        self._sig_pruefCanceled.emit()
        
        
    
    
    def finalize_pruefung(self):
        self._state = self.PRUEF_STATE_ENDING
        # Schließe alle Regel-Stellglieder
        if(not self._rs.set_allClosed()):
            self._rs.protokoll.append(cw.ProtokollEintrag("ACHTUNG! Automatisches Schließen der Regler fehlgeschlagen!", typ=cw.ProtokollEintrag.TYPE_FAILURE))            

        gasmengen = {}
        zaehlerSum = {}
        for p in self._rs._ports:
            gasmengen[p] = self._rs._ports[p].get_integrierteMenge()  
            zaehlerSum[p] = self._rs._ports[p].get_cnt()

        self._gsr.finalize_Regler(gasmengen, zaehlerSum)
        
        # Messungen pausieren
        # self._rs.set_paused(True)
        
        print ("Prüfung wird abgeschlossen ...")
        self._rs.protokoll.append(cw.ProtokollEintrag("Gesamtfluss: " + str(round(self._gsr.totalFlowSum, 2)) + "g", typ=cw.ProtokollEintrag.TYPE_STANDARD))    
        
        self._sig_pruefFinalized.emit() # not used?!
        
        
    
    def end_pruefung(self):
        """
        Abschließende Vorgänge
        """
        
        # Setze alle geplante Zuschaltungen der Flaschen auf False
        self._sms.clear_sms_zuschaltungen()
        # Schließe alle Ventile
        self._sms.write_sms_zuschaltungen()
        

        self._state = self.PRUEF_STATE_DONE
        self._sig_pruefEnded.emit()

    
    def stop_aufzeichnung(self):
        self.__recordStartTime = None
        self.__recordEndTime = self._rs.get_datamanager().get_LastTime()
    
        
    def update_pruefung(self):
        """Aktualisiert die Regler der Prüfung, inklusive Setzen neuer Sollwerte

        Args:
            data (dict): Dictionary mit Messdaten
        """
        
        if(self._state == self.PRUEF_STATE_RUNNING):
            
            try:
                # extrahiere Regler-Messwerte     
                busy = False
                flows = {}
                gasmengen = {}
                zahlerwerte = {}
                for p in self._rs._ports:
                    flows[p] = self._rs._ports[p].get_ist()
                    gasmengen[p] = self._rs._ports[p].get_integrierteMenge()
                    zahlerwerte[p] = self._rs._ports[p].get_cnt()

                # print(time.time())
                # print(gasmengen)
            
                anteil = -1
                
                # FlowSum aktiver Regler
                flowSum = 0
                for p in self._reglerAuswahl:
                    flowSum += flows[p]
                
                if(not busy):
                    anteil = self._gsr.update_Regler(flowSum, gasmengen, zahlerwerte) / self._reglerAuswahlArbeitsBereichMax
                  
                if(anteil >= 0):
                    # Reglerstellwerte müssen aktualisiert werden.
                    # print("Update Stellglieder")
                    if(not self._rs.set_GesamtSollWert(anteil, self._reglerAuswahl, pruefung=True)):
                        self._rs.protokoll.append(cw.ProtokollEintrag("ACHTUNG! Reglerstellwert liegt außerhalb des Arbeitsbereichs!", typ=cw.ProtokollEintrag.TYPE_WARNING))
                        # raise Exception("2")
                    
            except Exception as e:
                print (e)
                self._rs.protokoll.append(cw.ProtokollEintrag("Verbindungsverlust! Prüfung wird abgebrochen!", typ=cw.ProtokollEintrag.TYPE_FAILURE))
                self.cancel_pruefung()
                
            
            
        
        
    def calc_gesArbeitsBereichMax(self) -> float:
        """
        Bestimmt den maximalen Stellwert der gesetzten Reglerauswahl
        """
        
        abSum = 0
        for r in self._reglerAuswahl:
            abSum += self._reglerAuswahl[r]
        return abSum


    def get_gesZeit(self):
        return self.__gesZeit
    
    def get_gesMenge(self):
        return self.__gesMenge
    
    def get_pruefLaufZeit(self):
        return time.time() - self.__startTime
    
    def get_pruefLaufMenge(self):
        return self._gsr.totalFlowSum
    
    def get_pruefCurrentFlowSum(self):
        """
        Summierte Intgrale über Flüsse der in der Prüfung aktiven Regler
        """
        return self._gsr.lastFlow
    
    def get_pruefCurrentMassSum(self):
        """
        Summierte Zaehlerwerte der in der Prüfung aktiven Regler
        """
        return self._gsr.lastMassSum

    def get_recordEndTime(self):
        return self.__recordEndTime
    

    def is_busy(self):
        return (self._state == self.PRUEF_STATE_STARTING) or (self._state == self.PRUEF_STATE_RUNNING) or (self._state == self.PRUEF_STATE_ENDING)
    
    def is_recording(self):
        return self.__recordStartTime is not None