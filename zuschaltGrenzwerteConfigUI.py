from PyQt5.QtWidgets import QWidget, QDialog, QLabel, QVBoxLayout, QHBoxLayout, QGroupBox, QDoubleSpinBox, QPushButton

from PyQt5.QtGui import (QIcon, QPixmap)
from PyQt5.QtCore import (Qt)


class ZuschaltGrenzwerteConfigUI(QDialog):
    def __init__(self, sms):
        super().__init__()
        self.sms = sms
  
        layout = QVBoxLayout()
        self.setLayout(layout)
  
        self.setWindowTitle("Konfiguration der Zuschalt-Grenzwerte für Gasflaschen")


        groupConfig = QGroupBox("Grenzwerte der Gasflaschen-Zuschaltung")
        self.layoutConfig = QVBoxLayout()
        groupConfig.setLayout(self.layoutConfig)
        layout.addWidget(groupConfig)

        # min Druck
        
        widgetMin = QWidget()
        self.layoutMin = QHBoxLayout()
        widgetMin.setLayout(self.layoutMin)
        self.layoutConfig.addWidget(widgetMin)
        
        lMin = QLabel("min. Druck: ")
        self.layoutMin.addWidget(lMin)
        lMin.setFixedWidth(100)
        
        self.sMin = QDoubleSpinBox()
        self.layoutMin.addWidget(self.sMin)
        self.sMin.setMinimum(0.0)
        self.sMin.setMaximum(100.0)
        self.sMin.setSingleStep(0.1)
        self.sMin.setValue(self.sms.zuschaltGrenzwerte["DRUCK_MIN"])
        self.sMin.setFixedWidth(50)
        
        lUnitMin = QLabel("bar")
        self.layoutMin.addWidget(lUnitMin)
        lUnitMin.setFixedWidth(50)
        
        
        # max Druck Diff

        widgetMax = QWidget()
        self.layoutMax = QHBoxLayout()
        widgetMax.setLayout(self.layoutMax)
        self.layoutConfig.addWidget(widgetMax)
        
        lMax = QLabel("max. Druckdif.: ")
        self.layoutMax.addWidget(lMax)
        lMax.setFixedWidth(100)
        
        self.sMax = QDoubleSpinBox()
        self.layoutMax.addWidget(self.sMax)
        self.sMax.setMinimum(0.0)
        self.sMax.setMaximum(100.0)
        self.sMax.setSingleStep(0.1)
        self.sMax.setValue(self.sms.zuschaltGrenzwerte["DIFF_MAX"])
        self.sMax.setFixedWidth(50)
        
        lUnitMax = QLabel("bar")
        self.layoutMax.addWidget(lUnitMax)
        lUnitMax.setFixedWidth(50)


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
        
        self.sms.zuschaltGrenzwerte["DRUCK_MIN"] = self.sMin.value()
        self.sms.zuschaltGrenzwerte["DIFF_MAX"]  = self.sMax.value()
  
        self.close()
  
    
        