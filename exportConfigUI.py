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

        # Channel Config
        
        self.channelConfigGroup = ConfigGroup()
        layout.addWidget(self.channelConfigGroup)

        # Graph Config
        self.diagrammConfigGroup = DiagrammConfigGroup()
        layout.addWidget(self.diagrammConfigGroup)


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
        self.diagrammConfigGroup.saveConfig()
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

    
class DiagrammConfigGroup(QGroupBox):

    def __init__(self):
        super().__init__("Diagramm")

        self.mainLayout = QVBoxLayout()
        self.setLayout(self.mainLayout)


        # Y MAX Regler
        group_yMax_regler = QGroupBox()
        layout_yMax_regler = QHBoxLayout()
        layout_yMax_regler.setContentsMargins(0,0,0,0)
        group_yMax_regler.setLayout(layout_yMax_regler)    
        self.mainLayout.addWidget(group_yMax_regler)

        yMax_regler_label = QLabel("Max. Gaszufuhr: ")
        yMax_regler_label.setFixedWidth(200)
        layout_yMax_regler.addWidget(yMax_regler_label)

        self.yMax_regler_spinner = QDoubleSpinBox()
        self.yMax_regler_spinner.setDecimals(0)
        self.yMax_regler_spinner.setMaximum(10000)
        self.yMax_regler_spinner.setFixedWidth(100)
        self.yMax_regler_spinner.setValue(exportConfig.Y_MAX_REGLER)
        layout_yMax_regler.addWidget(self.yMax_regler_spinner)

        yMax_regler_unit = QLabel("g/min")
        layout_yMax_regler.addWidget(yMax_regler_unit)

        layout_yMax_regler.addStretch()

        # Y MAX Gas
        group_yMax = QGroupBox()
        layout_yMax = QHBoxLayout()
        layout_yMax.setContentsMargins(0,0,0,0)
        group_yMax.setLayout(layout_yMax)    
        self.mainLayout.addWidget(group_yMax)

        yMax_label = QLabel("Max. Gaskonzentration: ")
        yMax_label.setFixedWidth(200)
        layout_yMax.addWidget(yMax_label)

        self.yMax_spinner = QDoubleSpinBox()
        self.yMax_spinner.setDecimals(0)
        self.yMax_spinner.setFixedWidth(100)
        self.yMax_spinner.setValue(exportConfig.Y_MAX)
        layout_yMax.addWidget(self.yMax_spinner)

        yMax_proz = QLabel("%")
        layout_yMax.addWidget(yMax_proz)

        layout_yMax.addStretch()

        # Y STEP
        group_yStep = QGroupBox()
        layout_yStep = QHBoxLayout()
        layout_yStep.setContentsMargins(0,0,0,0)
        group_yStep.setLayout(layout_yStep)    
        self.mainLayout.addWidget(group_yStep)

        yStep_label = QLabel("y-Achsen Schrittweite")
        yStep_label.setFixedWidth(200)
        layout_yStep.addWidget(yStep_label)

        self.yStep_spinner = QDoubleSpinBox()
        self.yStep_spinner.setDecimals(0)
        self.yStep_spinner.setMinimum(1)
        self.yStep_spinner.setMaximum(1000)
        self.yStep_spinner.setFixedWidth(100)
        self.yStep_spinner.setValue(exportConfig.Y_STEP)
        layout_yStep.addWidget(self.yStep_spinner)

        yStep_proz = QLabel("%")
        layout_yStep.addWidget(yStep_proz)

        layout_yStep.addStretch()

        # N COLS
        group_nCols = QGroupBox()
        layout_nCols = QHBoxLayout()
        layout_nCols.setContentsMargins(0,0,0,0)
        group_nCols.setLayout(layout_nCols)    
        self.mainLayout.addWidget(group_nCols)

        nCols_label = QLabel("Anz. Spalten in Legende")
        nCols_label.setFixedWidth(200)
        layout_nCols.addWidget(nCols_label)

        self.nCols_spinner = QDoubleSpinBox()
        self.nCols_spinner.setDecimals(0)
        self.nCols_spinner.setMinimum(1)
        self.nCols_spinner.setMaximum(10)
        self.nCols_spinner.setFixedWidth(100)
        self.nCols_spinner.setValue(exportConfig.N_COLS)
        layout_nCols.addWidget(self.nCols_spinner)
        
        layout_nCols.addStretch()


    def saveConfig(self):
        exportConfig.Y_MAX_REGLER = int(self.yMax_regler_spinner.value())
        exportConfig.Y_MAX = int(self.yMax_spinner.value())
        exportConfig.Y_STEP = int(self.yStep_spinner.value())
        exportConfig.N_COLS = int(self.nCols_spinner.value())