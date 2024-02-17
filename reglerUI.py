# -*- coding: utf-8 -*-
"""

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

import hwSetup as hs
import reglerSetup as rs
import messdatenGraphWidget as mgw
import messdatenTableWidget as mtw
import pruefWidget as pw
import consoleWidget as cw
import helpDialog as hd
import reglerConfigUI as rc
import reglerConfigNullUI as rcn
import wika_cpu5000_dvr as wcpu
import secSetup as ss
import reglerReadOutputLog as rrol


class ReglerUI(QMainWindow):
    
    TITEL = "SimGas Regler GUI - CORI"
    VERSION = "0.8"
    YEAR = "2024"
    
    _sig_close = pyqtSignal()
    
    UI_UPDATE_INTERVAL = 1000 #[ms]
    
    
    #################################################
    # Aktivierung von Funktionalitäten der Anwendung
    
    # Manuelle Messung Controls
    ENABLE_MANUAL_CONTROLS = True
    
    # Sicherheitsmagnetschalter # NICHT ANPASSEN, WENN MAN NICHT WEIß WAS MAN TUT!
    ENABLE_SEC_MAGNET_SWITCH = True
    
    # Entwickleransicht
    SHOW_EXTENDED_FUNCTIONS = False
    
    ###################################
    
    def __init__(self, sgr, sms):
        super().__init__()
    
        # lade HW-Setup
    
        self.sgr = sgr
        self.sms = sms
            
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
        configAct = QAction('&Reglerkonfiguration', self)
        configAct.setStatusTip('Reglerkonfiguration')
        configAct.triggered.connect(self.open_config)
        configMenu.addAction(configAct)
        configNullAct = QAction('&Nullpunktabgleich', self)
        configNullAct.setStatusTip('Nullpunktabgleich')
        configNullAct.triggered.connect(self.open_configNull)
        configMenu.addAction(configNullAct)
        
        #########################
        
        # Beim Beenden
        # Schließe HW-Setup
        self._sig_close.connect(self.sgr._close_hwSetup)
        
        # Verbinde Datenankunft mit Darstellung
        self.sgr.get_datamanager().sig_newDataReceived.connect(self.rmw.display_data)
        
        
        # Verbinde Sec Setup
        if(self.ENABLE_SEC_MAGNET_SWITCH):
            # Message bei Verbindungsversuch
            self.sms.sig_SEC_ConnectFinished.connect(self.print_ConnectTryMessage_SEC)
            # Verbindung herstellen
            self.sms._connect_sec()
            # Schließe Sicherheitsmagnetschalter bei Schließen der Anwendung
            self._sig_close.connect(self.sms._close_secSetup)
            
        
        # Verbinde Hardware
        self.sgr.sig_HWConnectFinished.connect(self.print_ConnectTryMessage)
        self.sgr._connect_Ports()
                  
        self.showMaximized()
                  
        # Starten der Messschleife          
        self.sgr._start_MessSchleife()
        
        # Starten der Sicherheits Messschleife
        if(self.ENABLE_SEC_MAGNET_SWITCH):
            self.sms._start_MessSchleife()
        
        
        # Starte UI Update Timer
        self.timer_updateUI = QTimer()
        self.timer_updateUI.setInterval(self.UI_UPDATE_INTERVAL)
        self.timer_updateUI.timeout.connect(self.updateUI)
        self.timer_updateUI.start()
        
        
                

    def closeEvent(self, event):
        
        #self.timer_updateUI.disconnect()
        
        
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
            
            print ("Regler UI closed")
        else:
            event.ignore()
            
            
            
    
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
    
    
    
    def open_help(self):
        help = hd.HelpDialog(self.TITEL, self.VERSION, self.YEAR)
        help.exec()
        
        
    def open_config(self):
        configUI = rc.ReglerConfigUI(self.sgr)
        configUI.exec()
        
    
    def open_configNull(self):
        configNullUI = rcn.ReglerConfigNullUI(self.sgr)
        configNullUI.exec()
        
        
    def updateUI(self):
        #print ("update UI")
        self.rmw.console.update_Console()
        self.rmw.reglerTable.update_ReglerListWidget()
        
        if(self.ENABLE_SEC_MAGNET_SWITCH):
            self.rmw.smsWidget.update_SecMagnetSwitch()
        
        if(self.ENABLE_MANUAL_CONTROLS):
            self.rmw.messStatWidget.update_MessungStatus()
        



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
        
        #~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Graph
        #~~~~~~~~~~~~~~~~~~~~~~~~~~~
        
        
        self.graphWidget = mgw.MessdatenGraphWidget(self, mw.sgr.get_datamanager())
        self.leftLayout.addWidget(self.graphWidget)
        self.graphWidget.set_floatingWindowEnabled(False)
        
        # CurveNames
        curveNames = dict()
        for p in mw.sgr._ports:
            curveNames[p] = mw.sgr._ports[p].get_name()   
        self.graphWidget.set_curveNames(curveNames)
        
        
        
        
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
        
        rightGroup.setFixedWidth(700)
        
        
        #===============================================
        # Prüfung und Messung Group
        #===============================================
        
        pruefGroup = QGroupBox("")
        pruefLayout = QVBoxLayout()
        pruefGroup.setLayout(pruefLayout)
        rightLayout.addWidget(pruefGroup)
        
        self.pruefWidget = pw.PruefWidget(self.__mainWindow.sgr, self.__mainWindow.sms, self)
        self.pruefWidget._sig_pdfSaved.connect(self.handle_pdfExport)   
        
        pruefLayout.addWidget(self.pruefWidget)


        #-------------------------------
        # Sicherheitsmagnetschalter
        #---------------------------------
        if(self.__mainWindow.ENABLE_SEC_MAGNET_SWITCH):
            self.smsWidget = SecMagnetSwitch(self.__mainWindow.sms, self.__mainWindow.sgr)
            rightLayout.addWidget(self.smsWidget)
        

        
        #---------------------------
        # Console
        #------------------------
        
        self.console = cw.ConsoleWidget(self.__mainWindow.sgr.protokoll)
        rightLayout.addWidget(self.console)
             
        
    
    
    #========================
    # RIGHT MOST GROUP
    #========================
    
    
        rightmostGroup = QGroupBox()
        rightmostLayout = QVBoxLayout()
        rightmostGroup.setLayout(rightmostLayout)
        self.mainLayout.addWidget(rightmostGroup) 


        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Manual Control Group
        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    
        self.manualControlGroup = QGroupBox("Manuelle Gesamtsteuerung")
        manualControlLayout = QHBoxLayout()
        self.manualControlGroup.setLayout(manualControlLayout)
        rightmostLayout.addWidget(self.manualControlGroup)
        
        #--------------------------
        # Regler Stellwert Group
        #---------------------------
        
        
        self.setGetReglerGroup = QGroupBox()
        setGetReglerLayout = QVBoxLayout()
        self.setGetReglerGroup.setLayout(setGetReglerLayout)
        manualControlLayout.addWidget(self.setGetReglerGroup)        
        
        
        # Set Stellwert
        
        self.setReglerGroup = QGroupBox()
        setReglerLayout = QHBoxLayout()
        self.setReglerGroup.setLayout(setReglerLayout)
        setGetReglerLayout.addWidget(self.setReglerGroup)
        
        self.sollSpin = QDoubleSpinBox()
        self.sollSpin.setMaximum(self.__mainWindow.sgr.get_max_gesSollwert())
        self.sollSpin.setSingleStep(0.01)
        self.sollSpin.setDecimals(2)
        #self.sollSpin.setValue(10)
        #self.sollSpin.setFont(QFont("Arial", 24))
        self.sollSpin.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        setReglerLayout.addWidget(self.sollSpin, 1)
        
        self.sollUnitLabel = QLabel("[g/min]")
        self.sollUnitLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        setReglerLayout.addWidget(self.sollUnitLabel)
 
        self.setSollButton = QPushButton("Setze Gesamt-Sollwert")
        self.setSollButton.clicked.connect(self.buttonSetSollwert_clicked)
        setReglerLayout.addWidget(self.setSollButton,1)
        
        
        # Get Stellwert
        
        getReglerGroup = QGroupBox()
        getReglerLayout = QHBoxLayout()
        getReglerGroup.setLayout(getReglerLayout)
        setGetReglerLayout.addWidget(getReglerGroup)
        
        self.aktReglerText = QLineEdit("{:4.2f}".format(mw.sgr.get_GesamtSollWert()))
        self.aktReglerText.setReadOnly(True)
        self.aktReglerText.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        getReglerLayout.addWidget(self.aktReglerText, 1)
        
        self.sollUnitLabelAkt = QLabel("[g/min]")
        self.sollUnitLabelAkt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        getReglerLayout.addWidget(self.sollUnitLabelAkt)
        
        self.getSollButton = QPushButton("Lese Gesamt-Sollwert")
        self.getSollButton.clicked.connect(self.buttonGetSollwert_clicked)
        getReglerLayout.addWidget(self.getSollButton, 1)
        
        # Stop Knopf
        
        self.closeAllButton = QPushButton("ALLE \n SCHLIESSEN")
        self.closeAllButton.clicked.connect(self.buttonCloseAll_clicked)
        manualControlLayout.addWidget(self.closeAllButton)
        self.closeAllButton.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
    
        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Messung 
        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        rightmostLayout.addStretch(1)
        if(self.__mainWindow.ENABLE_MANUAL_CONTROLS):
            self.messStatWidget = MessungStatus_Widget(self.__mainWindow.sgr)
            rightmostLayout.addWidget(self.messStatWidget)

        
       
        #----------------------------
        # Record Group
        #---------------------------
        
        self.recordGroup = QGroupBox("Aufzeichnen")
        recordLayout = QHBoxLayout()
        self.recordGroup.setLayout(recordLayout)
        
        self.buttonStartRecord = QPushButton("Aufzeichnung starten")
        self.buttonStartRecord.clicked.connect(self.buttonStartRecord_clicked)
        self.buttonStopRecordAndExport = QPushButton("Stop und Export zu Excel")
        self.buttonStopRecordAndExport.clicked.connect(self.buttonStopRecordAndExport_clicked)
        self.buttonStopRecordAndExport.setEnabled(False)
        
        recordLayout.addWidget(self.buttonStartRecord)
        recordLayout.addWidget(self.buttonStopRecordAndExport)
        
        rightmostLayout.addWidget(self.recordGroup)
        

            
            

            
    def set_extendedFunctionVisibility(self, extendedVis):
        
        self.recordGroup.setVisible(extendedVis)
        self.messStatWidget.setVisible(extendedVis)
        self.manualControlGroup.setVisible(extendedVis)
        self.smsWidget.set_extendedFunctionVisibility(extendedVis)
        self.reglerTable.set_extendedFunctionVisibility(extendedVis)
        self.dataTable.setVisible(extendedVis)    
    
        
        


    def buttonCloseAll_clicked(self):
        print ("Schließe alle Regler... ")
        if(self.__mainWindow.sgr.set_allClosed()):
            self.__mainWindow.sgr.protokoll.append(cw.ProtokollEintrag("Gesamt-Sollwert gesetzt: " + str(0) + " g/min", typ=cw.ProtokollEintrag.TYPE_SUCCESS))
            self.pruefWidget.set_ControlledModeEnabled(True)        
        else:
            self.__mainWindow.sgr.protokoll.append(cw.ProtokollEintrag("Schließen der Regler fehlgeschlagen!", typ=cw.ProtokollEintrag.TYPE_FAILURE))
           
        
        
    def buttonSetSollwert_clicked(self):
        soll = self.sollSpin.value()
        print ("Set ges.soll: " + str(soll))
        
        # Calc zentrierte Reglerauswahl
        reglerAuswahl = self.__mainWindow.sgr.calc_reglerAuswahl(soll)
        
        if(self.__mainWindow.sgr.set_GesamtSollwertAbsolut(soll, reglerAuswahl=reglerAuswahl)):
            self.__mainWindow.sgr.protokoll.append(cw.ProtokollEintrag("Gesamt-Sollwert gesetzt: " + str(soll) + " g/min", typ=cw.ProtokollEintrag.TYPE_SUCCESS))
            if(soll == 0):
                self.pruefWidget.set_ControlledModeEnabled(True)
            else:
                self.pruefWidget.set_ControlledModeEnabled(False)
                
        
        else:
            self.__mainWindow.sgr.protokoll.append(cw.ProtokollEintrag("Setzen des Gesamt-Sollwertes fehlgeschlagen! Stellwert gültig?", typ=cw.ProtokollEintrag.TYPE_FAILURE))
            
        
        
    def buttonGetSollwert_clicked(self):
        print ("current soll: " + str(self.sollSpin.value()))
        wert = self.__mainWindow.sgr.get_GesamtSollWert()
        if(wert != None):
            self.aktReglerText.setText("{:4.2f}".format(wert))
        else:
            print ("Lesen des Gesamt-Sollwertes fehlgeschlagen.")
            self.__mainWindow.sgr.protokoll.append(cw.ProtokollEintrag("Lesen des Gesamt-Sollwertes fehlgeschlagen!", typ=cw.ProtokollEintrag.TYPE_FAILURE))
 
        
        
        
    def handle_pdfExport(self, fName):
        if(fName != ""):
            self.__mainWindow.sgr.protokoll.append(cw.ProtokollEintrag("Protokoll gespeichert unter " + fName + "!", typ=cw.ProtokollEintrag.TYPE_SUCCESS))
        else:
            self.__mainWindow.sgr.protokoll.append(cw.ProtokollEintrag("Speichern des Graph fehlgeschlagen!", typ =  cw.ProtokollEintrag.TYPE_FAILURE))
            
        
        
        
        
################################################################################################
#
# Aufzeichnung der Messwerte
        
    def buttonStartRecord_clicked(self):
        """
        Startet die Aufzeichnung von Messdaten
        """

        self.__mainWindow.sgr.start_recordData()

        self.buttonStartRecord.setText("Aufzeichnung läuft...")
        
        # Setze Verfügbarkeit der Aufzeichnugnsbuttons
        self.buttonStartRecord.setEnabled(False)
        self.buttonStopRecordAndExport.setEnabled(True)
        
        self.__mainWindow.sgr.protokoll.append(cw.ProtokollEintrag("Aufzeichnung der Messwerte gestartet. Pfad: " + self.__mainWindow.sgr.dm.dataRecordPath, typ=cw.ProtokollEintrag.TYPE_SUCCESS))
       
    
    
    
    def buttonStopRecordAndExport_clicked(self):
        """
        Stoppt die Aufzeichnung von Messdaten
        """
        
        self.buttonStartRecord.setText("Aufzeichnung starten")
        self.buttonStartRecord.setEnabled(True)
        self.buttonStopRecordAndExport.setEnabled(False)
        
        self.__mainWindow.sgr.stop_recordData()

        self.__mainWindow.sgr.protokoll.append(cw.ProtokollEintrag("Aufzeichnung der Messwerte gespeichert unter: " + self.__mainWindow.sgr.dm.dataRecordPath , typ=cw.ProtokollEintrag.TYPE_SUCCESS))



    def display_data(self, data):
        #print (data)
        self.graphWidget.update_MessGraphWidget()
        self.pruefWidget.update_pruefWidget(data)
        
        
        
    def set_GraphRange(self, gesZeit):
        self.graphWidget.set_timeRangeOnFocus(gesZeit)
        
        
    def set_ManualModeEnabled(self, enabled):
        self.setReglerGroup.setEnabled(enabled)
        self.reglerTable.set_secLockOpen(enabled) 
        self.closeAllButton.setEnabled(enabled)
    
        if(self.__mainWindow.ENABLE_MANUAL_CONTROLS):
            self.messStatWidget.setEnabled(enabled)

        
    
    def closeMessdatenUI(self):
        self.graphWidget.set_openedExtern(False)
        self.leftLayout.insertWidget(0, self.graphWidget)


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
            self.sumReglerWidget.update_ReglerWidget(totalSet=self.__setup.get_GesamtSollWert(), totalIst=self.parent.rmw.pruefWidget.pruefung.get_pruefCurrentFlowSum(), hwStatus=self.__setup._hwConnectStatus)             
        else:
            self.sumReglerWidget.update_ReglerWidget(totalSet=self.__setup.get_GesamtSollWert(), totalIst=self.__setup.get_GesamtIstWert(), hwStatus=self.__setup._hwConnectStatus)     


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
    WIDTH_SETSPIN = 70
    WIDTH_SETPB = 50
    WIDTH_CLOSE = 50
    WIDTH_ENABLE = 50

    
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
        
        self.pbOpenReglerOutputLog = QLabel("")
        
        self.pbSetSoll = QPushButton("Set")
            
        # Inhalte anpassen

        name = "" if (not sum) else "\u03A3"
        bereich = "Bereich [g/min]" 
        istwert = "Istwert [g/min]"
        
        
        
        
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
                
                
            self.pStellwert = QLabel("Stellwert")
            self.pStellwert.setAlignment(Qt.AlignCenter)
            
            self.pStellwert.setFont(LisionStyle.LABEL_FONT_BOLD)  
            self.lIstwert.setFont(LisionStyle.LABEL_FONT_BOLD)  
            
            
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
        self.sSetSoll.setFixedWidth(self.WIDTH_SETSPIN)
        self.pbSetSoll.setFixedWidth(self.WIDTH_SETPB)
        self.pbClose.setFixedWidth(self.WIDTH_CLOSE)
        self.cbEnable.setFixedWidth(self.WIDTH_ENABLE)
            

        # Füge Widgets zur GUI hinzu
        mainLayout.addWidget(self.lActive)
        mainLayout.addWidget(self.lName)
        mainLayout.addWidget(self.lArbeitsbereich) 
        mainLayout.addWidget(self.pStellwert)
        mainLayout.addWidget(self.lIstwert)
        mainLayout.addWidget(self.sSetSoll)
        mainLayout.addWidget(self.pbSetSoll)
        mainLayout.addWidget(self.pbClose)
        mainLayout.addWidget(self.cbEnable)
        mainLayout.addWidget(self.pbOpenReglerOutputLog)
            
            
        self.lName.setText(name)
        self.lArbeitsbereich.setText(bereich)
        self.lIstwert.setText(istwert)
        
        
    def set_extendedFunctionVisibility(self, extendedVis):

            self.sSetSoll.setVisible(extendedVis)  
            self.pbSetSoll.setVisible(extendedVis)      
            self.pbClose.setVisible(extendedVis)
            self.cbEnable.setVisible(extendedVis)
            self.pbOpenReglerOutputLog.setVisible(extendedVis)
        
    
    def pbSetSollClicked(self):
        self.regler._set_Sollwert(self.sSetSoll.value())
        
    
    def pbCloseClicked(self):
        self.regler._set_Sollwert(0)
    
    
    def pbOpenReglerOutputLogClicked(self):
        logWidget = rrol.ReglerReadOutputLog(self.parent, self.regler)
    
    
    def cbEnable_stateChanged(self):
        # Wenn Regler deaktivert wird: Auf 0 setzen.
        if(not self.cbEnable.isChecked()):
            self.regler._close()
        
        self.regler.set_enabled(self.cbEnable.isChecked())
    
        
    def update_ReglerWidget(self, totalSet=0, totalIst=0, hwStatus=-1):
        
        if(self.regler != None):
            
            # Aktiviert
            self.lArbeitsbereich.setEnabled(self.cbEnable.isChecked())
            self.pStellwert.setEnabled(self.cbEnable.isChecked())
            self.lIstwert.setEnabled(self.cbEnable.isChecked())
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
                self.sSetSoll.setEnabled(False)
                self.pbSetSoll.setEnabled(False)
                self.pbClose.setEnabled(False)
                self.cbEnable.setEnabled(False)
                
            else:
                self.lActive.setPixmap(self.bildActive)
                self.lIstwert.setText("{:4.2f}".format(self.regler.get_ist()))

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
            self.lIstwert.setText("{:4.2f}".format(totalIst))
            
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




class MessungStatus_Widget(QGroupBox):
    
    def __init__(self, sgr):
        super().__init__("Messung")
        
        self._sgr = sgr
        
        messungLayout = QVBoxLayout()
        self.setLayout(messungLayout)
        
        # Status
        messStatusGroup = QGroupBox()
        messStatusLayout = QHBoxLayout()
        messStatusGroup.setLayout(messStatusLayout)
        messungLayout.addWidget(messStatusGroup, 1)
        
        self.bildMessungActive = QPixmap("symbols/light_green.png")
        self.bildMessungInactive = QPixmap("symbols/light_red.png")
          
        self.lMessungActive = QLabel("")
        self.lMessungActive.setFixedWidth(25)
        messStatusLayout.addWidget(self.lMessungActive, 1)
        
        self.lMessungActiveLabel = QLabel("Paused")
        messStatusLayout.addWidget(self.lMessungActiveLabel, 1)

        #=====================
        # CONTROLS
        
        messControlGroup = QGroupBox()
        messControlLayout = QHBoxLayout()
        messControlGroup.setLayout(messControlLayout)
        messungLayout.addWidget(messControlGroup)
        
        # Start
        self.pbStartMessung = QPushButton("Start")
        messControlLayout.addWidget(self.pbStartMessung, 1)
        self.pbStartMessung.clicked.connect(self.pbStartMessung_clicked)
        
        # Pause
        self.pbPauseMessung = QPushButton("Pause")
        messControlLayout.addWidget(self.pbPauseMessung, 1)
        self.pbPauseMessung.clicked.connect(self.pbPauseMessung_clicked)
        
        # Reset Messungen
        self.pbResetMessung = QPushButton("Reset Messungen")
        messungLayout.addWidget(self.pbResetMessung, 1)
        self.pbResetMessung.clicked.connect(self.pbResetMessung_clicked)
        
        messungLayout.addSpacing(10)
        
        
    def update_MessungStatus(self):
        if(self._sgr != None):
            if(self._sgr.is_paused()):
                self.lMessungActive.setPixmap(self.bildMessungInactive)
                self.lMessungActiveLabel.setText("PAUSED")
                self.pbPauseMessung.setEnabled(False)
                self.pbStartMessung.setEnabled(True)
            else:
                self.lMessungActive.setPixmap(self.bildMessungActive)
                self.lMessungActiveLabel.setText("RUNNING")
                self.pbPauseMessung.setEnabled(True)
                self.pbStartMessung.setEnabled(False)
                
                
    def pbStartMessung_clicked(self):
        if(self._sgr != None):
            self._sgr.set_paused(False)            
            
                            
    def pbPauseMessung_clicked(self):
        if(self._sgr != None):
            self._sgr.set_paused(True) 
        
            
    def pbResetMessung_clicked(self):
        if(self._sgr != None):
            self._sgr.reset()         
        
      
class SecMagnetSwitch(QGroupBox):
    
    def __init__(self, sms, sgr):
        super().__init__("Sicherheitsmagnetschalter")
        mainLayout = QVBoxLayout()
        self.setLayout(mainLayout)
        
        self.sms = sms
        self.sgr = sgr
        
        ################################
        # Connection
        ##########################
        
        self.connectionGroup = QGroupBox ("")
        connectLayout = QHBoxLayout()
        self.connectionGroup.setLayout(connectLayout)
        mainLayout.addWidget(self.connectionGroup)
        
        # Connect Status
        self.bildActive = QPixmap("symbols/light_green.png")
        self.bildWarning = QPixmap("symbols/light_yellow.png")
        self.bildInactive = QPixmap("symbols/light_red.png")
          
        self.lActive = QLabel("")
        #self.lActive.setFixedWidth(25)
        connectLayout.addWidget(self.lActive)
        
        connectLayout.addSpacing(1)
        
        # Open Status
        self.lOpen = QLabel("----")
        self.lOpen.setFixedWidth(60)
        #connectLayout.addWidget(self.lOpen)
        
        # Port
        self.lPort = QLabel("COM:")
        self.lPort.setFixedWidth(60)
        #connectLayout.addWidget(self.lPort)
        self.tPortNum = QLineEdit("11")
        #self.tPortNum.setFixedWidth(60)
        #connectLayout.addWidget(self.tPortNum)
        
        # Connect
        self.pbConnect = QPushButton("Connect")
        #self.pbConnect.setFixedWidth(60)
        self.pbConnect.clicked.connect(self.buttonConnect_clicked)
        #connectLayout.addWidget(self.pbConnect)
        
        # Open
        self.pbOpen = QPushButton("Hauptventil öffnen")
        #self.pbOpen.setFixedWidth(160)
        self.pbOpen.clicked.connect(self.buttonOpen_clicked)
        connectLayout.addWidget(self.pbOpen)
        
        # Close
        self.pbClose = QPushButton("Hauptventil schließen")
        #self.pbClose.setFixedWidth(160)
        self.pbClose.clicked.connect(self.buttonClose_clicked)
        connectLayout.addWidget(self.pbClose)
        
        #############################
        # Data
        #############################
        
        dataGroup = QGroupBox("")
        dataLayout = QVBoxLayout()
        dataGroup.setLayout(dataLayout)
        mainLayout.addWidget(dataGroup)
        
        self.gasGroup = QGroupBox("Gas")
        dataLeftLayout = QHBoxLayout()
        self.gasGroup.setLayout(dataLeftLayout)
        dataLayout.addWidget(self.gasGroup)
        
        # FP
        fpGroup = QGroupBox()
        fpLayout = QHBoxLayout()
        fpGroup.setLayout(fpLayout)
        dataLeftLayout.addWidget(fpGroup)
        self.iFP = QLabel("Gas-Druck")
        self.iFP.setFixedWidth(100)
        fpLayout.addWidget(self.iFP)
        self.tFP = QLineEdit("")
        self.tFP.setFixedWidth(60)
        self.tFP.setReadOnly(True)
        fpLayout.addWidget(self.tFP)
        self.lFP = QLabel("[bar]")
        self.lFP.setFixedWidth(60)
        fpLayout.addWidget(self.lFP)
        
        # TP
        tpGroup = QGroupBox()
        tpLayout = QHBoxLayout()
        tpGroup.setLayout(tpLayout)
        dataLeftLayout.addWidget(tpGroup)
        self.iTP = QLabel("Gas-Temp.")
        self.iTP.setFixedWidth(100)
        tpLayout.addWidget(self.iTP)
        self.tTP = QLineEdit("")
        self.tTP.setFixedWidth(60)
        self.tTP.setReadOnly(True)
        tpLayout.addWidget(self.tTP)
        self.lTP = QLabel("[°C]")
        self.lTP.setFixedWidth(60)
        tpLayout.addWidget(self.lTP)
        
        self.raumGroup = QGroupBox("Raum")
        dataRightLayout = QHBoxLayout()
        self.raumGroup.setLayout(dataRightLayout)
        dataLayout.addWidget(self.raumGroup)
        
        # TE
        teGroup = QGroupBox()
        teLayout = QHBoxLayout()
        teGroup.setLayout(teLayout)
        dataRightLayout.addWidget(teGroup)
        self.iTE = QLabel("Raum-Temp.")
        self.iTE.setFixedWidth(100)
        teLayout.addWidget(self.iTE)
        self.tTE = QLineEdit("")
        self.tTE.setFixedWidth(60)
        self.tTE.setReadOnly(True)
        teLayout.addWidget(self.tTE)
        self.lTE = QLabel("[°C]")
        self.lTE.setFixedWidth(60)
        teLayout.addWidget(self.lTE)
        
        # HU
        huGroup = QGroupBox()
        huLayout = QHBoxLayout()
        huGroup.setLayout(huLayout)
        dataRightLayout.addWidget(huGroup) 
        self.iHU = QLabel("Raum-Hum.")
        self.iHU.setFixedWidth(100)
        huLayout.addWidget(self.iHU)
        self.tHU = QLineEdit("")
        self.tHU.setFixedWidth(60)
        self.tHU.setReadOnly(True)
        huLayout.addWidget(self.tHU)
        self.lHU = QLabel("[%]")
        self.lHU.setFixedWidth(60)
        huLayout.addWidget(self.lHU)
        
   
        #self.pbReadFP = QPushButton("read")
        #self.pbReadFP.setFixedWidth(60)
        #self.pbReadFP.clicked.connect(self.buttonRead_clicked)
        #mainLayout.addWidget(self.pbReadFP)
        
        
    def set_extendedFunctionVisibility(self, extendedVis):
        self.raumGroup.setVisible(extendedVis)

        
    
    def buttonConnect_clicked(self):
        print ("Try to connect: SecMagSwitch")
        self.sms._connect_sec(port)
        
    def buttonOpen_clicked(self):
        self.sms.set_sms_open(True)
        
    def buttonClose_clicked(self):
        self.sms.set_sms_open(False)
    
    
    
    def buttonRead_clicked(self):
        #msg = self.sms._read("TE?")
        #val = float(msg)
        #self.tFP.setText(str(val))
        pass 
    
    
    def update_SecMagnetSwitch(self):
        if(self.sms != None):
            
            # Connection
            if(self.sms._secConnectStatus == self.sms.SEC_CONNECT_STATUS_NONE):
                # NOT CONNECTED
                self.lActive.setPixmap(self.bildInactive)
                self.lOpen.setEnabled(False)
                self.pbConnect.setEnabled(True)
                self.lOpen.setText("")
            else:
                # CONNECTED
                self.lActive.setPixmap(self.bildActive)
                self.lOpen.setEnabled(True)
                self.pbConnect.setEnabled(False)
                
                # Open STatus
                if(self.sms._sms_Open == False):
                    self.lOpen.setText("CLOSED")
                else:
                    self.lOpen.setText("OPEN")     
                    
                # Messwerte
                
                fp = self.sms.data[self.sms.CMD_TABLE[1]]
                tp = "---"
                te = self.sms.data[self.sms.CMD_TABLE[2]]
                hu = self.sms.data[self.sms.CMD_TABLE[3]]
                
                
                extFPdata = dict()
                
                if(type(fp) != str):
                    
                    # Berechnung GasTemp:
                    tp = 987.0 / ( 6.2886 - math.log10(fp*100) ) - 273.15
                    
                    extFPdata["FP"] = fp
                    
                    # Aktuelle Gas-Eigenschaften an Regler zur Kalibrierung weitergeben
                    self.sgr.set_current_GasEigenschaften(fp, tp)
                    
                    # Gas Druck und Gas Temperatur in String umwandeln   
                    fp = "{:4.1f}".format(fp)
                    tp = "{:4.1f}".format(tp)
                    
                    
                self.sgr.set_externData(extFPdata)
            
                if(type(te) != str):
                    # Raum-Temperatur in String umwandeln        
                    te = "{:4.1f}".format(te)
                    
                if(type(hu) != str):
                    # Raum-Feuchtigkeit in String umwandeln
                    hu = "{:4.1f}".format(hu)

                self.tFP.setText(fp)
                self.tTE.setText(te)
                self.tHU.setText(hu)
                self.tTP.setText(tp)

                #self.tFP.setText(str(self.sms.data[self.sms.CMD_TABLE[1]]))
                #self.tTE.setText(str(self.sms.data[self.sms.CMD_TABLE[2]]))
                #self.tHU.setText(str(self.sms.data[self.sms.CMD_TABLE[3]]))
                
                
        
    
          
          
            

if __name__ == '__main__':

    app = QApplication(sys.argv)


    # ModBus Controller
    mbc = # TODO Init ModBusCtrl
    
    # SecSetup (Magnetschalter)
    sms = ss.SecSetup(mbc)
    
    # Regel Stellglieder
    sgr = rs.SimGasRegler(mbc)
    
    # TODO: Umgebungssensorik ausgliedern
    
    

    # Öffne Anzeige
    main = ReglerUI(sgr, sms)

    ec = app.exec_()
    
    if(sgr.terminated):
        print ("Programm regulär geschlossen.")
    else:   
        sgr._close_hwSetup()
        print ("Programm abgestürzt!")
        
    sys.exit(ec)