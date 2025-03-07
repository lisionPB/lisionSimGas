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
        
        # Gas Flaschen Sensorik
        config_gfs = self.sensorConfigGroup.getConfig_GasFlaschenSensorik()    
        for s in config_gfs:
            self.sms._sgEA._sensors[s]["min"] = config_gfs[s][0]
            self.sms._sgEA._sensors[s]["max"] = config_gfs[s][1]
  
        # MGS Boxen Sensorik
        config_mgs = self.sensorConfigGroup.getConfig_MGSBoxenSensorik()    
        for s in config_mgs:
            self.sms._sgEA._sensorsMGS[s]["min"] = config_mgs[s][0]
            self.sms._sgEA._sensorsMGS[s]["max"] = config_mgs[s][1]
            
        self.close()
  
  
    
  
class SensorConfigGroup(QGroupBox):
    def __init__(self, sms):
        super().__init__("Sensorkonfiguration")

        layout = QVBoxLayout()
        self.setLayout(layout)
        
        
        # Gas Flaschen
        self.scrs_gfs = {}
        
        flaschenGroup = QGroupBox("Gas-Zufuhr Sensorik")
        flaschenLayout = QVBoxLayout()
        flaschenGroup.setLayout(flaschenLayout)
        layout.addWidget(flaschenGroup)
        
        for s in sms._sgEA._sensors:
            scr = SensorConfigRow(s, sms._sgEA._sensors[s])
            self.scrs_gfs[s] = scr
            flaschenLayout.addWidget(scr)
            
        # MGS Boxen
        self.scrs_mgs = {}
        
        mgsGroup = QGroupBox("MGS Boxen Sensorik")
        mgsLayout = QVBoxLayout()
        mgsGroup.setLayout(mgsLayout)
        layout.addWidget(mgsGroup)
        
        for s in sms._sgEA._sensorsMGS:
            scr = SensorConfigRow(s, sms._sgEA._sensorsMGS[s])
            self.scrs_mgs[s] = scr
            mgsLayout.addWidget(scr)
            
            
    def getConfig_GasFlaschenSensorik(self):
        conf = {}
        for s in self.scrs_gfs:
            conf[s] = [self.scrs_gfs[s].sMin.value(), self.scrs_gfs[s].sMax.value()]
            
        return conf
            
    def getConfig_MGSBoxenSensorik(self):
        conf = {}
        for s in self.scrs_mgs:
            conf[s] = [self.scrs_mgs[s].sMin.value(), self.scrs_mgs[s].sMax.value()]
            
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
        self.sMin.setMaximum(1000000.00)
        self.sMin.setSingleStep(0.01)
        self.sMin.setValue(self.s["min"])
        self.sMin.setEnabled(True)
        layout.addWidget(self.sMin)
        
        # Arbeitsbereich MAX
        lMax = QLabel("Wert 20mA")
        layout.addWidget(lMax)
        self.sMax = QDoubleSpinBox()
        self.sMax.setMinimum(0.00)
        self.sMax.setMaximum(1000000.00)
        self.sMax.setSingleStep(0.01)
        self.sMax.setValue(self.s["max"])
        self.sMax.setEnabled(True)
        layout.addWidget(self.sMax)
        
        
        
        
        
        
        
        