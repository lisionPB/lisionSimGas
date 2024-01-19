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
        self.reglerConfigGroup = ReglerConfigGroup(sgr)
        layout.addWidget(self.reglerConfigGroup)

        # Schließen
        closeGroup = QGroupBox()
        closeLayout = QHBoxLayout()
        closeGroup.setLayout(closeLayout)
        layout.addWidget(closeGroup)
        
        closeLayout.addStretch(1) 
        
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
        
        self.__r = _r # Regler
        self.__na = na.NullAbgleich()
        
        
        # Fenster Titelleiste
        self.setWindowTitle("Nullpunktabgleich")
        self.setWindowIcon(QIcon('symbols/lision.ico'))
        
        # Deaktiviere Help-Button des Fensters
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        
        
        layout = QVBoxLayout()        
        self.setLayout(layout)
        
        # Titel
        titel = QLabel("Nullabgleich:")
        titel.setFont(QFont('Arial', 18))
        layout.addWidget(titel)
        
        # Text
        message = QLabel("Bitte Ventile vor und hinter Regler schließen, dann Nullabgleich starten!")
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
        
        
        # Processbar 
        self.barProcess = QProgressBar()
        layout.addWidget(self.barProcess)
        
        
        # Button Schließen
        self.pbClose = QPushButton("Schließen")
        self.pbClose.clicked.connect(self.closeEvent)
        layout.addWidget(self.pbClose)
        
        
        # Aktualisierung
        self.updateTimer = QTimer()
        self.updateTimer.setInterval(10)
        self.updateTimer.timeout.connect(self.update_processbar)
        self.updateTimer.start()
        
            
    def start_abgleich(self):
        self.__na.start()
        self.pbDurchfuehren.setEnabled(False)
        self.pbClose.setText("Abbrechen")
    
        
    def update_processbar(self):
        val = self.__na.update_and_get_process()
        self.barProcess.setValue((int)(val * 100))
        if(self.__na.state == na.STATE_DONE):
            self.pbClose.setText("Schließen")
            self.pbDurchfuehren.setEnabled(True)
        
    
    def closeEvent(self, event):
        self.close()
        
        