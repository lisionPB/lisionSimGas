"""
GUI-Klasse zum Nullabgleich der Regelstellglieder
"""

from PyQt5.QtWidgets import QDialog, QLabel, QVBoxLayout, QHBoxLayout, QGroupBox, QDoubleSpinBox, QPushButton, QProgressBar

import PyQt5.QtCore

from PyQt5.QtGui import (QIcon, QPixmap, QFont)
from PyQt5.QtCore import (Qt, QTimer)


import nullAbgleich as na

class ReglerConfigNullUI(QDialog):


    def __init__(self, sgr):
        super().__init__()
        self.sgr = sgr
  
        layout = QVBoxLayout()
        self.setLayout(layout)
  
        self.setWindowTitle("Nullpunktabgleich")

        # Konfig
        # Gruppe aller Regelstellglieder
        self.reglerConfigGroup = ReglerConfigGroup(sgr)
        layout.addWidget(self.reglerConfigGroup)

        closeGroup = QGroupBox()
        closeLayout = QHBoxLayout()
        closeGroup.setLayout(closeLayout)
        layout.addWidget(closeGroup)
        
        # Layout 
        closeLayout.addStretch(1) 
        
        # Fenster Schließen
        self.pbCancelConfig = QPushButton("Schließen")
        self.pbCancelConfig.clicked.connect(self.close)
        closeLayout.addWidget(self.pbCancelConfig)
  
    
  
class ReglerConfigGroup(QGroupBox):
    def __init__(self, sgr):
        super().__init__("Nullpunktabgleich")
        self.sgr = sgr
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        self.rcrs = {}
        for r in sgr._ports:
            rcr = ReglerConfigNullRow(sgr._ports[r])
            self.rcrs[r] = rcr
            layout.addWidget(rcr)
            
    def getConfig(self):
        conf = {}
        for r in self.rcrs:
            conf[r] = [self.rcrs[r].sMin.value(), self.rcrs[r].sMax.value(), self.rcrs[r].sPX0.value(), self.rcrs[r].sPX1.value(), self.rcrs[r].sPX2.value(), self.rcrs[r].sPX3.value()]
            
        return conf
            
  

  
class ReglerConfigNullRow(QGroupBox):
    def __init__(self, r):
        
        super().__init__()
        
        self.r = r # Regler
        
        layout = QHBoxLayout()
        self.setLayout(layout)
        
        
        # Name
        lName = QLabel(r.get_name())
        layout.addWidget(lName)
        
        # Arbeitsbereich MIN und MAX
        lMin = QLabel("Min")
        layout.addWidget(lMin)
        
        self.sMin = QDoubleSpinBox()
        self.sMin.setMinimum(0.00)
        self.sMin.setMaximum(10000.00)
        self.sMin.setSingleStep(0.01)
        self.sMin.setValue(self.r.get_arbeitsBereich_min())
        self.sMin.setEnabled(False)
        layout.addWidget(self.sMin)
        
        lMax = QLabel("Max")
        layout.addWidget(lMax)
        
        self.sMax = QDoubleSpinBox()
        self.sMax.setMinimum(0.00)
        self.sMax.setMaximum(10000.00)
        self.sMax.setSingleStep(0.01)
        self.sMax.setValue(self.r.get_arbeitsBereich_max())
        self.sMax.setEnabled(False)
        layout.addWidget(self.sMax)
        
        # Button
        pbAbgleich = QPushButton("Abgleich durchführen")
        pbAbgleich.clicked.connect(self.openAbgleichDialog)
        layout.addWidget(pbAbgleich)
        
    
    def openAbgleichDialog(self):
        ad = AbgleichDialog(self.r)
        ad.exec()
        
        
        
        
class AbgleichDialog(QDialog):
    
    def __init__(self, _r):
        super().__init__()
        
        self.__na = na.NullAbgleich(_r)
        
        
        # Fenster Titelleiste
        self.setWindowTitle("Nullpunktabgleich")
        self.setWindowIcon(QIcon('symbols/lision.ico'))
        
        # Deaktiviere Help-Button des Fensters
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        
        # Ausblenden des Schließbuttons
        self.setWindowFlags(PyQt5.QtCore.Qt.FramelessWindowHint)
        
        
        layout = QVBoxLayout()        
        self.setLayout(layout)
        
        # Titel
        titel = QLabel("Nullabgleich:")
        titel.setFont(QFont('Arial', 18))
        layout.addWidget(titel)
        
        # Text
        message = QLabel("Bitte Ventile vor und hinter Regler schließen, dann Nullabgleich starten! \n\n Der Nullabgleich kann mehrere Minuten dauern. Andere Funktionen werden solange blockiert.")
        layout.addWidget(message)
        
        
        # Bild
        bildLabel = QLabel("")
        bildLabel.setGeometry(0, 0, 256, 256)
        bildBild = QPixmap("symbols/nullabgleich_haehne.png")
        bildLabel.setPixmap(bildBild)
        layout.addWidget(bildLabel)
    
    
        # Button Nullabgleich druchführen
        self.pbDurchfuehren = QPushButton("Nullabgleich durchführen")
        self.pbDurchfuehren.clicked.connect(self.start_abgleich)
        layout.addWidget(self.pbDurchfuehren)
        
        
        # Fortschritt Status
        self.statusLabel = QLabel("")
        layout.addWidget(self.statusLabel)
        
        
        # Button Schließen
        self.pbClose = QPushButton("Schließen")
        self.pbClose.clicked.connect(self.closeEvent)
        layout.addWidget(self.pbClose)
        
        
        # Aktualisierung
        self.updateTimer = QTimer()
        self.updateTimer.setInterval(100)
        self.updateTimer.timeout.connect(self.update)
        self.updateTimer.start()
        
            
    def start_abgleich(self):
        self.__na.start()
        self.set_functionsLocked(lock=False)
    
        
    def set_functionsLocked(self, lock):
        """
        setzt entsprechende Flags, um die Funktionalitäten während eines Abgleichs einzuschränken, um 
        Ablauf des Abgleichs nicht zu stören.

        Args:
            lock (bool): True setzen, um Funktionen zu disablen
        """
        self.pbClose.setEnabled(not lock)
        self.pbDurchfuehren.setEnabled(not lock)
            
        
    def update(self):
        state = self.__na.updateCalibration()
        
        if(state != (na.STATE_RUNNING or na.STATE_INIT or na.STATE_READY)):
            self.set_functionsLocked(lock=False)

            if(state == na.STATE_DONE):
                self.statusLabel.setText("Nullabgleich abgeschlossen.")
            elif(state == na.STATE_ERROR):
                self.statusLabel.setText("Nullabgleich fehlgeschlagen!")
            elif(state == na.STATE_IDLE):
                self.statusLabel.setText("Bereit.")
                
        else:
            self.set_functionsLocked(lock=True)
            self.statusLabel.setText("Nullabgleich läuft. Bitte warten ...")
            
        
    
    def closeEvent(self, event):
        self.close()
        
        