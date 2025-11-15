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

import lock
import logger
import exportConfig

import hwSetup as hs
import reglerSetup as rs
import messdatenGraphWidget as mgw
import messdatenTableWidget as mtw
import mgsWidget as mgsw
import gasGardWidget as gsw
import pruefWidget as pw
import consoleWidget as cw
import helpDialog as hd
import expertModeEnterPW as emepw
import exportConfigUI as ecui
import reglerConfigUI as rc
import sensorConfigUI as sc
import reglerConfigNullUI as rcn
import zuschaltGrenzwerteConfigUI as zgc
import secSetup as ss
import reglerReadOutputLog as rrol
import gasGardSetup as gs

import entlueftung as entl
import befuellen as befu

class ReglerUI(QMainWindow):
    
    TITEL = "SimGas Regler GUI - CORI"
    VERSION = "0.19"
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
    
    def __init__(self, sgr, sms, ggs, app):
        super().__init__()
    
        # lade HW-Setup
    
        self.sgr = sgr
        self.sms = sms
        self.ggs = ggs
        
        self.befuellungsvorgang = None
        self.entlueftungsvorgang = None
            
        self.rmw = ReglerMainWidget(self)     
        self.setCentralWidget(self.rmw)  
        
        # Hide Extended Functions
        self.extendedFunctions = self.SHOW_EXTENDED_FUNCTIONS
        self.rmw.set_extendedFunctionVisibility(self.SHOW_EXTENDED_FUNCTIONS) 
                
        self.setWindowTitle(self.TITEL)
        self.setWindowIcon(QIcon("symbols/lision.ico"))
        
        # self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint)
    

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
            
        self.configZuGrenz = QAction('&Zuschaltungsgrenzwerte', self)
        self.configZuGrenz.setStatusTip('Zuschaltungsgrenzwerte')
        self.configZuGrenz.triggered.connect(self.open_configZuschaltGrenzwerte)
        configMenu.addAction(self.configZuGrenz)

        self.configExport = QAction('&Exportkonfiguration', self)
        self.configExport.setStatusTip('Exportkonfiguration')
        self.configExport.triggered.connect(self.open_configExport)
        configMenu.addAction(self.configExport)
        
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
            # Verbindungsstatus
            self.sms._sig_disableMGS.connect(self.print_DisableMessage_MGSBox)
            self.sms._sig_disableMGS.connect(self.hide_MGSBoxSensors)
            self.sms._sig_enableMGS.connect(self.print_EnableMessage_MGSBox)
            self.sms._sig_enableMGS.connect(self.show_MGSBoxSensors)          
            self.sms._sig_disableGasSensor.connect(self.print_DisableMessage_GasSensor)  
            
            # Starten der SEC-Messschleife, sobald Verbindung hergestellt
            self.sms.sig_SEC_ConnectFinished.connect(self.sms._start_MessSchleife) 
            # Ankommende Vordruck Daten in DataManager einspeisen
            self.sgr.get_datamanager().addChannels(list(self.sms._sgEA._sensors.keys()))           
            # Ankommende MGSBoxen Daten in DataManager einspeisen
            self.sgr.get_datamanager().addChannels(list(self.sms._sgEA._sensorsMGS.keys()))
            # channel labels
            secLabels = {}
            for s in self.sms._sgEA._sensors:
                secLabels[s] = self.sms._sgEA._sensors[s]["data_label"]
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
            # Verbindungsstatus
            self.ggs._sig_disableGG.connect(self.print_DisableMessage_GasGard)
            self.ggs._sig_disableGG.connect(self.hide_GasGardSensors)
            self.ggs._sig_enableGG.connect(self.print_EnableMessage_GasGard)
            self.ggs._sig_enableGG.connect(self.show_GasGardSensors)
            
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
        
        self.rmw.graphWidget_gasSensorik.set_selectedChannelNames(chNameList)

        # Set eingeblendete Gas Sensoren
        self.update_gasSensorGraphVisibilities()

        
        # Diagramm Gaszufuhr
        self.rmw.graphWidget.set_selectedChannelNames(["COM1", "COM1_SOLL", "COM2", "COM2_SOLL", "COM3", "COM3_SOLL", "GES_IST", "GES_SOLL", "Gasflasche 1", "Gasflasche 2", "Gasflasche 3"])
        self.rmw.graphWidget.graphWidget.setCurveVisibility(self.rmw.pruefWidget.conf["visibility"])


            
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
        # self.setFixedSize(app.primaryScreen().size().width()-2, app.primaryScreen().size().height()-10)
                          
        # Starte UI Update Timer
        self.timer_updateUI = QTimer()
        self.timer_updateUI.setInterval(self.UI_UPDATE_INTERVAL)
        self.timer_updateUI.timeout.connect(self.updateUI)
        self.timer_updateUI.start()
        
    
    def moveEvent(self, event):
        #self.move(0,0)
        event.ignore()
        
        
    def closeEvent(self, event):
        
        closeOK = True
        
        # Schließen verhindern, wenn Befüllungsvorgang läuft
        if(self.befuellungsvorgang != None):
            closeOK = False
            
            msgBoxReg = QMessageBox()
            msgBoxReg.setWindowIcon(QIcon('symbols/lision.ico'))
            msgBoxReg.setIcon(QMessageBox.Warning)
            msgBoxReg.setText("Die Software kann nicht geschlossen werden, solange ein Befüllungsvorgang läuft!")
            msgBoxReg.setWindowTitle("Befüllungsvorgang läuft nocht!")
            msgBoxReg.setStandardButtons(QMessageBox.Ok)
        
            msgBoxReg.exec()
        
        # Schließen verhindern, wenn Entlüftungsvorgang läuft
        if(self.entlueftungsvorgang != None):
            closeOK = False
            
            msgBoxReg = QMessageBox()
            msgBoxReg.setWindowIcon(QIcon('symbols/lision.ico'))
            msgBoxReg.setIcon(QMessageBox.Warning)
            msgBoxReg.setText("Die Software kann nicht geschlossen werden, solange ein Entlüftungsvorgang läuft!")
            msgBoxReg.setWindowTitle("Entlüftungsvorgang läuft nocht!")
            msgBoxReg.setStandardButtons(QMessageBox.Ok)
        
            msgBoxReg.exec()
           
        
        # Schließen verhindern, solange Sollwert > 0
        if(closeOK and self.sgr.get_GesamtSollWert() > 0):
            
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
            self.ggs.save_sensorConfig()

            # Save ZuschaltConfig
            self.sms.save_zuschaltungsGrenzwertConfig()
            
            # Save PruefConfig
            self.rmw.pruefWidget.save_pruefConfig()
            
            
            print ("Regler UI closed")
        else:
            event.ignore()
            
            
            
            
    def switch_expertMode(self, checked):
        if(checked):
            enterPWDialog = emepw.DialogExpertModeEnterPW()
            enterPWDialog.sig_pw.connect(self.checkExpertModePW)
            enterPWDialog.exec()
        else:
            self.rmw.set_extendedFunctionVisibility(False)   
        
        
    def checkExpertModePW(self, pw):
        if(pw):
            self.rmw.set_extendedFunctionVisibility(True)
        else:
            # self.rmw.set_extendedFunctionVisibility(False)
            print("Falsches Expert Mode Passwort!")
            self.configExpertModeAct.trigger()


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
    
    
    # GasGard

    def print_ConnectTryMessage_GasGard(self, check):
        if(check == 1): 
            self.sgr.protokoll.append(cw.ProtokollEintrag("Verbindung zur GasGard-Hardware hergestellt!", typ=cw.ProtokollEintrag.TYPE_SUCCESS))
        elif(check == -1):     
            self.sgr.protokoll.append(cw.ProtokollEintrag("Fehler beim Verbinden der GasGard-Hardware!", typ=cw.ProtokollEintrag.TYPE_FAILURE))
    
    
    def print_DisableMessage_GasGard(self):
        self.sgr.protokoll.append(cw.ProtokollEintrag("GasGard Sensorik nicht verbunden.", typ=cw.ProtokollEintrag.TYPE_WARNING))
    
    
    def print_EnableMessage_GasGard(self):
        self.sgr.protokoll.append(cw.ProtokollEintrag("GasGard Sensorik verbunden.", typ=cw.ProtokollEintrag.TYPE_SUCCESS))
        
    
    def hide_GasGardSensors(self):
        self.rmw.gsWidget.setEnabled(False)
        self.rmw.gsWidget.setTitle("GasGard XL - offline")
    
    def show_GasGardSensors(self):
        self.rmw.gsWidget.setEnabled(True)
        self.rmw.gsWidget.setTitle("GasGard XL - online")

    # Gas Sensor

    def print_DisableMessage_GasSensor(self, sensor):
        self.sgr.protokoll.append(cw.ProtokollEintrag(f"Sensor {sensor} nicht verbunden.", typ=cw.ProtokollEintrag.TYPE_WARNING))


    # MGS    
    
    def print_DisableMessage_MGSBox(self, box):
        self.sgr.protokoll.append(cw.ProtokollEintrag(f"MGS Box {box} nicht verbunden.", typ=cw.ProtokollEintrag.TYPE_WARNING))
        
        
    def print_EnableMessage_MGSBox(self, box):
        self.sgr.protokoll.append(cw.ProtokollEintrag(f"MGS Box {box} verbunden.", typ=cw.ProtokollEintrag.TYPE_SUCCESS))
    
    
    def hide_MGSBoxSensors(self, box):
        self.rmw.mgsWidget.hide_MGSBox(box)
    
    
    def show_MGSBoxSensors(self, box):
        self.rmw.mgsWidget.show_MGSBox(box)
    
    
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
        
        
    def open_configZuschaltGrenzwerte(self):
        configZuschaltungUI = zgc.ZuschaltGrenzwerteConfigUI(self.sms)
        configZuschaltungUI.exec()
        

    def open_configExport(self):

        # Get Curve Visibility from 
        for c, vis in self.rmw.graphWidget_gasSensorik.graphWidget.getCurveVisibility().items():
            if (c in exportConfig.channelExportConfigs):
                exportConfig.channelExportConfigs[c]["active"] = vis

        configExportUI = ecui.ExportConfigUI()
        configExportUI.sig_exportConfig_changed.connect(self.update_gasSensorGraphVisibilities)
        configExportUI.exec()

        
    def updateUI(self):
        # print ("update UI")
        self.rmw.console.update_Console()
        self.rmw.reglerTable.update_ReglerListWidget()
        
        if(self.ENABLE_SEC_MAGNET_SWITCH):
            self.rmw.smsWidget.update_SecMagnetSwitch()   
            self.rmw.mgsWidget.update_MGSWidget()


    def update_gasSensorGraphVisibilities(self):
        visibleGasSensors = {}
        for s in exportConfig.channelExportConfigs:
            visibleGasSensors[s] = exportConfig.channelExportConfigs[s]["active"]
        self.rmw.graphWidget_gasSensorik.graphWidget.setCurveVisibility(visibleGasSensors)




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
            self.smsWidget = SecMagnetSwitch(self.__mainWindow, self.__mainWindow.sms, self.__mainWindow.sgr)
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
        self.smsWidget._sig_updateZuschaltung.connect(self.pruefWidget.updateFlaschenZuschaltung)
        self.smsWidget._sig_updateZuschaltung.connect(self.smsWidget.updateFlaschenZuschaltung)
        self.smsWidget.updateFlaschenZuschaltung()
        rightLayout.addWidget(self.pruefWidget)
        
        
        #---------------------------
        # Console
        #------------------------
        
        self.console = cw.ConsoleWidget(self.__mainWindow.sgr.protokoll)
        rightLayout.addWidget(self.console)
        self.console.setFixedHeight(111)
        
        rightLayout.addStretch(1)
        
             
            
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
        self.__mainWindow.configZuGrenz.setEnabled(enabled)
        # Flaschenzuschaltung
        self.smsWidget.enableFlaschenZuschaltungen(enabled)
        if(enabled == False):
            self.smsWidget.enableBefuellungUndEntlueft(enabled)
    
    
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

            ReglerUI.SHOW_EXTENDED_FUNCTIONS = extendedVis

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
        
        
        
    
    def set_secLockOpen(self, _open):
        self.secLockOpen = _open


        
        
      
class SecMagnetSwitch(QGroupBox):
    
    _sig_updateZuschaltung = pyqtSignal()
    
    def __init__(self, mw, sms, sgr):
        super().__init__("Gas-Zufuhr")
        mainLayout = QVBoxLayout()
        self.setLayout(mainLayout)
        
        self.mw = mw
        self.sms = sms
        self.sgr = sgr
        
        #############################
        # Data
        #############################
        
        # Gas Flaschen Sensoren
        self.gasGroups = {}
        for s in self.sms._sgEA._sensors:
            gdw = GasData_Widget(s, sms)
            self.gasGroups[s] = gdw
            gdw._sig_updateZuschaltung.connect(self._sig_updateZuschaltung.emit)
            mainLayout.addWidget(self.gasGroups[s])
            
            
        ##############################
        # GAS Befüllung und Entlüftung
        ##################
        
        gasBefEntWidget = QWidget()
        gasBefEntLayout = QHBoxLayout()
        gasBefEntWidget.setLayout(gasBefEntLayout)
        mainLayout.addWidget(gasBefEntWidget)
        
        
        gasBefEntLayout.setContentsMargins(0,0,0,0)
        
        # Befüllen
        self.buttonBefuellen = QPushButton("Prüfanlage befüllen")
        self.buttonBefuellen.clicked.connect(self.buttonBefuellen_clicked)
        self.buttonBefuellen.setFixedWidth(150)
        self.buttonBefuellen.setEnabled(True)
        gasBefEntLayout.addWidget(self.buttonBefuellen)    
    
        # Entlüftung
        self.buttonEntlueften = QPushButton("Prüfanlage entlüften")
        self.buttonEntlueften.clicked.connect(self.buttonEntlueften_clicked)
        self.buttonEntlueften.setFixedWidth(150)
        self.buttonEntlueften.setEnabled(True)
        gasBefEntLayout.addWidget(self.buttonEntlueften)
        

    # Befüllungsvorgang
    def buttonBefuellen_clicked(self):
        
        self.mw.befuellungsvorgang = befu.Befuellen(self.sgr, self.sms)
        self.mw.befuellungsvorgang.sig_befuellung_finished.connect(self.befuellungsvorgangBeendet)
        if(self.mw.befuellungsvorgang.initBefuellung()):
            self.mw.rmw.pruefWidget.pbStartPruefung.setEnabled(False)
            self.mw.rmw.set_ManualModeEnabled(False)
        else:
            self.mw.befuellungsvorgang = None
        
        
    def befuellungsvorgangBeendet(self):
        self.mw.befuellungsvorgang = None   
        self.mw.rmw.set_ManualModeEnabled(True)

        self.clear_allFlaschenZuschaltungen()

        self._sig_updateZuschaltung.emit()


    #Entlüftungsvorgang
    def buttonEntlueften_clicked(self):
        
        self.mw.entlueftungsvorgang = entl.Entlueftung(self.sgr, self.sms)
        self.mw.entlueftungsvorgang.sig_entlueftung_finished.connect(self.entlueftungsvorgangBeendet)
        if(self.mw.entlueftungsvorgang.initEntlueftung()):
            self.mw.rmw.pruefWidget.pbStartPruefung.setEnabled(False)
            self.mw.rmw.set_ManualModeEnabled(False)
        else:
            self.mw.entlueftungsvorgang = None
            
        
    def entlueftungsvorgangBeendet(self):
        self.mw.entlueftungsvorgang = None
        self.mw.rmw.set_ManualModeEnabled(True)  
        
        self.clear_allFlaschenZuschaltungen()
        
        self._sig_updateZuschaltung.emit()
        
        # self.test.emit()
        
        
    # update
    
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
                    
                    
                    
    def enableFlaschenZuschaltungen(self, enable):
        for s in self.gasGroups:
            self.gasGroups[s].setZuschaltungEnabled(enable)
    
    
    def enableBefuellungUndEntlueft(self, enable):
        self.buttonBefuellen.setEnabled(enable)
        self.buttonEntlueften.setEnabled(enable)
        
    
    def clear_allFlaschenZuschaltungen(self):
        for s in self.gasGroups:
            self.gasGroups[s]._setMagVentClosed()
             
        self._sig_updateZuschaltung.emit()
            
    def updateFlaschenZuschaltung(self):
        
        enableBelueftung = False
        enableEntlueftung = True
        
        for s in self.sms.zuschaltung:
            # print(f"UpdateFlaschenZuschaltung: Zuschaltung: {s}: {self.sms.zuschaltung[s]}")
            if(self.sms.zuschaltung[s] == True):
                enableBelueftung = True
                enableEntlueftung = False
        
        # Aktivierung Befüllung und Entlüftung je nach Zuschaltung
        self.buttonBefuellen.setEnabled(enableBelueftung) 
        self.buttonEntlueften.setEnabled(enableEntlueftung)
    
    
                
class GasData_Widget(QGroupBox):
    
    _sig_updateZuschaltung = pyqtSignal()
    
    def __init__(self, name, sms):
        super().__init__(name)
        
        self.s = name
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
            
            
    def setZuschaltungEnabled(self, enabled):
        self.cbActive.setEnabled(enabled)
            
            
    def _setMagVentClosed(self):
        self.cbActive.setChecked(False)
        self.sms.set_sms_zuschaltung(self.s, False) 
        self._sig_updateZuschaltung.emit()
    
            
    def _toggleMagVentOpen(self):
        
        # Prüfe Zuschaltung der Flasche
        if(self.cbActive.isChecked()):
            
            zuschaltungOK = self.sms.checkFlaschenZuschaltung(self.s)

            # Keine Daten zu Flaschendruck vorhanden
            if(zuschaltungOK == -1):
                
                self.cbActive.setChecked(False)
                
                msgBoxReg = QMessageBox()
                msgBoxReg.setWindowIcon(QIcon('symbols/lision.ico'))
                msgBoxReg.setIcon(QMessageBox.Warning)
                msgBoxReg.setText("Achtung! Es sind keine Daten zum Flaschen-Druck vorhanden!\nFlasche kann für die Prüfung nicht verwendet werden!")
                msgBoxReg.setWindowTitle("Keine Daten!")
                msgBoxReg.setStandardButtons(QMessageBox.Ok)
                
                returnValue = msgBoxReg.exec()

            # Eigendruck zu niedrig
            elif(zuschaltungOK == 1):
                
                self.cbActive.setChecked(False)
                
                msgBoxReg = QMessageBox()
                msgBoxReg.setWindowIcon(QIcon('symbols/lision.ico'))
                msgBoxReg.setIcon(QMessageBox.Warning)
                msgBoxReg.setText("Achtung! Der Druck der gewählten Flasche ist zu niedrig!\nFlasche kann für die Prüfung nicht verwendet werden!")
                msgBoxReg.setWindowTitle("Flaschendruck zu niedrig!")
                msgBoxReg.setStandardButtons(QMessageBox.Ok)
                
                returnValue = msgBoxReg.exec()

            # Differenzdruck zu hoch
            elif(zuschaltungOK == 2):
            
                self.cbActive.setChecked(False)
                
                msgBoxReg = QMessageBox()
                msgBoxReg.setWindowIcon(QIcon('symbols/lision.ico'))
                msgBoxReg.setIcon(QMessageBox.Warning)
                msgBoxReg.setText("Achtung! Der Druckunterschied zwischen den gewählten Flaschen ist zu hoch!\nFlasche kann für die Prüfung nicht verwendet werden!")
                msgBoxReg.setWindowTitle("Druckdifferenz zu hoch!")
                msgBoxReg.setStandardButtons(QMessageBox.Ok)
                
                returnValue = msgBoxReg.exec()        
                
            
        # Schalten durchführen   
        self.sms.set_sms_zuschaltung(self.s, self.cbActive.isChecked()) 
        
        if(ReglerUI.SHOW_EXTENDED_FUNCTIONS):
            self.sms.set_sms_open(self.s, self.cbActive.isChecked())
        
        self._sig_updateZuschaltung.emit()


        
        
        

if __name__ == '__main__':


    wagoIP = '172.20.20.2'
    gasgardIP = '172.20.30.2'

    if(not lock.islocked()):
        lock.lock()
    
        log = logger.Logger()
        #log.startExternalLogging("log")

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
        main = ReglerUI(sgr, sms, ggs, app)

        ec = app.exec_()
        
        if(sgr.terminated):
            print ("Programm regulär geschlossen.")
            lock.unlock()
        else:   
            sgr._close_hwSetup()
            print ("Programm abgestürzt!")

        #log.stopExternalLogging()

    else:
        print("Es läuft bereits eine Instanz von SimGasUI!\nLöschen Sie andernfalls die Datei simgas.lock!")
        # lock.showMsgLocked("Es läuft bereits eine Instanz von SimGasUI!\nLöschen Sie andernfalls die Datei simgas.lock vom Desktop!")
        pass
