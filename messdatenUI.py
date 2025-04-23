
import ctypes

from PyQt5 import QtCore
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QMainWindow

class MessdatenUI(QMainWindow):
    
    sig_close = pyqtSignal()
    
    def __init__(self, parent, mdgw):
        super().__init__(parent)
        
        self._parent = parent
        self._mdgw = mdgw
        
        self.setCentralWidget(self._mdgw)    
                
        self.setWindowTitle("Messdaten UI")
        self.setWindowIcon(QIcon("symbols/lision.ico"))
        
        # Setzt Symbol in der Taskleiste
        myappid = u'lision.DaEf.simgas.v0_18.messdatenUI' # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        
        self.showMaximized()
                
        #self.setWindowFlags(
        #    Qt.WindowCloseButtonHint | Qt.WindowMaximizeButtonHint
        #)
        
    
   
    def closeEvent(self, event):       
        self.sig_close.emit()