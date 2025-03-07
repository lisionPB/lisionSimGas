# -*- coding: utf-8 -*-
"""
Main Klasse der SimGas Steuerungssoftware

@author: paulb
"""
import sys
import ctypes
import pandas
import math
import pyqtgraph as pg

from PyQt5 import QtCore
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton, QLabel, QAction, QDoubleSpinBox, QLineEdit, QProgressBar, QSizePolicy, QCheckBox
from PyQt5.QtCore import Qt, QTimer, pyqtSignal

from lisionStyle import LisionStyle

from SimGasEA import SimGasEA
from gasGardEA import GasGardEA

import hwSetup as hs
import reglerSetup as rs
import messdatenGraphWidget as mgw
import messdatenTableWidget as mtw
import mgsWidget as mgsw
import gasGardWidget as gsw
import pruefWidget as pw
import consoleWidget as cw
import helpDialog as hd
import reglerConfigUI as rc
import sensorConfigUI as sc
import reglerConfigNullUI as rcn
import secSetup as ss
import reglerReadOutputLog as rrol
import gasGardSetup as gs


class ReglerUI(QMainWindow):
    
    TITEL = "SimGas Regler GUI - CORI"
    VERSION = "0.16"
    YEAR = "2025"
    
    _sig_close = pyqtSignal()
    
    UI_UPDATE_INTERVAL = 1000 #[ms]
    
    
    #################################################
    # Aktivierung von Funktionalitäten der Anwendung
    
    # Manuelle Messung Controls
    ENABLE_MANUAL_CONTROLS = True
    
    # Menü zum Nullabgleich verfügbar machen
    ENABLE_FUNCTION_NULLABGLEICH = True
    
    # Sicherheitsmagnetschalter
    ENABLE_SEC_MAGNET_SWITCH = True
    
    # GasGard Verbindung
    ENABLE_GASGARD_SENSORS = True
    
    # Entwickleransicht
    SHOW_EXTENDED_FUNCTIONS = False
    
    ###################################
    
    def __init__(self, sgr, sms, ggs):
        super().__init__()
    
        # lade HW-Setup
    
        self.sgr = sgr
        self.sms = sms
        self.ggs = ggs
            
        self.rmw = ReglerMainWidget(self)     
        self.setCentralWidget(self.rmw)  
        
        # Hide Extended Functions
        self.rmw.set_extendedFunctionVisibility(self.SHOW_EXTENDED_FUNCTIONS) 
                
        self.setWindowTitle(self.TITEL)
        self.setWindowIcon(QIcon("symbols/lision.ico"))

        # Setzt Symbol in der Taskleiste
        myappid = u'lision.DaEf.simgas.' + self.VERSION
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        
        
        ########
        # MENÜ	

        menuBar = self.menuBar()

        # Hilfe öffnen
        helpMenu = menuBar.addMenu('&Hilfe')
        helpAct = QAction('&Hilfe öffnen', self)
        helpAct.setStatusTip('Hilfe öffnen')
        helpAct.triggered.connect(self.open_help)
        helpMenu.addAction(helpAct)
        
        # Konfiguration öffnen
        configMenu = menuBar.addMenu('&Einstellungen')
        
        self.configAct = QAction('&Reglerkonfiguration', self)
        self.configAct.setStatusTip('Reglerkonfiguration')
        self.configAct.triggered.connect(self.open_config)
        configMenu.addAction(self.configAct)
        
        self.configSensorAct = QAction('&Sensorkonfiguration', self)
        self.configSensorAct.setStatusTip('Sensorkonfiguration')
        self.configSensorAct.triggered.connect(self.open_config_sensors)
        configMenu.addAction(self.configSensorAct)
        
        self.configNullAct = QAction('&Nullpunktabgleich', self)
        self.configNullAct.setStatusTip('Nullpunktabgleich')
        self.configNullAct.triggered.connect(self.open_configNull)
        if(self.ENABLE_FUNCTION_NULLABGLEICH):
            configMenu.addAction(self.configNullAct)
        
        self.configExpertModeAct = QAction('&Expertenmodus', configMenu, checkable=True)    
        configMenu.addAction(self.configExpertModeAct)
        self.configExpertModeAct.triggered.connect(self.switch_expertMode)
        
        
        
        #########################
        
        # Beim Beenden
        # Schließe HW-Setup
        self._sig_close.connect(self.sgr._close_hwSetup)
        
        # Verbinde Datenankunft mit Darstellung
        self.sgr.get_datamanager().sig_newDataReceived.connect(self.rmw.display_data)
         
         
        
         
        ###      
        # Sicherheitsmagnetschalter  
        # Verbinde Sec Setup
        if(self.ENABLE_SEC_MAGNET_SWITCH):
            # Message bei Verbindungsversuch
            self.sms.sig_SEC_ConnectFinished.connect(self.print_ConnectTryMessage_SEC)
            # Starten der SEC-Messschleife, sobald Verbindung hergestellt
            self.sms.sig_SEC_ConnectFinished.connect(self.sms._start_MessSchleife)            
            # Ankommende MGSBoxen Daten in DataManager einspeisen
            self.sgr.get_datamanager().addChannels(list(self.sms._sgEA._sensorsMGS.keys()))
            # channel labels
            secLabels = {}
            for s in self.sms._sgEA._sensorsMGS:
                secLabels[s] = self.sms._sgEA._sensorsMGS[s]["data_label"]
            self.sgr.get_datamanager().update_channelLabels(secLabels)
            self.sms._sig_NewSecData.connect(self.sgr.get_datamanager().append_RawData) 
            
            # Schließe Sicherheitsmagnetschalter bei Schließen der Anwendung
            self._sig_close.connect(self.sms._close_secSetup)

            # Verbindung herstellen
            self.sms._connect_sec()
            
            
        ###
        # GasGard  
        # Verbinde GasGard Setup
        if(self.ENABLE_GASGARD_SENSORS):
            # Message bei Verbindungsversuch
            self.ggs.sig_GG_ConnectFinished.connect(self.print_ConnectTryMessage_GasGard)
            # Starten der SEC-Messschleife, sobald Verbindung hergestellt
            self.ggs.sig_GG_ConnectFinished.connect(self.ggs._start_MessSchleife)            
            # Ankommende GasGard Daten in DataManager einspeisen
            self.sgr.get_datamanager().addChannels(list(self.ggs._ggEA._sensors.keys()))
            # channel labels
            ggLabels = {}
            for s in self.ggs._ggEA._sensors:
                ggLabels[s] = self.ggs._ggEA._sensors[s]["data_label"]
            self.sgr.get_datamanager().update_channelLabels(ggLabels)
            self.ggs.sig_NewGGData.connect(self.sgr.get_datamanager().append_RawData) 

            # Trenne Verbindung bei Schließen der Anwendung
            self._sig_close.connect(self.ggs._close_ggSetup)

            # Verbindung herstellen
            self.ggs._connect_gg()
           
           
           
        ###
        # GasSensorik Graph: GasGard + mgs Boxen
               
        # Channel Names des Graphen setzen
        chNameList = []
        # GasGard
        chNameList.extend(list(self.ggs._ggEA._sensors.keys()))
        # MGS Boxen
        chNameList.extend(list(self.sms._sgEA._sensorsMGS.keys()))
        
        # print(chNameList)
        
        self.rmw.graphWidget_gasSensorik.set_selectedChannelNames(chNameList)
            
            
            
            
        ###
        # Gas Durchfluss Regler
        
        # Verbinde Hardware
        self.sgr.sig_HWConnectFinished.connect(self.print_ConnectTryMessage)
        
        # Setze alles in 0-Position
        self.sgr.sig_HWConnectFinished.connect(self.sgr._set_initPosition)
        
        # Starten der Messschleife, sobald Verbindung hergestellt
        self.sgr.sig_HWConnectFinished.connect(self.sgr._start_MessSchleife)
        
        self.sgr._connect_Ports()
                  
                  
                  
        #########
        # Start der UI
                  
        self.showMaximized()
                          
        # Starte UI Update Timer
        self.timer_updateUI = QTimer()
        self.timer_updateUI.setInterval(self.UI_UPDATE_INTERVAL)
        self.timer_updateUI.timeout.connect(self.updateUI)
        self.timer_updateUI.start()
        
        
                

    def closeEvent(self, event):
        
        closeOK = True
        
        # Schließen verhindern, solange Sollwert > 0
        if(self.sgr.get_GesamtSollWert() > 0):
            
            msgBoxReg = QMessageBox()
            msgBoxReg.setWindowIcon(QIcon('symbols/lision.ico'))
            msgBoxReg.setIcon(QMessageBox.Warning)
            msgBoxReg.setText("Warnung! Die Regler wurden noch nicht geschlossen! Anwendung trotzdem schließen? \n\nHinweis: Es wird versucht, die Stellglieder zu schließen.")
            msgBoxReg.setWindowTitle("Anwendung schließen?")
            msgBoxReg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            
            returnValue = msgBoxReg.exec()
            
            if not returnValue == QMessageBox.Ok:
                closeOK = False
                

        if(closeOK):
            self._sig_close.emit()
            
            # Save ReglerConfig
            self.sgr.save_reglerConfig()
            
            # Save SensorConfig
            self.sms.save_sensorConfig()
            
            # Save PruefConfig
            self.rmw.pruefWidget.save_pruefConfig()
            
            print ("Regler UI closed")
        else:
            event.ignore()
            
            
            
            
    def switch_expertMode(self, checked):
        self.rmw.set_extendedFunctionVisibility(checked) 
        
            
    
    def print_ConnectTryMessage(self, check):
        if(check == 1): 
            self.sgr.protokoll.append(cw.ProtokollEintrag("Verbindung zur Hardware hergestellt", typ=cw.ProtokollEintrag.TYPE_SUCCESS))
        elif(check == -1):     
            self.sgr.protokoll.append(cw.ProtokollEintrag("Fehler beim Verbinden der Hardware!", typ=cw.ProtokollEintrag.TYPE_FAILURE))
    
    
    def print_ConnectTryMessage_SEC(self, check):
        if(check == 1): 
            self.sgr.protokoll.append(cw.ProtokollEintrag("Verbindung zur SEC-Hardware hergestellt", typ=cw.ProtokollEintrag.TYPE_SUCCESS))
        elif(check == -1):     
            self.sgr.protokoll.append(cw.ProtokollEintrag("Fehler beim Verbinden der SEC-Hardware!", typ=cw.ProtokollEintrag.TYPE_FAILURE))
    
    
    def print_ConnectTryMessage_GasGard(self, check):
        if(check == 1): 
            self.sgr.protokoll.append(cw.ProtokollEintrag("Verbindung zur GasGard-Hardware hergestellt!", typ=cw.ProtokollEintrag.TYPE_SUCCESS))
        elif(check == -1):     
            self.sgr.protokoll.append(cw.ProtokollEintrag("Fehler beim Verbinden der GasGard-Hardware!", typ=cw.ProtokollEintrag.TYPE_FAILURE))
    
    
    
    
    def open_help(self):
        help = hd.HelpDialog(self.TITEL, self.VERSION, self.YEAR)
        help.exec()
        
        
    def open_config(self):
        configUI = rc.ReglerConfigUI(self.sgr)
        configUI.exec()
        
        
    def open_config_sensors(self):
        configUIsensors = sc.SensorConfigUI(self.sms)
        configUIsensors.exec()
         
    
    def open_configNull(self):
        configNullUI = rcn.ReglerConfigNullUI(self.sgr)
        configNullUI.exec()
        
        
    def updateUI(self):
        # print ("update UI")
        self.rmw.console.update_Console()
        self.rmw.reglerTable.update_ReglerListWidget()
        
        if(self.ENABLE_SEC_MAGNET_SWITCH):
            self.rmw.smsWidget.update_SecMagnetSwitch()   
            self.rmw.mgsWidget.update_MGSWidget()


class ReglerMainWidget(QWidget):
    
    def __init__(self, mw):
        super().__init__()

        self.__mainWindow = mw

        self.setGeometry(100, 100, 800, 500)        

        self.mainLayout = QHBoxLayout()
        self.setLayout(self.mainLayout)
        
    #========================
    # LEFT
    #========================
        
        leftGroup = QGroupBox()
        self.leftLayout = QVBoxLayout()
        leftGroup.setLayout(self.leftLayout)
        self.mainLayout.addWidget(leftGroup)     
        
        self.leftLayout.setContentsMargins(0,0,0,0)
        
        #~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Graph
        #~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Regler
        
        # CurveNames
        chNames_SGR = []
        for p in mw.sgr._ports:
            chNames_SGR.append(p)
        
        self.graphWidget = mgw.MessdatenGraphWidget(self, mw.sgr.get_datamanager())
        self.leftLayout.addWidget(self.graphWidget)
        self.graphWidget.set_floatingWindowEnabled(False)
        self.graphWidget.sig_closeExternal.connect(self.closeMessdatenUI)
        
        
        # GasGard
        
        self.graphWidget_gasSensorik = mgw.MessdatenGraphWidget(self, mw.sgr.get_datamanager())
        self.leftLayout.addWidget(self.graphWidget_gasSensorik)
        self.graphWidget_gasSensorik.set_floatingWindowEnabled(False)
        self.graphWidget_gasSensorik.sig_closeExternal.connect(self.closeMessdatenUI_GasGard)
        
        
        
        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Data
        #~~~~~~~~~~~~~~~~~~~
        
        
        #--------------------------
        # Messdaten
        #---------------------------
        
        self.dataTable = mtw.MessdatenTableWidget(mw.sgr.get_datamanager())
        self.leftLayout.addWidget(self.dataTable)
        
        # DataLayout 
        
        dataGroup = QGroupBox()
        dataLayout = QHBoxLayout()
        dataGroup.setLayout(dataLayout)
        self.leftLayout.addWidget(dataGroup)  
        
        
        #------------------------------
        # Reglerliste
        #------------------------------
        
        self.reglerTable = ReglerListe_Widget(self.__mainWindow, self.__mainWindow.sgr)
        dataLayout.addWidget(self.reglerTable)
        

                

        

    #=========================
    # RIGHT Group
    #=========================


        rightGroup = QGroupBox()
        rightLayout = QVBoxLayout()
        rightGroup.setLayout(rightLayout)
        self.mainLayout.addWidget(rightGroup)   
        
        rightLayout.setContentsMargins(0,0,0,0)
        
        rightGroup.setFixedWidth(700)
        
        #-------------------------------
        # Gaszufuhr: Flaschen, Magnetschalter
        #---------------------------------
        if(self.__mainWindow.ENABLE_SEC_MAGNET_SWITCH):
            self.smsWidget = SecMagnetSwitch(self.__mainWindow.sms, self.__mainWindow.sgr)
            rightLayout.addWidget(self.smsWidget)
            
        
        #-------------------------------
        # Gassensoren: Gas Sensorik
        #---------------------------------
        
        gasSensorikGroup = QGroupBox("Gas Sensorik")
        gasSensorikLayout = QVBoxLayout()
        gasSensorikGroup.setLayout(gasSensorikLayout)
        rightLayout.addWidget(gasSensorikGroup)   
        
        # MGS Boxen
        
        self.mgsWidget = mgsw.MGSWidget(self.__mainWindow.sms)
        gasSensorikLayout.addWidget(self.mgsWidget)
        
        # GasGard XL
        
        self.gsWidget = gsw.GasGardWidget(self.__mainWindow.ggs)
        gasSensorikLayout.addWidget(self.gsWidget)
        # Statusanzeige
        self.__mainWindow.ggs.sig_NewGGStatus.connect(self.gsWidget.update_GasSensorStatus)
        
            
        #--------------------------------------
        # Prüfung und Messung Group
        #--------------------------------------
        
        self.pruefWidget = pw.PruefWidget(self.__mainWindow.sgr, self.__mainWindow.sms, self)
        self.pruefWidget._sig_pdfSaved.connect(self.handle_pdfExport)   
        rightLayout.addWidget(self.pruefWidget)
        
        
        #---------------------------
        # Console
        #------------------------
        
        self.console = cw.ConsoleWidget(self.__mainWindow.sgr.protokoll)
        rightLayout.addWidget(self.console)
             
            
    def set_extendedFunctionVisibility(self, extendedVis):
        
        self.reglerTable.set_extendedFunctionVisibility(extendedVis)
        self.dataTable.setVisible(extendedVis)
        self.pruefWidget.set_extendedFunctionVisibility(extendedVis)
    
            
        
    def handle_pdfExport(self, fName):
        if(fName != ""):
            self.__mainWindow.sgr.protokoll.append(cw.ProtokollEintrag("Protokoll gespeichert unter " + fName + "!", typ=cw.ProtokollEintrag.TYPE_SUCCESS))
        else:
            self.__mainWindow.sgr.protokoll.append(cw.ProtokollEintrag("Speichern des Graph fehlgeschlagen!", typ =  cw.ProtokollEintrag.TYPE_FAILURE))
            
        

    def display_data(self, data):
        # print (data)
        self.graphWidget.update_MessGraphWidget()
        self.graphWidget_gasSensorik.update_MessGraphWidget()
        self.pruefWidget.update_pruefWidget(data)
        self.gsWidget.update_GasSensorValues(data)
        
        
        
    def set_GraphRange(self, gesZeit):
        self.graphWidget.set_timeRangeOnFocus(gesZeit)
        self.graphWidget_gasSensorik.set_timeRangeOnFocus(gesZeit)
        
        
    def set_ManualModeEnabled(self, enabled):
        self.reglerTable.set_secLockOpen(enabled)
        # Menüsteuerung
        self.__mainWindow.configAct.setEnabled(enabled)
        self.__mainWindow.configNullAct.setEnabled(enabled)
        self.__mainWindow.configSensorAct.setEnabled(enabled)

    
    def closeMessdatenUI(self):
        self.leftLayout.insertWidget(0, self.graphWidget)


    def closeMessdatenUI_GasGard(self):
        self.leftLayout.insertWidget(1, self.graphWidget_gasSensorik)
        
        

############################################################################################################################
#
# Hilfsklassen
#-------------------------------------------------


class ReglerListe_Widget(QGroupBox):
    def __init__(self, parent, _setup):
        super().__init__("Reglerkonfiguration")
        
        self.parent = parent
        self.__setup = _setup
        
        
        mainLayout = QVBoxLayout()
        self.setLayout(mainLayout)
        
        mainLayout.setSpacing(0)
        
        self.reglerWidgets = {}
        # Header Zeile
        self.headerWidget = ReglerOverview_Widget(self.parent)
        mainLayout.addWidget(self.headerWidget)
        # Einzelen Regler
        for p in self.__setup._ports:
            row = ReglerOverview_Widget(self.parent, self.__setup._ports[p])
            
            row.setContentsMargins(0,0,0,0)
            
            self.reglerWidgets[p] = row
            mainLayout.addWidget(row)
        # Summenzeile
        self.sumReglerWidget = ReglerOverview_Widget(self.parent, sum=True, totalSet=self.__setup.get_GesamtSollWert(), totalIst=self.__setup.get_GesamtIstWert(),  gesBereich=self.__setup.get_ges_arbeitsBereich())
        mainLayout.addWidget(self.sumReglerWidget)


    def update_ReglerListWidget(self):
        for row in self.reglerWidgets:
            self.reglerWidgets[row].update_ReglerWidget()
        if (self.parent.rmw.pruefWidget.pruefung != None and self.parent.rmw.pruefWidget.pruefung._state == self.parent.rmw.pruefWidget.pruefung.PRUEF_STATE_RUNNING):
            self.sumReglerWidget.update_ReglerWidget(totalSet=self.__setup.get_GesamtSollWert(), totalIst=self.parent.rmw.pruefWidget.pruefung.get_pruefCurrentFlowSum(), hwStatus=self.__setup._hwConnectStatus, zaehlSum=self.parent.rmw.pruefWidget.pruefung.get_pruefCurrentMassSum())             
        else:
            self.sumReglerWidget.update_ReglerWidget(totalSet=self.__setup.get_GesamtSollWert(), totalIst=self.__setup.get_GesamtIstWert(), hwStatus=self.__setup._hwConnectStatus, zaehlSum=self.__setup.get_GesamtZaehlMenge())     


    def set_secLockOpen(self, open):
        for row in self.reglerWidgets:
            self.reglerWidgets[row].set_secLockOpen(open)
            
            
    def set_extendedFunctionVisibility(self, extendedVis):
        self.headerWidget.set_extendedFunctionVisibility(extendedVis)
        for row in self.reglerWidgets:
            self.reglerWidgets[row].set_extendedFunctionVisibility(extendedVis)
        self.sumReglerWidget.set_extendedFunctionVisibility(extendedVis)
            
            

class ReglerOverview_Widget(QGroupBox):
    
    WIDTH_ACTIVE = 25
    WIDTH_NAME = 25
    WIDTH_ARBEITSBEREICH = 120
    # WIDTH_PROGRESS = 200 # Bleibt frei
    WIDTH_IST = 120
    WIDTH_CNT = 120
    WIDTH_SETSPIN = 70
    WIDTH_SETPB = 50
    WIDTH_CLOSE = 50
    WIDTH_ENABLE = 50
    WIDTH_LOG = 100

    
    def __init__(self, parent, regler=None, sum=False, totalSet=0, totalIst=0, gesBereich=[]):
        
        super().__init__()
        self.parent = parent
        mainLayout = QHBoxLayout()
        self.setLayout(mainLayout)
        
        self.regler = regler
        self.sum = sum
        
        self.secLockOpen = True # Schließen, wenn Prüfung gestartet wird
        
        self.bildActive = QPixmap("symbols/light_green.png")
        self.bildWarning = QPixmap("symbols/light_yellow.png")
        self.bildInactive = QPixmap("symbols/light_red.png")
        
        # Border
        if(sum):
            self.setObjectName("sumReglerWidget")
            self.setStyleSheet("QWidget#sumReglerWidget {border-top: 1px solid black;}")
        else:
            if(regler == None):
                self.setObjectName("headerReglerWidget")
                self.setStyleSheet("QWidget#headerReglerWidget {border-bottom: 1px solid black;}")
        
        
        self.lActive = QLabel("")
            
        self.lName = QLabel()
        self.lName.setFont(LisionStyle.LABEL_FONT_BOLD)  
        
        self.lArbeitsbereich = QLabel()
        self.lArbeitsbereich.setAlignment(Qt.AlignCenter)
            
        self.lIstwert = QLabel()
        self.lIstwert.setAlignment(Qt.AlignCenter)
        
        self.lCounter = QLabel()
        self.lCounter.setAlignment(Qt.AlignCenter)
        
        self.pbOpenReglerOutputLog = QLabel("")
        
        self.pbSetSoll = QPushButton("Set")
            
        # Inhalte anpassen

        # Header
        name = "" if (not sum) else "\u03A3"
        bereich = "Bereich [g/min]" 
        istwert = "Durchfluss Ist"
        counter = "Menge Ist"
        
        
        
        if(regler != None):
            # Widget ist einem einzelnen Regler zugordnet
            
            # Active
            self.lActive.setPixmap(self.bildInactive)
            # Name
            name = regler.get_name()
            # Arbeitsbereich
            bereich = str(regler.get_arbeitsBereich())
            self.lArbeitsbereich.setEnabled(False)
            # Stellwert
            self.pStellwert = QProgressBar(self)
            self.pStellwert.setAlignment(Qt.AlignCenter)
            self.pStellwert.setValue(int(regler.get_soll_percentage()))
            self.pStellwert.setFormat("" + str(regler.get_soll()) + " g/min")
            # Istwert
            istwert = str(regler.get_ist())
            self.lIstwert.setStyleSheet("background-color: white; border: 1px solid black;")
            # Counter
            counter = str(regler.get_cnt())
            self.lCounter.setStyleSheet("background-color: white; border: 1px solid black;")
            # Set Soll
            self.sSetSoll = QDoubleSpinBox()
            self.sSetSoll.setMinimum(regler.get_arbeitsBereich()[0])
            self.sSetSoll.setMaximum(regler.get_arbeitsBereich()[1])
            self.sSetSoll.setSingleStep(0.01)   
            self.pbSetSoll.clicked.connect(self.pbSetSollClicked)         
            # Close
            self.pbClose = QPushButton("Close")
            self.pbClose.clicked.connect(self.pbCloseClicked)
            # Enable
            self.cbEnable = QCheckBox()
            self.cbEnable.setChecked(True)
            self.cbEnable.stateChanged.connect(self.cbEnable_stateChanged)
            # Log
            self.pbOpenReglerOutputLog = QPushButton("Log...")
            self.pbOpenReglerOutputLog.clicked.connect(self.pbOpenReglerOutputLogClicked)
            
        else:
            # Widget ist keinem Einzelnen Regler zugordnet
            
            if(not sum):
                # HEADER
                self.lArbeitsbereich.setFont(LisionStyle.LABEL_FONT_BOLD)
                
                self.sSetSoll = QLabel("Setze Soll")
                self.sSetSoll.setFont(LisionStyle.LABEL_FONT_BOLD)
                
                self.pbSetSoll = QLabel("")
                self.pbClose = QLabel("")
                
                self.cbEnable = QLabel ("Aktiv")
                self.cbEnable.setFont(LisionStyle.LABEL_FONT_BOLD)
                
                self.pbOpenReglerOutputLog = QLabel("")
                
            else:
                # SUMME (Untere Zeile)
                
                bereich = str(gesBereich)
                
                
            self.pStellwert = QLabel("Sollwert")
            self.pStellwert.setAlignment(Qt.AlignCenter)
            self.pStellwert.setFont(LisionStyle.LABEL_FONT_BOLD)  
            self.lIstwert.setFont(LisionStyle.LABEL_FONT_BOLD)  
            self.lCounter.setFont(LisionStyle.LABEL_FONT_BOLD)
            
            
            if(sum):
                self.lActive.setPixmap(self.bildInactive)
                   
                self.pStellwert.setText(str(totalSet))
                
                self.sSetSoll = QDoubleSpinBox()
                self.sSetSoll.setMinimum(gesBereich[0])
                self.sSetSoll.setMaximum(gesBereich[1])
                self.sSetSoll.setSingleStep(0.01) 
                    
                self.pbClose = QPushButton("Close")
                
                self.cbEnable = QLabel("")
                
                istwert = str(totalIst)
                

        # Breiten
        self.lActive.setFixedWidth(self.WIDTH_ACTIVE)
        self.lName.setFixedWidth(self.WIDTH_NAME)
        self.lArbeitsbereich.setFixedWidth(self.WIDTH_ARBEITSBEREICH)
        self.lIstwert.setFixedWidth(self.WIDTH_IST)
        self.lCounter.setFixedWidth(self.WIDTH_CNT)
        self.sSetSoll.setFixedWidth(self.WIDTH_SETSPIN)
        self.pbSetSoll.setFixedWidth(self.WIDTH_SETPB)
        self.pbClose.setFixedWidth(self.WIDTH_CLOSE)
        self.cbEnable.setFixedWidth(self.WIDTH_ENABLE)
        self.pbOpenReglerOutputLog.setFixedWidth(self.WIDTH_LOG)
            

        # Füge Widgets zur GUI hinzu
        mainLayout.addWidget(self.lActive)
        mainLayout.addWidget(self.lName)
        mainLayout.addWidget(self.lArbeitsbereich) 
        
        # Zentriere Stellwert-Label
        if(regler == None):
            mainLayout.addStretch(1)
        mainLayout.addWidget(self.pStellwert)
        if(regler == None):
            mainLayout.addStretch(1)
            
        mainLayout.addWidget(self.lIstwert)
        mainLayout.addWidget(self.lCounter)
        mainLayout.addWidget(self.sSetSoll)
        mainLayout.addWidget(self.pbSetSoll)
        mainLayout.addWidget(self.pbClose)
        mainLayout.addWidget(self.cbEnable)
        mainLayout.addWidget(self.pbOpenReglerOutputLog)
            
            
        self.lName.setText(name)
        self.lArbeitsbereich.setText(bereich)
        self.lIstwert.setText(istwert)
        self.lCounter.setText(counter)
        
        
    def set_extendedFunctionVisibility(self, extendedVis):

            self.sSetSoll.setVisible(extendedVis)  
            self.pbSetSoll.setVisible(extendedVis)      
            self.pbClose.setVisible(extendedVis)
            self.cbEnable.setVisible(extendedVis)
            self.pbOpenReglerOutputLog.setVisible(extendedVis)
            self.lCounter.setVisible(extendedVis)
        
    
    def pbSetSollClicked(self):
        self.regler.set_Sollwert(self.sSetSoll.value())
        
    
    def pbCloseClicked(self):
        self.regler.set_Sollwert(0)
    
    
    def pbOpenReglerOutputLogClicked(self):
        logWidget = rrol.ReglerReadOutputLog(self.parent, self.regler)
    
    
    def cbEnable_stateChanged(self):
        # Wenn Regler deaktivert wird: Auf 0 setzen.
        if(not self.cbEnable.isChecked()):
            self.regler._close()
        
        self.regler.set_enabled(self.cbEnable.isChecked())
    
        
    def update_ReglerWidget(self, totalSet=0, totalIst=0, hwStatus=-1, zaehlSum=0):
        
        if(self.regler != None):
            
            # Aktiviert
            self.lArbeitsbereich.setEnabled(self.cbEnable.isChecked())
            self.pStellwert.setEnabled(self.cbEnable.isChecked())
            self.lIstwert.setEnabled(self.cbEnable.isChecked())
            self.lCounter.setEnabled(self.cbEnable.isChecked())
            self.sSetSoll.setEnabled(self.cbEnable.isChecked())
            self.pbSetSoll.setEnabled(self.cbEnable.isChecked())
            self.pbClose.setEnabled(self.cbEnable.isChecked())
            
                                  
            # Prüfung Running
            self.sSetSoll.setEnabled(self.secLockOpen)
            self.pbSetSoll.setEnabled(self.secLockOpen)
            self.pbClose.setEnabled(self.secLockOpen)
            self.cbEnable.setEnabled(self.secLockOpen)
            
            
            
            # Connection            
            if(self.regler.connected == False):
                self.lActive.setPixmap(self.bildInactive)
                    
                self.lArbeitsbereich.setEnabled(False)
                self.pStellwert.setEnabled(False)
                self.lIstwert.setEnabled(False)
                self.lCounter.setEnabled(False)
                self.sSetSoll.setEnabled(False)
                self.pbSetSoll.setEnabled(False)
                self.pbClose.setEnabled(False)
                self.cbEnable.setEnabled(False)
                
            else:
                self.lActive.setPixmap(self.bildActive)
                self.lIstwert.setText("{:4.2f}".format(self.regler.get_ist()))
                self.lCounter.setText("{:4.2f}".format(self.regler.get_cnt()))
                

            # Disable unimplemented Functions
            # self.sSetSoll.setEnabled(False)
            # self.pbSetSoll.setEnabled(False)
            
            # Update Ist-Stellwert 
            self.pStellwert.setValue(int(self.regler.get_soll() / self.regler.get_arbeitsBereich()[1] * 100))
            self.pStellwert.setFormat("{:4.2f}".format(self.regler.get_soll()) + " g/min")
            styleSheet = "QProgressBar::chunk {background-color: yellow;}" if(self.regler.get_soll_percentage() <= 10 or  self.regler.get_soll_percentage() >= 90) else "QProgressBar::chunk {background-color: green;}"
            self.pStellwert.setStyleSheet(styleSheet)
            

        else:
            # Kein Regler zugewiesn sondern HEader oder SUm
            
            self.pStellwert.setText("{:4.2f}".format(totalSet) + " g/min")
            self.lIstwert.setText("{:4.2f}".format(totalIst) + " g/min")
            self.lCounter.setText("{:4.2f}".format(zaehlSum) + " g")
            
            # Statusanzeige HW-Connection
            if(hwStatus == hs.HWSetup.HW_CONNECT_STATUS_NONE):
                self.lActive.setPixmap(self.bildInactive)
            elif(hwStatus == hs.HWSetup.HW_CONNECT_STATUS_FAILURE):
                self.lActive.setPixmap(self.bildWarning)
            else:
                self.lActive.setPixmap(self.bildActive)
                
            # Disable unimplemented Functions
            self.pbClose.setEnabled(False)
            self.pbSetSoll.setEnabled(False)
            self.sSetSoll.setEnabled(False)
        
        
        
    
    def set_secLockOpen(self, open):
        self.secLockOpen = open


        
        
      
class SecMagnetSwitch(QGroupBox):
    
    def __init__(self, sms, sgr):
        super().__init__("Gas-Zufuhr")
        mainLayout = QVBoxLayout()
        self.setLayout(mainLayout)
        
        self.sms = sms
        self.sgr = sgr

        
        #############################
        # Data
        #############################
        
        dataGroup = QGroupBox("Gas-Flaschen")
        dataLayout = QVBoxLayout()
        dataGroup.setLayout(dataLayout)
        mainLayout.addWidget(dataGroup)
        
        # Gas Flaschen Sensoren
        self.gasGroups = {}
        for i, s in enumerate(self.sms._sgEA._sensors):
            self.gasGroups[s] = GasData_Widget(s, i+1, sms)
            dataLayout.addWidget(self.gasGroups[s])
    
    
    def update_SecMagnetSwitch(self):
        if(self.sms != None):
            
            # Connection
            if(self.sms._secConnectStatus == self.sms.SEC_CONNECT_STATUS_NONE):
                # NOT CONNECTED
                pass
                
            else:
                # CONNECTED                
                # Gas Vordruck
                for s in self.gasGroups:
                    self.gasGroups[s].update_GasData(self.sms.dataGas[s]["FP"], self.sms.dataGas[s]["TP"])
                
                
class GasData_Widget(QGroupBox):
    
    def __init__(self, name, ventilNr, sms):
        super().__init__(name)
        
        self.ventilNr = ventilNr
        self.sms = sms
        
        dataLeftLayout = QHBoxLayout()
        self.setLayout(dataLeftLayout)
        dataLeftLayout.setContentsMargins(5,5,5,5)
        
        self.cbActive = QCheckBox()
        dataLeftLayout.addWidget(self.cbActive)
        self.cbActive.clicked.connect(self._toggleMagVentOpen)
        
        # FP
        fpGroup = QGroupBox()
        fpLayout = QHBoxLayout()
        fpLayout.setContentsMargins(0,0,0,0)
        fpGroup.setLayout(fpLayout)
        dataLeftLayout.addWidget(fpGroup)
        self.iFP = QLabel("Gas-Druck")
        self.iFP.setFixedWidth(100)
        fpLayout.addWidget(self.iFP)
        self.tFP = QLineEdit("")
        self.tFP.setFixedWidth(60)
        self.tFP.setReadOnly(True)
        self.tFP.setAlignment(QtCore.Qt.AlignCenter)
        fpLayout.addWidget(self.tFP)
        self.lFP = QLabel("bar")
        self.lFP.setFixedWidth(60)
        fpLayout.addWidget(self.lFP)
        
        # TP
        tpGroup = QGroupBox()
        tpLayout = QHBoxLayout()
        tpLayout.setContentsMargins(0,0,0,0)
        tpGroup.setLayout(tpLayout)
        dataLeftLayout.addWidget(tpGroup)
        self.iTP = QLabel("Gas-Temp.")
        self.iTP.setFixedWidth(100)
        tpLayout.addWidget(self.iTP)
        self.tTP = QLineEdit("")
        self.tTP.setFixedWidth(60)
        self.tTP.setReadOnly(True)
        self.tTP.setAlignment(QtCore.Qt.AlignCenter)
        tpLayout.addWidget(self.tTP)
        self.lTP = QLabel("°C")
        self.lTP.setFixedWidth(60)
        tpLayout.addWidget(self.lTP)
    
    
    def update_GasData(self, fp, tp):
 
        if(type(fp) == float):
            fp = "{:4.1f}".format(fp)
            self.tFP.setText(fp)
        if(type(tp) == float):
            tp = "{:4.1f}".format(tp)
            self.tTP.setText(tp)        
            
            
    def _toggleMagVentOpen(self):
        self.sms.set_sms_open(self.ventilNr, self.cbActive.isChecked())
        
    
            

if __name__ == '__main__':

    # IP-Adresse des WAGO Feldbuskopplers
    wagoIP = '172.20.20.2'
    gasgardIP = '172.20.30.2'

    app = QApplication(sys.argv)
   
    # SecSetup (Magnetschalter)
    sgEA = SimGasEA(wagoIP) 
    sms = ss.SecSetup(sgEA)
    
    # Regel Stellglieder
    sgr = rs.SimGasRegler(sgEA)
    
    # GasGard Sensorik
    ggEA = GasGardEA(gasgardIP)
    ggs = gs.GasGardSetup(ggEA)


    # Öffne Anzeige
    main = ReglerUI(sgr, sms, ggs)

    ec = app.exec_()
    
    if(sgr.terminated):
        print ("Programm regulär geschlossen.")
    else:   
        sgr._close_hwSetup()
        print ("Programm abgestürzt!")
