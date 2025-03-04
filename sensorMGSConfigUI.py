from PyQt5.QtWidgets import QDialog, QLabel, QVBoxLayout, QHBoxLayout, QGroupBox, QDoubleSpinBox, QPushButton

from PyQt5.QtGui import (QIcon, QPixmap)
from PyQt5.QtCore import (Qt)


class SensorMGSConfigUI(QDialog):
    def __init__(self, sms):
        super().__init__()
  
        self.sms = sms
  
        layout = QVBoxLayout()
        self.setLayout(layout)
  
        self.setWindowTitle("Sensorkonfiguration für MGS Boxen")

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
        
        for s in config:
            self.sms._sgEA._sensorsMGS[s]["min"] = config[s][0]
            self.sms._sgEA._sensorsMGS[s]["max"] = config[s][1]
  
        self.close()
  
    
  
class SensorConfigGroup(QGroupBox):
    def __init__(self, sms):
        super().__init__("Sensorkonfiguration MGS Boxen")

        layout = QHBoxLayout()
        self.setLayout(layout)
        
        groupBox1 = QGroupBox("MGS Box 1")
        layoutBox1 = QVBoxLayout()
        groupBox1.setLayout(layoutBox1)
        layout.addWidget(groupBox1)
        
        groupBox2 = QGroupBox("MGS Box 2")
        layoutBox2 = QVBoxLayout()
        groupBox2.setLayout(layoutBox2)
        layout.addWidget(groupBox2)
        
        self.scrs = {}
        for i, s in enumerate(sms._sgEA._sensorsMGS):
            scr = SensorConfigRow(s, sms._sgEA._sensorsMGS[s])
            self.scrs[s] = scr
            if(i <= 1):
                layoutBox1.addWidget(scr)
            else:
                layoutBox2.addWidget(scr)
                
            
            
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
        self.sMin.setMinimum(0)
        self.sMin.setMaximum(1000000)
        self.sMin.setSingleStep(1)
        self.sMin.setDecimals(0)
        self.sMin.setValue(self.s["min"])
        self.sMin.setEnabled(True)
        layout.addWidget(self.sMin)
        
        # Arbeitsbereich MAX
        lMax = QLabel("Wert 20mA")
        layout.addWidget(lMax)
        self.sMax = QDoubleSpinBox()
        self.sMax.setMinimum(0)
        self.sMax.setMaximum(1000000)
        self.sMax.setSingleStep(1)
        self.sMax.setDecimals(0)
        self.sMax.setValue(self.s["max"])
        self.sMax.setEnabled(True)
        layout.addWidget(self.sMax)
        
        
        
        
        
        
        
        