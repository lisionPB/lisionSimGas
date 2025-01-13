import os

from PyQt5 import QtCore, QtGui, QtWidgets, QtPrintSupport
from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QDoubleSpinBox, QLabel, QWidget, QLineEdit
from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap

import pyqtgraph as pg
import pyqtgraph.exporters as pyexp

import random
import json
import time
from datetime import datetime

from reportlab.pdfgen import canvas
from reportlab.lib import utils
from reportlab.lib.units import cm
from reportlab.platypus import Frame, Image

import matplotlib.pyplot as plt

#from PIL import Image 

from datamanager import DataManager
from pruefung import Pruefung
import consoleWidget as cw

import parametrierung
from parametrierungUI import ParametrierungUI



class GasSensorWidget(QGroupBox):
    
    _sig_pdfSaved = pyqtSignal(str) # "" wenn fehler, sonst Filename
    
    def __init__(self, rs, ggs, mw):
        """
        Arguments:
            rs (ReglerSetup): zugrundliegendes reglerSetup 
        """
        
        super().__init__("Gas Sensorik")
        
        # self.sgr = rs
        self.ggs = ggs
        self.mw = mw
        
        self.mainLayout = QVBoxLayout()
        self.setLayout(self.mainLayout)
        
        self.init_UI()
        
        
        
        
    def init_UI(self):
        
        ################################
        # Connection
        ##########################
        
        self.connectionGroup = QGroupBox ("Verbindungssstatus")
        connectLayout = QHBoxLayout()
        self.connectionGroup.setLayout(connectLayout)
        self.mainLayout.addWidget(self.connectionGroup)
        
        # Connect Status
        self.bildActive = QPixmap("symbols/light_green.png")
        self.bildWarning = QPixmap("symbols/light_yellow.png")
        self.bildInactive = QPixmap("symbols/light_red.png")
          
        self.lActive = QLabel("")
        connectLayout.addWidget(self.lActive)
        
        connectLayout.addSpacing(1)
        
        
        #############################
        # Data
        #############################
        
        dataGroup = QGroupBox("Gas-Sensoren")
        dataLayout = QVBoxLayout()
        dataGroup.setLayout(dataLayout)
        self.mainLayout.addWidget(dataGroup)
        
        self.gasGroups = {}
        
        for i, s in enumerate(self.ggs._ggEA._sensors):
            self.gasGroups[s] = GasData_Widget(s)
            dataLayout.addWidget(self.gasGroups[s])
    
    
                
                
class GasData_Widget(QGroupBox):
    
    def __init__(self, name):
        super().__init__(name)
        layout = QHBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(5,5,5,5)
        
        self.lCurrentValue = QLabel("Messwert: ")
        self.lCurrentValue.setFixedWidth(100)
        layout.addWidget(self.lCurrentValue)
        self.leCurrentValue = QLineEdit("")
        self.leCurrentValue.setFixedWidth(60)
        self.leCurrentValue.setReadOnly(True)
        self.leCurrentValue.setAlignment(QtCore.Qt.AlignRight)
        layout.addWidget(self.leCurrentValue)
        self.lCurrentValueUnit = QLabel("[g/m³]")
        self.lCurrentValueUnit.setFixedWidth(60)
        layout.addWidget(self.lCurrentValueUnit)
        
        self.lCurrentValueMax = QLabel("max: ")
        self.lCurrentValueMax.setFixedWidth(100)
        layout.addWidget(self.lCurrentValueMax)
        self.leCurrentValueMax = QLineEdit("")
        self.leCurrentValueMax.setFixedWidth(60)
        self.leCurrentValueMax.setReadOnly(True)
        self.leCurrentValueMax.setAlignment(QtCore.Qt.AlignRight)
        layout.addWidget(self.leCurrentValueMax)
        self.lCurrentValueMaxUnit = QLabel("[g/m³]")
        self.lCurrentValueMaxUnit.setFixedWidth(60)
        layout.addWidget(self.lCurrentValueMaxUnit)
        
        self.pbResetMax = QPushButton("reset")
        layout.addWidget(self.pbResetMax)
    
    
    def update_GasData(self, value):
        pass
    