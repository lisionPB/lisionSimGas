from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QIcon

import consoleWidget as cw

class Befuellen(QObject):
    
    DEFAULT_BEFUELLUNGSZEIT = 5     # s
    DEFAULT_BERUHIGUNGSZEIT = 10    # Am Ende erst Regler dann Magnetventile
    
    sig_befuellung_finished = pyqtSignal()
    
    def __init__(self, sgr, sms):
        super().__init__()
        self.sgr = sgr
        self.sms = sms

        self._timer = QTimer()
        self._timer_abschluss = QTimer()    # 

    
    def initBefuellung(self):
        
        msgBoxReg = QMessageBox()
        msgBoxReg.setWindowIcon(QIcon('symbols/lision.ico'))
        msgBoxReg.setIcon(QMessageBox.Warning)
        msgBoxReg.setText("Achtung! Bitte alle Gasflaschen zur Befüllung der Anlage öffnen!\nVorsicht: Kurzzeitiger Gasaustritt am Reglerausgang!")
        msgBoxReg.setWindowTitle("Befüllungsvorgang starten")
        msgBoxReg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        
        returnValue = msgBoxReg.exec()
        
        if returnValue == QMessageBox.Ok:
            self.startBefuellung()
            return True
        
        return False
            
            
    
    def startBefuellung(self):
        print("Befüllungsvorgang läuft...")
        self.sgr.protokoll.append(cw.ProtokollEintrag("Befüllungsvorgang gestartet.", typ=cw.ProtokollEintrag.TYPE_SUCCESS))
        self._timer.setInterval(self.DEFAULT_BEFUELLUNGSZEIT * 1000)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.schliesseRegler)
        self._timer.start()
        
        # Magnetventile öffnen, Nur die die auch angeschlossen sind!
        for s in self.sms.zuschaltung:
            if(self.sms.checkFlaschenZuschaltung(s, checkDiffDruck=False)):
                self.sms.set_sms_zuschaltung(s, True)
            else:
                self.sms.set_sms_zuschaltung(s, False)
        self.sms.write_sms_zuschaltungen()
        
        # Regler öffnen
        self.sgr.set_allOpen(0.10)
        
        
    def schliesseRegler(self):
        # Regler schließen
        self.sgr.set_allClosed()
        
        # Timer bis zum Ende der Befüllung
        self._timer_abschluss.setInterval(self.DEFAULT_BERUHIGUNGSZEIT * 1000)
        self._timer_abschluss.setSingleShot(True)
        self._timer_abschluss.timeout.connect(self.stopBefuellung)
        self._timer_abschluss.start()
    
    
    
    def stopBefuellung(self):
        
        # Magnetventile schließen
        for s in self.sms.zuschaltung:
            self.sms.set_sms_zuschaltung(s, False)
        self.sms.write_sms_zuschaltungen()
         
        print("Befüllungsvorgang abgeschlossen.")
        self.sgr.protokoll.append(cw.ProtokollEintrag("Befüllungsvorgang abgeschlossen.", typ=cw.ProtokollEintrag.TYPE_SUCCESS))
        self.sig_befuellung_finished.emit()
        