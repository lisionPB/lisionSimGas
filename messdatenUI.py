
import ctypes

from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QMainWindow

class MessdatenUI(QMainWindow):
    
    def __init__(self, parent, mdgw):
        super().__init__(parent)
        
        self._parent = parent
        self._mdgw = mdgw
        
        self.setCentralWidget(self._mdgw)    
                
        self.setWindowTitle("Messdaten UI")
        self.setWindowIcon(QIcon("symbols/lision.ico"))
        
        # Setzt Symbol in der Taskleiste
        myappid = u'lision.DaEf.simgas.v0_4.messdatenUI' # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        
        self.showMaximized()
        
    
   
    def closeEvent(self, event):        
        self._parent.closeMessdatenUI()