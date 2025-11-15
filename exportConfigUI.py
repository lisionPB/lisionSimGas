from PyQt5.QtWidgets import QGroupBox, QDialog, QLineEdit, QVBoxLayout, QHBoxLayout, QPushButton, QDoubleSpinBox, QLabel, QCheckBox
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon

import exportConfig

class ExportConfigUI(QDialog):
    
    sig_exportConfig_changed = pyqtSignal()

    def __init__(self):
        
        super().__init__()
  
        layout = QVBoxLayout()
        self.setLayout(layout)
  
        self.setWindowTitle("Diagrammexport Konfiguration")
        self.setWindowIcon(QIcon("symbols/lision.ico"))
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        # Konfig
        self.channelConfigGroup = ConfigGroup()
        layout.addWidget(self.channelConfigGroup)

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
        
        self.channelConfigGroup.saveConfig() 
        self.sig_exportConfig_changed.emit()         
        self.close()
  
  
    
  
class ConfigGroup(QGroupBox):
    def __init__(self):
        super().__init__("Kanäle")

        self.mainLayout = QVBoxLayout()
        self.setLayout(self.mainLayout)
        
        self.configRows = self.initConfigRows()


    def initConfigRows(self):

        configRows = {}
        for c in exportConfig.channelExportConfigs:
            configRows[c] = ConfigRow(c)
            self.mainLayout.addWidget(configRows[c])

        return configRows


    def saveConfig(self):
        for cr in self.configRows:
            self.configRows[cr].saveConfigRow()

  


class ConfigRow(QGroupBox):
    def __init__(self, channel):
        super().__init__()

        self.channel = channel

        layout = QHBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        self.setLayout(layout)
        
        # Name
        self.lName = QLabel(channel)        
        self.lName.setFixedWidth(200)
        layout.addWidget(self.lName)
        
        # User Label
        self.lLabel = QLineEdit(exportConfig.channelExportConfigs[channel]["user_label"])
        self.lLabel.setFixedWidth(300)
        layout.addWidget(self.lLabel)

        # Active
        self.cbActive = QCheckBox()
        self.cbActive.setChecked(exportConfig.channelExportConfigs[channel]["active"])
        layout.addWidget(self.cbActive)

    def saveConfigRow(self):
        exportConfig.channelExportConfigs[self.channel]["user_label"] = self.lLabel.text()
        exportConfig.channelExportConfigs[self.channel]["active"] = self.cbActive.isChecked()