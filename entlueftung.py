from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QIcon

import consoleWidget as cw

class Entlueftung(QObject):
    
    DEFAULT_ENTLUEFTUNGSZEIT = 15   # s
    
    sig_entlueftung_finished = pyqtSignal()
    
    def __init__(self, sgr, sms):
        super().__init__()
        self.sgr = sgr
        self.sms = sms

        self._timer = QTimer()

    
    def initEntlueftung(self):
        
        msgBoxReg = QMessageBox()
        msgBoxReg.setWindowIcon(QIcon('symbols/lision.ico'))
        msgBoxReg.setIcon(QMessageBox.Warning)
        msgBoxReg.setText("Achtung! Schließen Sie alle Gasflaschen bevor Sie fortfahren!")
        msgBoxReg.setWindowTitle("Entlüftungsvorgang starten")
        msgBoxReg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        
        returnValue = msgBoxReg.exec()
        
        if returnValue == QMessageBox.Ok:
            self.startEntlueftung()
            
            
    
    def startEntlueftung(self):
        print("Entlüftungsvorgang läuft...")
        self.sgr.protokoll.append(cw.ProtokollEintrag("Entlüftungsvorgang gestartet.", typ=cw.ProtokollEintrag.TYPE_SUCCESS))
        self._timer.setInterval(self.DEFAULT_ENTLUEFTUNGSZEIT * 1000)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.stopEntlueftung)
        self._timer.start()
        
        # Magnetventile öffnen
        for s in self.sms.zuschaltung:
            self.sms.set_sms_zuschaltung(s, True)
        self.sms.write_sms_zuschaltungen()
        
        # Regler öffnen
        self.sgr.set_allOpen()
        
    
    def stopEntlueftung(self):
        
        # Magnetventile schließen
        for s in self.sms.zuschaltung:
            self.sms.set_sms_zuschaltung(s, False)
        self.sms.write_sms_zuschaltungen()
        
        # Regler schließen
        self.sgr.set_allClosed()
         
        print("Entlüftungsvorgang abgeschlossen.")
        self.sgr.protokoll.append(cw.ProtokollEintrag("Entlüftungsvorgang abgeschlossen.", typ=cw.ProtokollEintrag.TYPE_SUCCESS))
        self.sig_entlueftung_finished.emit()
        