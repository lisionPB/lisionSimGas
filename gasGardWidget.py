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

import gasGardEA


class GasGardWidget(QGroupBox):
    
    _sig_pdfSaved = pyqtSignal(str) # "" wenn fehler, sonst Filename
    
    def __init__(self, ggs):
        
        super().__init__("GasGard XL - online")
        
        self.ggs = ggs
        
        self.mainLayout = QVBoxLayout()
        self.setLayout(self.mainLayout)
        
        self.init_UI()
        
        # Set Sensor Names when ready
        self.ggs._ggEA.sig_sensorNamesReceived.connect(self.set_SensorNames)
        # self.set_SensorNames()
        
        
    def init_UI(self):
                
        #############################
        # Data
        #############################
        
        self.gasGroups = {}
        
        for i, s in enumerate(self.ggs._ggEA._sensors):
            self.gasGroups[s] = GasData_Widget(self.ggs._ggEA._sensors[s]["label"])
            self.mainLayout.addWidget(self.gasGroups[s])
    
    
    def set_SensorNames(self):
        for s in self.gasGroups:
            self.gasGroups[s].set_GasSensorName(self.ggs._ggEA._sensors[s]["type"])
        
            
    def update_GasSensorStatus(self, device_status, sensors_status):
        for s in list(self.gasGroups.keys()):
            if(s in sensors_status):
                self.gasGroups[s].update_GasSensorStatus(sensors_status[s])
            else:
                self.gasGroups[s].update_GasSensorStatus(None)
           
            
    def update_GasSensorValues(self, sensors_values):
        
        for s in list(self.gasGroups.keys()):
            if(s in sensors_values):
                self.gasGroups[s].update_GasSensorValue(sensors_values[s])
            else:
                self.gasGroups[s].update_GasSensorValue(None)
                
    
    
                
                
class GasData_Widget(QGroupBox):
    
    def __init__(self, name):
        
        super().__init__(name)
        
        self.name = name
        self.nameSet = False
        
        self.bildAlarm1 = QPixmap("symbols/light_yellow.png")
        self.bildAlarm1_Off = QPixmap("symbols/light_yellow_off.png")
        self.bildAlarm2 = QPixmap("symbols/light_red.png")
        self.bildAlarm2_Off = QPixmap("symbols/light_red_off.png")
        
        self.maxValue = 0
        
        layout = QHBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(5,0,5,0)
        
        # Messwert
        self.lCurrentValue = QLabel("Messwert:")
        self.lCurrentValue.setFixedWidth(100)
        layout.addWidget(self.lCurrentValue)
        self.leCurrentValue = QLineEdit("")
        self.leCurrentValue.setFixedWidth(60)
        self.leCurrentValue.setReadOnly(True)
        self.leCurrentValue.setAlignment(QtCore.Qt.AlignRight)
        layout.addWidget(self.leCurrentValue)
        self.lCurrentValueUnit = QLabel("%")
        self.lCurrentValueUnit.setFixedWidth(60)
        layout.addWidget(self.lCurrentValueUnit)
        
        # Max Value
        self.lCurrentValueMax = QLabel("Max-Wert:")
        self.lCurrentValueMax.setFixedWidth(100)
        layout.addWidget(self.lCurrentValueMax)
        self.leCurrentValueMax = QLineEdit("")
        self.leCurrentValueMax.setFixedWidth(60)
        self.leCurrentValueMax.setReadOnly(True)
        self.leCurrentValueMax.setAlignment(QtCore.Qt.AlignRight)
        layout.addWidget(self.leCurrentValueMax)
        self.lCurrentValueMaxUnit = QLabel("%")
        self.lCurrentValueMaxUnit.setFixedWidth(60)
        layout.addWidget(self.lCurrentValueMaxUnit)
        
        # Reset Max Value
        self.pbResetMax = QPushButton("Reset")
        layout.addWidget(self.pbResetMax)
        self.pbResetMax.clicked.connect(self.reset_maxValue)
        
        # Alerts
        # 1 
        alert1Group = QGroupBox("A1")
        layout.addWidget(alert1Group)
        alert1Layout = QVBoxLayout()
        alert1Layout.setContentsMargins(8,0,0,3)
        alert1Group.setLayout(alert1Layout)
        self.lAlarm1 = QLabel("")
        self.lAlarm1.setPixmap(self.bildAlarm1_Off)
        alert1Layout.addWidget(self.lAlarm1)
        # 2 
        alert2Group = QGroupBox("A2")
        layout.addWidget(alert2Group)
        alert2Layout = QVBoxLayout()
        alert2Layout.setContentsMargins(8,0,0,3)
        alert2Group.setLayout(alert2Layout)
        self.lAlarm2 = QLabel("")
        self.lAlarm2.setPixmap(self.bildAlarm2_Off)
        alert2Layout.addWidget(self.lAlarm2)
    
    
    def set_GasSensorName(self, name):
        self.setTitle(self.name + ": " + name)
    
    
    def update_GasSensorStatus(self, status):
        # Alarme
        if(status != None):
            # 1
            if(status[gasGardEA.CH_ALARM_1]):
                self.lAlarm1.setPixmap(self.bildAlarm1)
            else:
                self.lAlarm1.setPixmap(self.bildAlarm1_Off)
            # 2 
            if(status[gasGardEA.CH_ALARM_2]):
                self.lAlarm2.setPixmap(self.bildAlarm2)
            else:
                self.lAlarm2.setPixmap(self.bildAlarm2_Off)
        
        else:
            # TODO: Anzeige, dass keine Status Daten von Sensor
            pass    
        
        
    def update_GasSensorValue(self, value):
        self.leCurrentValue.setText(str(value))
        if(value != None):
            if(value >= self.maxValue):
                self.maxValue = value
                self.leCurrentValueMax.setText(str(self.maxValue))
        else:
            self.leCurrentValueMax.setText(str("---"))
            
    def reset_maxValue(self):
        self.maxValue = 0