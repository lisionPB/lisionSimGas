import parametrierung

from PyQt5 import Qt, QtCore, QtGui, QtWidgets, QtPrintSupport
from PyQt5.QtWidgets import QGroupBox, QLineEdit, QVBoxLayout, QHBoxLayout, QPushButton, QDoubleSpinBox, QLabel
from PyQt5.QtCore import QTimer, pyqtSignal


class ParametrierungUI(QGroupBox):
    
    ID_SENDSLOT = 20
    
    def __init__(self, sgr):
        
        super().__init__()
        
        self.sgr = sgr
        
        self.sgr._worker.sig_paused_for.connect(self.use_SendSlot)
        
        self.mainLayout = QVBoxLayout()
        self.setLayout(self.mainLayout)
        
        self.rows = {}
        for p in self.sgr._ports:
            self.rows[p] = ReglerParametrierungReihe(self.sgr._ports[p].get_name())
            self.mainLayout.addWidget(self.rows[p])
        
        self.pbSendParams = QPushButton("Parameter Senden")
        self.pbSendParams.clicked.connect(self.send_Params)
        self.mainLayout.addWidget(self.pbSendParams)
        self.pbSendParams.setVisible(False)
    
    
    
                
    def update_Params(self, parameter):
        for n in parameter:
            self.rows[n].updateKp(parameter[n]["Kp"])
            self.rows[n].updateTi(parameter[n]["Ti"])
            
        
            
    def request_SendSlot(self):
        """
        Fordere eine Pause der MessLoop, damit neue Parameter gesendet werden können.
        Sende eigene ID_SENDSLOT mit, um zu idetifizieren, wenn Pause für eigenen Slot geschaffen wird
        """
        
        self.sgr.sig_pauseMessLoop.emit(self.ID_SENDSLOT)
        
        
    def use_SendSlot(self, forID):
        """ 
        Wenn MessLoop für Parametrierung pausiert, sende Params
        """
        if(forID == self.ID_SENDSLOT):
            if(self.sgr._worker._paused):
                self.send_Params()
        
        
            
    def send_Params(self, versuch=1):
        """
        Sendet die aktuell berechneten Parameter an die Regelstellglieder.
        Inkl. Rücklesen
        
        returns: True, wenn Übertragung erfolgreich. Sonst False
        """

        for p in self.sgr._ports:
            
            # Enable Param Tuning
            (self.sgr._ports[p].writeParameter(7, 64))
            (self.sgr._ports[p].writeParameter(12, 6))
            (self.sgr._ports[p].writeParameter(79, 5))
            # Send Params
            (self.sgr._ports[p].writeParameter(167, float(self.rows[p].tKp.text())))
            (self.sgr._ports[p].writeParameter(168, float(self.rows[p].tTi.text())))
            # Back To Normal Operation
            (self.sgr._ports[p].writeParameter(12, 0))
            (self.sgr._ports[p].writeParameter(7, 82))
        
        # Rücklesen
        self.read_Params()
            
        # Check Übereinstimmung
        ok = True
        for p in self.sgr._ports:
            
            # Kp
            sollKp = round(float(self.rows[p].tKp.text()), 3)
            istKp = round(float(self.rows[p].lKpConf.text()[1:-1]), 3)
            abgleichKp = sollKp == istKp
            #print (f'sollKp: {sollKp} == istKp : {istKp} : {abgleichKp}')
            if(not abgleichKp):
                ok = False
            
            # Ti
            sollTi = round(float(self.rows[p].tTi.text()), 3)
            istTi = round(float(self.rows[p].lTiConf.text()[1:-1]), 3)
            abgleichTi = sollTi == istTi
            #print (f'sollTi: {sollTi} == istTi : {istTi} : {abgleichTi}')
            if(not abgleichTi):
                ok = False
        
        self.sgr.sig_continueMessLoop.emit()
        
        # max. 3 Versuche
        if(not ok and versuch < 3):
            self.send_Params(versuch=versuch+1)
        
        return ok
    
    
    
    def read_Params(self):
        """
        Liest die aktuellen PID Parameter aus den Regelstellgliedern aus und schreibt sie in die Textfelder
        """
        for p in self.sgr._ports:
            kp = self.sgr._ports[p].readParameter(167)
            ti = self.sgr._ports[p].readParameter(168)

            self.rows[p].updateKpConf(kp)
            self.rows[p].updateTiConf(ti)
            
            
    def update_Params_Conf(self, confirmedParameters):
        for n in confirmedParameters:
            self.rows[n].updateKpConf(parameter[n]["Kp"])
            self.rows[n].updateTiConf(parameter[n]["Ti"])
            
            
        
class ReglerParametrierungReihe(QGroupBox):
    
    def __init__(self, name):
        super().__init__()
        
        self.mainLayout = QHBoxLayout()
        self.setLayout(self.mainLayout)
        
        # Reglername
        self.name = QLabel(name)
        self.mainLayout.addWidget(self.name)
        
        # Kp 
        self.lKp = QLabel("Kp:")
        self.mainLayout.addWidget(self.lKp)
        self.lKp.setFixedWidth(30)
        self.tKp = QLineEdit()
        self.mainLayout.addWidget(self.tKp)
        self.tKp.setFixedWidth(70)
        self.tKp.setReadOnly(True)
        self.tKp.setAlignment(QtCore.Qt.AlignCenter)
        
        self.lKpConf = QLabel("")
        self.mainLayout.addWidget(self.lKpConf)
        self.lKpConf.setFixedWidth(80)
        
        
        # Ti
        self.lTi = QLabel("Ti:")
        self.mainLayout.addWidget(self.lTi)
        self.lTi.setFixedWidth(30)
        self.tTi = QLineEdit()
        self.mainLayout.addWidget(self.tTi)
        self.tTi.setFixedWidth(70)
        self.tTi.setReadOnly(True)
        self.tTi.setAlignment(QtCore.Qt.AlignCenter)
        
        self.lTiConf = QLabel("")
        self.mainLayout.addWidget(self.lTiConf)
        self.lTiConf.setFixedWidth(80)
    
    
    def updateKp(self, kp):
        self.tKp.setText('{0:.3f}'.format(kp))
        
    def updateTi(self, ti):
        self.tTi.setText('{0:.3f}'.format(ti))
        
    def updateKpConf(self, kpConf):
        self.lKpConf.setText("(" + '{0:.3f}'.format(kpConf) + ")")
    
    def updateTiConf(self, tiConf):
        self.lTiConf.setText("(" + '{0:.3f}'.format(tiConf) + ")")