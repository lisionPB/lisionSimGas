from PyQt5.QtWidgets import QDialog, QLabel, QVBoxLayout, QHBoxLayout, QGroupBox, QDoubleSpinBox, QPushButton

from PyQt5.QtGui import (QIcon, QPixmap)
from PyQt5.QtCore import (Qt)


class SensorConfigUI(QDialog):
    def __init__(self, sms):
        super().__init__()
  
        self.sms = sms
  
        layout = QVBoxLayout()
        self.setLayout(layout)
  
        self.setWindowTitle("Sensorkonfiguration")

        # Konfig
        self.sensorConfigGroup = SensorConfigGroup(sms)
        layout.addWidget(self.sensorConfigGroup)

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
        config = self.sensorConfigGroup.getConfig()    
        # TODO: Plausi Check?
        
        for s in config:
            self.sms._sgEA._sensors[s]["min"] = config[s][0]
            self.sms._sgEA._sensors[s]["max"] = config[s][1]
  
        self.close()
  
    
  
class SensorConfigGroup(QGroupBox):
    def __init__(self, sms):
        super().__init__("Sensorkonfiguration")

        layout = QVBoxLayout()
        self.setLayout(layout)
        
        self.scrs = {}
        for s in sms._sgEA._sensors:
            scr = SensorConfigRow(s, sms._sgEA._sensors[s])
            self.scrs[s] = scr
            layout.addWidget(scr)
            
            
    def getConfig(self):
        conf = {}
        for s in self.scrs:
            conf[s] = [self.scrs[s].sMin.value(), self.scrs[s].sMax.value()]
            
        return conf
            
  

  
class SensorConfigRow(QGroupBox):
    def __init__(self,name, s):
        
        super().__init__()
        
        self.s = s
        
        layout = QHBoxLayout()
        self.setLayout(layout)
        
        
        # Name
        lName = QLabel(name)
        layout.addWidget(lName)
        
        # Arbeitsbereich MIN
        lMin = QLabel("Wert 4mA")
        layout.addWidget(lMin)
        self.sMin = QDoubleSpinBox()
        self.sMin.setMinimum(0.00)
        self.sMin.setMaximum(10000.00)
        self.sMin.setSingleStep(0.01)
        self.sMin.setValue(self.s["min"])
        self.sMin.setEnabled(True)
        layout.addWidget(self.sMin)
        
        # Arbeitsbereich MAX
        lMax = QLabel("Wert 20mA")
        layout.addWidget(lMax)
        self.sMax = QDoubleSpinBox()
        self.sMax.setMinimum(0.00)
        self.sMax.setMaximum(10000.00)
        self.sMax.setSingleStep(0.01)
        self.sMax.setValue(self.s["max"])
        self.sMax.setEnabled(True)
        layout.addWidget(self.sMax)
        
        
        
        
        
        
        
        