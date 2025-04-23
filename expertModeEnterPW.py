# -*- coding: utf-8 -*-
"""
Created on Mon Jan 18 15:45:31 2023

@author: Paul Benz

v1.0
"""

from PyQt5.QtWidgets import QDialog, QLabel, QVBoxLayout, QLineEdit, QPushButton

from PyQt5.QtGui import (QIcon, QPixmap)
from PyQt5.QtCore import Qt, pyqtSignal

class DialogExpertModeEnterPW(QDialog):

    PW = "0000"
    
    sig_pw = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon("symbols/lision.ico"))
        self.setWindowTitle("Expertenmodus - Passwortabfrage")
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        
        self.setFixedWidth(300)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        enterLabel = QLabel("Passwort:")
        layout.addWidget(enterLabel)
  
        self.enterLE = QLineEdit("")
        self.enterLE.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.enterLE)
  
        okPB = QPushButton("OK")
        layout.addWidget(okPB)
        okPB.clicked.connect(self.emitPW)
        okPB.clicked.connect(self.close)
  
  
  
    def closeEvent(event):
        self.sig_pw.emit(False)
        
  
    def emitPW(self):
        self.sig_pw.emit(self.enterLE.text() == self.PW)
      
        