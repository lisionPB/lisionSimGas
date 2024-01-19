from PyQt5.QtWidgets import QDialog, QLabel, QVBoxLayout, QHBoxLayout, QGroupBox, QDoubleSpinBox, QPushButton

from PyQt5.QtGui import (QIcon, QPixmap)
from PyQt5.QtCore import (Qt)


class ReglerConfigUI(QDialog):
    def __init__(self, sgr):
        super().__init__()
        self.sgr = sgr
  
        layout = QVBoxLayout()
        self.setLayout(layout)
  
        self.setWindowTitle("Reglerkonfiguration")

        # Konfig
        self.reglerConfigGroup = ReglerConfigGroup(sgr)
        layout.addWidget(self.reglerConfigGroup)

        # Save and Cancel
        saveGroup = QGroupBox()
        saveLayout = QHBoxLayout()
        saveGroup.setLayout(saveLayout)
        layout.addWidget(saveGroup)
        
        
        self.pbCancelConfig = QPushButton("Abbrechen")
        self.pbCancelConfig.clicked.connect(self.close)
        saveLayout.addWidget(self.pbCancelConfig)
        
        saveLayout.addStretch(1) 
        
        self.pbSaveConfig = QPushButton("Speichern")
        self.pbSaveConfig.clicked.connect(self.saveConfig)
        saveLayout.addWidget(self.pbSaveConfig)
        
    
    def saveConfig(self):
        config = self.reglerConfigGroup.getConfig()    
        # TODO: Plausi Check?
        
        for p in config:
            self.sgr._ports[p].set_Kalibrierung(config[p][2:6])
  
        self.close()
  
    
  
class ReglerConfigGroup(QGroupBox):
    def __init__(self, sgr):
        super().__init__("Reglerkonfiguration")
        self.sgr = sgr
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        self.rcrs = {}
        for r in sgr._ports:
            rcr = ReglerConfigRow(sgr._ports[r])
            self.rcrs[r] = rcr
            layout.addWidget(rcr)
            
    def getConfig(self):
        conf = {}
        for r in self.rcrs:
            conf[r] = [self.rcrs[r].sMin.value(), self.rcrs[r].sMax.value(), self.rcrs[r].sPX0.value(), self.rcrs[r].sPX1.value(), self.rcrs[r].sPX2.value(), self.rcrs[r].sPX3.value()]
            
        return conf
            
  

  
class ReglerConfigRow(QGroupBox):
    def __init__(self, r):
        
        super().__init__()
        
        self.r = r
        
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
        
        # PX0
        lPX0 = QLabel("P" + r.get_name()[1] + "0")
        layout.addWidget(lPX0)
        
        self.sPX0 = QDoubleSpinBox()
        self.sPX0.setMinimum(-10000.00)
        self.sPX0.setMaximum(10000.00)
        self.sPX0.setSingleStep(0.01)
        self.sPX0.setValue(self.r.get_kalibrierung()[0])
        layout.addWidget(self.sPX0)
        
        # PX1
        lPX1 = QLabel("P" + r.get_name()[1] + "1")
        layout.addWidget(lPX1)
        
        self.sPX1 = QDoubleSpinBox()
        self.sPX1.setMinimum(-10000.00)
        self.sPX1.setMaximum(10000.00)
        self.sPX1.setSingleStep(0.01)
        self.sPX1.setValue(self.r.get_kalibrierung()[1])
        layout.addWidget(self.sPX1)
        
        # PX2
        lPX2 = QLabel("P" + r.get_name()[1] + "2")
        layout.addWidget(lPX2)
        
        self.sPX2 = QDoubleSpinBox()
        self.sPX2.setMinimum(-10000.00)
        self.sPX2.setMaximum(10000.00)
        self.sPX2.setSingleStep(0.01)
        self.sPX2.setValue(self.r.get_kalibrierung()[2])
        layout.addWidget(self.sPX2)
        
        
        # PX3
        lPX3 = QLabel("P" + r.get_name()[1] + "3")
        layout.addWidget(lPX3)
        
        self.sPX3 = QDoubleSpinBox()
        self.sPX3.setMinimum(-10000.00)
        self.sPX3.setMaximum(10000.00)
        self.sPX3.setSingleStep(0.01)
        self.sPX3.setValue(self.r.get_kalibrierung()[3])
        layout.addWidget(self.sPX3)
        
        # Plausibility Check
        # TODO: Für Min / Max
        
        
        
        
        
        
        
        