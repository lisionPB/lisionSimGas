from PyQt5 import QtCore
from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit

class MGSWidget(QGroupBox):
    
    def __init__(self, sms):
        super().__init__("MGS Boxen")
        
        self.sms = sms
        
        self.mgsGroups = {}
        
        self.mainLayout = QHBoxLayout()
        self.setLayout(self.mainLayout)
        
        self.groupBox1 = QGroupBox("MGS Box 1 - online")
        layoutBox1 = QVBoxLayout()
        self.groupBox1.setLayout(layoutBox1)
        self.mainLayout.addWidget(self.groupBox1)
        
        self.groupBox2 = QGroupBox("MGS Box 2 - online")
        layoutBox2 = QVBoxLayout()
        self.groupBox2.setLayout(layoutBox2)
        self.mainLayout.addWidget(self.groupBox2)
                
        for i, s in enumerate(self.sms._sgEA._sensorsMGS):
            self.mgsGroups[s] = MGS_Box_Widget(self.sms._sgEA._sensorsMGS[s]["label"])
            if(i <= 1):
                layoutBox1.addWidget(self.mgsGroups[s])
            else:
                layoutBox2.addWidget(self.mgsGroups[s])
                
                
    def update_MGSWidget(self):
        for s in self.mgsGroups:
            self.mgsGroups[s].update_MGSData(self.sms.dataMGS[s])
            
            
    def hide_MGSBox(self, box):
        if(box == 1):
            self.groupBox1.setEnabled(False)
            self.groupBox1.setTitle("MGS Box 1 - offline")
            
        if(box == 2):
            self.groupBox2.setEnabled(False)
            self.groupBox2.setTitle("MGS Box 2 - offline")


    def show_MGSBox(self, box):
        if(box == 1):
            self.groupBox1.setEnabled(True)
            self.groupBox1.setTitle("MGS Box 1 - online")
            
        if(box == 2):
            self.groupBox2.setEnabled(True)
            self.groupBox2.setTitle("MGS Box 2 - online")       
            
            
class MGS_Box_Widget(QGroupBox):
    def __init__(self, name):
        super().__init__(name)
        
        dataLeftLayout = QHBoxLayout()
        self.setLayout(dataLeftLayout)
        dataLeftLayout.setContentsMargins(5,5,5,5)

        # PPM
        valGroup = QGroupBox()
        valLayout = QHBoxLayout()
        valLayout.setContentsMargins(0,0,0,0)
        valGroup.setLayout(valLayout)
        dataLeftLayout.addWidget(valGroup)
        self.lVal = QLabel("Gas-Konz.")
        self.lVal.setFixedWidth(100)
        valLayout.addWidget(self.lVal)
        self.tVal = QLineEdit("")
        self.tVal.setFixedWidth(60)
        self.tVal.setReadOnly(True)
        self.tVal.setAlignment(QtCore.Qt.AlignCenter)
        valLayout.addWidget(self.tVal)
        self.lVal = QLabel("ppm")
        self.lVal.setFixedWidth(60)
        valLayout.addWidget(self.lVal)
        
        valLayout.addStretch(1)
        
        
    def update_MGSData(self, val):
 
        if(type(val) == float):
            val = "{:6.0f}".format(val)
            self.tVal.setText(val)