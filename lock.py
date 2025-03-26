import os
import sys
import ctypes

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

FILENAME_LOCK = "benutzer\\simgas.lock"

def islocked():
    return os.path.exists(FILENAME_LOCK)


def lock():
    with open(FILENAME_LOCK, 'w') as f:
        f.write("")  

def unlock():
    if os.path.exists(FILENAME_LOCK):
        os.remove(FILENAME_LOCK)
    

def showMsgLocked(msg):
    
    app = QApplication(sys.argv)
    main = MessageWindow(msg)
    main.show()
    ec = app.exec_()

    
class MessageWindow(QMainWindow):
    
    sig_close = pyqtSignal()
    
    def __init__(self, msg):
        super().__init__()
        self.setWindowIcon(QIcon('symbols/lision.ico'))
        self.setWindowTitle("Anwendung läuft bereits!")
        
        # create central widget
        self.widget = QWidget()     
        self.setCentralWidget(self.widget)
        self.mainLayout = QVBoxLayout()
        self.widget.setLayout(self.mainLayout)
        
        # Text
        msgLabel = QLabel(msg)
        self.mainLayout.addWidget(msgLabel)
        
        # Button
        pbOK = QPushButton("OK")
        self.mainLayout.addWidget(pbOK)
        pbOK.clicked.connect(self.close)
        pbOK.setFixedWidth(150)
        
        
                
    