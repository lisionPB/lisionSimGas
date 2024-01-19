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
    
    def __init__(self, rs, sms, gesZeit, gesMenge, totZeit, initFaktor):
        """
        Initialisierung der Prüfung

        Args:
            rs (ReglerSetup): zugrunde liegende HW-Configuration
        """
        
        super().__init__()
        
        self._state = self.PRUEF_STATE_SETUP
        
        self._rs = rs
        self._sms = sms
        self._gsr = gesamtSollwertRegler.GesamtSollwertRegler(gesZeit, gesMenge, totZeit, initFaktor)
        
        # Bestimme regelmäßigen Fluss, um Menge über Zeit zu erreichen
        fluss = gesMenge / gesZeit
        
        # Bestimme ReglerAuswahl
        self._reglerAuswahl = self._rs.calc_reglerAuswahl(fluss)
        self._reglerAuswahlArbeitsBereichMax = self.calc_gesArbeitsBereichMax()
        
        self.__gesZeit = gesZeit
        self.__gesMenge = gesMenge
        
        self.__startTime = 0
        
        
        
    def prepare_pruefung(self):
        """
        Bereitet die Prüfung mit den gesetzten Einstellungen vor.
        Öffnet das Sicherheitsventil, um den Vordruck aufzubauen, wenn Konfiguration gültig.
        Kein Starten des Timers bis zum Start der eigentlichen Prüfung !!! -> pruefWidget
        """
        
        if(self._reglerAuswahlArbeitsBereichMax > 0):
            self._gsr.start_Regler(log=False)
            anteil = self._gsr.calc_stellwert(0) / self._reglerAuswahlArbeitsBereichMax
            
            print (anteil)
            
            if (anteil > 0):
                # Prüfung kann gestartet werden
                # Öffne Sicherheitsventil
                self._sms.set_sms_open(True)
                
                # Messungen starten
                self._rs.set_paused(False)
                # STATE auf RUNNING setzen
                self._state = self.PRUEF_STATE_STARTING
                
                return True
        
        # Keine Gültige Reglerkonfiguration
        return False
       
        
    def start_pruefung(self):
        """
        Starte die Prüfung:
        Startet den Gesamtsollwertregler
        Setze ersten Stellwert (intern multipliziert mit initFaktor)
        
        """
        if(self._reglerAuswahlArbeitsBereichMax > 0):
            stellwert = self._gsr.start_Regler()
            
            # Erstes Setzen des Sollwertes            
            anteil = stellwert / self._reglerAuswahlArbeitsBereichMax
            
            if(anteil >= 0):
                # Reglerstellwerte müssen aktualisiert werden.
                if(not self._rs.set_GesamtSollWert(anteil, self._reglerAuswahl)):
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
        self._sms.set_sms_open(False)   
        
        # Messungen pausieren
        # self._rs.set_paused(True)

        self._state = self.PRUEF_STATE_FAILURE        
        self._sig_pruefCanceled.emit()
        
        
    
    
    def finalize_pruefung(self):
        self._state = self.PRUEF_STATE_ENDING
        # Schließe alle Regel-Stellglieder
        if(not self._rs.set_allClosed()):
            self._rs.protokoll.append(cw.ProtokollEintrag("ACHTUNG! Automatisches Schließen der Regler fehlgeschlagen!", typ=cw.ProtokollEintrag.TYPE_FAILURE))            

        self._gsr.finalize_Regler()
        
        # Messungen pausieren
        # self._rs.set_paused(True)
        
        print ("Prüfung beendet.")
        self._rs.protokoll.append(cw.ProtokollEintrag("Prüfung abgeschlossen! Gesamtfluss: " + str(self._gsr.totalFlowSum), typ=cw.ProtokollEintrag.TYPE_SUCCESS))    
        
        self._sig_pruefFinalized.emit()
        
        
    
    def end_pruefung(self):
        """
        Abschließendes Schließen des Magnetventils
        """
        self._state = self.PRUEF_STATE_DONE
        self._sms.set_sms_open(False)
        self._sig_pruefEnded.emit()
    
        
    def update_pruefung(self, data):
        """Aktualisiert die Regler der Prüfung

        Args:
            data (dict): Dictionary mit Messdaten
        """
        
        if(self._state == self.PRUEF_STATE_RUNNING):
            
            try:
                # extrahiere Regler-Messwerte     

                busy = False
                messwerte = {}  # Lege Frame an
                for p in self._rs._ports:
                    if(p in data):
                        if(data[p] != "BUSY"):
                            messwerte[p] = data[p]  # Schreibe Messwert in Frame
                        else:
                            busy = True
                    else:
                        raise Exception("1")
                        
                messwerte[dm.DataManager.TIME_LABEL] = data[dm.DataManager.TIME_LABEL]        
            
                anteil = -1
                if(not busy):
                    anteil = self._gsr.update_Regler(messwerte) / self._reglerAuswahlArbeitsBereichMax
                
                if(anteil >= 0):
                    # Reglerstellwerte müssen aktualisiert werden.
                    print("Update Stellglieder")
                    if(not self._rs.set_GesamtSollWert(anteil, self._reglerAuswahl, pruefung=True)):
                        raise Exception("2")
                    
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
