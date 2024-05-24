from PyQt5.QtCore import QObject, pyqtSignal
    
import time

import reglerSetup
import gesamtSollwertRegler
import consoleWidget as cw
import datamanager as dm

class Pruefung(QObject):
    """
    Ablaufsteuerung der Prüfung
    """
    
    PRUEF_STATE_FAILURE = -1
    PRUEF_STATE_SETUP = 0
    PRUEF_STATE_READY = 1
    PRUEF_STATE_RUNNING = 2
    PRUEF_STATE_STARTING = 2.1
    PRUEF_STATE_ENDING = 2.2
    PRUEF_STATE_DONE = 3

    _sig_pruefCanceled = pyqtSignal()
    _sig_pruefFinalized = pyqtSignal()
    _sig_pruefEnded = pyqtSignal()
    
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
        
        self.__gesZeit = gesZeit
        self.__gesMenge = gesMenge
        
        self.__startTime = 0
        
        
        
    def prepare_pruefung(self):
        """
        Bereitet die Prüfung mit den gesetzten Einstellungen vor.
        Prüft, ob Sicherheitsmagnetventil offen
        Kein Starten des Timers bis zum Start der eigentlichen Prüfung !!! -> pruefWidget
        """
                    
        # Prüfe, ob Sicherheitsmagnetventil geöffnet wurde
        if(not self._sms.is_sms_open()):
            self._rs.protokoll.append(cw.ProtokollEintrag("Sicherheitsmagnetventil nicht geöffnet! Prüfung wird nicht gestartet!", typ=cw.ProtokollEintrag.TYPE_FAILURE))
            return False
        
        
        # Prüfe auf gültige Reglerkonfiguration        
        if(not self._reglerAuswahlArbeitsBereichMax > 0):
            self.sgr.protokoll.append(cw.ProtokollEintrag("Prüfung konnte nicht gestartet werden! Prüf-Konfiguration überprüfen!", typ=cw.ProtokollEintrag.TYPE_FAILURE))
            return False
            
            
            
        for p in self._rs._ports:
            self._rs._ports[p].start_Integration()
        self._gsr.start_Regler(self._reglerAuswahl, log=False)
        anteil = self._gsr.calc_stellwert(0, True) / self._reglerAuswahlArbeitsBereichMax
        
        # print (anteil)           
        
        if (anteil > 0):
            # Prüfung kann gestartet werden
            
            # Messungen starten
            self._rs.set_paused(False)
            # STATE auf RUNNING setzen
            self._state = self.PRUEF_STATE_STARTING
            
            return True
            
            
        
        
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
            self._startTime = time.time()
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

        self._state = self.PRUEF_STATE_FAILURE        
        self._sig_pruefCanceled.emit()
        
        
    
    
    def finalize_pruefung(self):
        self._state = self.PRUEF_STATE_ENDING
        # Schließe alle Regel-Stellglieder
        if(not self._rs.set_allClosed()):
            self._rs.protokoll.append(cw.ProtokollEintrag("ACHTUNG! Automatisches Schließen der Regler fehlgeschlagen!", typ=cw.ProtokollEintrag.TYPE_FAILURE))            

        gasmengen = {}
        for p in self._rs._ports:
            gasmengen[p] = self._rs._ports[p].get_integrierteMenge()  

        self._gsr.finalize_Regler(gasmengen)
        
        # Messungen pausieren
        # self._rs.set_paused(True)
        
        print ("Prüfung beendet.")
        self._rs.protokoll.append(cw.ProtokollEintrag("Prüfung abgeschlossen! Gesamtfluss: " + str(round(self._gsr.totalFlowSum, 2)) + "g", typ=cw.ProtokollEintrag.TYPE_SUCCESS))    
        
        self._sig_pruefFinalized.emit()
        
        
    
    def end_pruefung(self):
        """
        Abschließende Vorgänge
        """
        self._state = self.PRUEF_STATE_DONE
        self._sig_pruefEnded.emit()
        
    
        
    def update_pruefung(self):
        """Aktualisiert die Regler der Prüfung, inklusive Setzen neuer Sollwerte

        Args:
            data (dict): Dictionary mit Messdaten
        """
        
        if(self._state == self.PRUEF_STATE_RUNNING):
            
            try:
                # extrahiere Regler-Messwerte     
                busy = False
                gasmengen = {}
                for p in self._rs._ports:
                    gasmengen[p] = self._rs._ports[p].get_integrierteMenge()  

                # print(time.time())
                # print(gasmengen)
            
                anteil = -1
                if(not busy):
                    anteil = self._gsr.update_Regler(gasmengen) / self._reglerAuswahlArbeitsBereichMax
                  
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
        zeit = self._rs.get_datamanager().get_LastTime()
        if(zeit != None):
            return zeit
        else:
            print ("LastTime NONE !!!")
            return 0
    
    def get_pruefLaufMenge(self):
        return self._gsr.totalFlowSum
    
    def get_pruefCurrentFlowSum(self):
        return self._gsr.lastFlow
