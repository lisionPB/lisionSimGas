import os

from PyQt5 import QtCore, QtGui, QtWidgets, QtPrintSupport
from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QDoubleSpinBox, QLabel, QWidget
from PyQt5.QtCore import QTimer, pyqtSignal


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

import exportConfig

class PruefWidget(QGroupBox):
    
    DEFAULT_ZEIT_MIN = 1
    DEFAULT_ZEIT_AUFZEICHNUNG_MIN = 1
    DEFAULT_MASSE_G = 8
    DEFAULT_RAMPENZEIT_S = 5
    
    FILE_CONFIG_DEFAULTS = "config_pruefung.json"
    
    _sig_pdfSaved = pyqtSignal(str) # "" wenn fehler, sonst Filename
    
    def __init__(self, rs, sms, mw):
        """
        Arguments:
            rs (ReglerSetup): zugrundliegendes reglerSetup 
        """
        
        super().__init__("Prüfung")
        
        self.sgr = rs
        self.sms = sms
        self.mw = mw
        
        self.conf = self._load_pruefConfig()
        
        self.mainLayout = QVBoxLayout()
        self.setLayout(self.mainLayout)
        
        self.init_UI()
        
        self.pruefung = None
        
        # Prüfzeit Timer
        self.timer_startPruefung = QTimer()
        self.timer_startPruefung.setSingleShot(True)
        self.timer_startPruefung.timeout.connect(self.start_pruefung)
        
        self.timer_finishPruefung = QTimer()
        self.timer_finishPruefung.setSingleShot(True)
        self.timer_finishPruefung.timeout.connect(self.finishPruefung)
        
        self.timer_endPruefung = QTimer()
        self.timer_endPruefung.setSingleShot(True)
        self.timer_endPruefung.timeout.connect(self.endPruefung)

        # Aufzeichnungs Timer
        self.timer_endAufzeichnung = QTimer()
        self.timer_endAufzeichnung.setSingleShot(True)
        self.timer_endAufzeichnung.timeout.connect(self.stop_aufzeichnung)
    
    
    def _load_pruefConfig(self):
        """
        Liest Default Pruef-Konfiguration aus json-File
        """
        # TODO: Ausnahmebehandlung, wenn Config File nicht gefunden wurde oder File ungültiges Format hat!
        
        f = open(self.FILE_CONFIG_DEFAULTS)
        conf = json.load(f)
        
        self.DEFAULT_MASSE_G = conf["DEFAULT_MASSE_G"]
        self.DEFAULT_RAMPENZEIT_S = conf["DEFAULT_RAMPENZEIT_S"]
        self.DEFAULT_ZEIT_MIN = conf["DEFAULT_ZEIT_MIN"]        
               
        self.mw.graphWidget.graphWidget.setCurveVisibility(conf["visibility"])
        
        
        f.close()
        
        return conf


    def save_pruefConfig(self):  
        conf = {}
        conf["DEFAULT_MASSE_G"] =  self.sMengeSpinner.value()
        conf["DEFAULT_RAMPENZEIT_S"] = self.sStartzeitSpinner.value()
        conf["DEFAULT_ZEIT_MIN"] = self.sZeitSpinner.value()
        
        
        visibility = {}
        for c in self.mw.graphWidget.graphWidget.curves:
            visibility[c] = self.mw.graphWidget.graphWidget.curves[c].isVisible()
        conf["visibility"] = visibility
                
        
        with open(self.FILE_CONFIG_DEFAULTS, "w") as outfile:
            json.dump(conf, outfile, indent=4)
        

        print ("Default-Einstellungen gespeichert.")
        
        
        
    
    
    def init_UI(self):
        
    ####################################################
    # KONFIGURATION
    ###############
        
        self.groupConfig = QGroupBox("Konfiguration")
        self.layoutConfig = QVBoxLayout()
        self.groupConfig.setLayout(self.layoutConfig)
        self.mainLayout.addWidget(self.groupConfig)
        
        # self.layoutConfig.setContentsMargins(0,0,0,0)
        
        # Prüfungzeit
        groupZeit = QWidget()
        layoutZeit = QHBoxLayout()
        groupZeit.setLayout(layoutZeit)
        self.layoutConfig.addWidget(groupZeit)
        
        lZeitLabel = QLabel("Einströmzeit [min]")
        layoutZeit.addWidget(lZeitLabel)
        lZeitLabel.setFixedWidth(200)
        
        self.sZeitSpinner = QDoubleSpinBox()
        layoutZeit.addWidget(self.sZeitSpinner)
        self.sZeitSpinner.setDecimals(0)
        self.sZeitSpinner.setSingleStep(1)
        self.sZeitSpinner.setValue(self.DEFAULT_ZEIT_MIN)
        self.sZeitSpinner.setMinimum(1)
        self.sZeitSpinner.setMaximum(10000)
        self.sZeitSpinner.setFixedWidth(150)
        self.sZeitSpinner.valueChanged.connect(self.calc_initFluss)
        
        layoutZeit.addStretch(1)
        layoutZeit.setContentsMargins(0,0,0,0)


        # Aufzeichnungszeit
        groupAufzeichnungsZeit = QWidget()
        layoutAufzeichnungsZeit = QHBoxLayout()
        groupAufzeichnungsZeit.setLayout(layoutAufzeichnungsZeit)
        self.layoutConfig.addWidget(groupAufzeichnungsZeit)
        
        lAufzeichnungsZeitLabel = QLabel("Aufzeichnungszeit [min]")
        layoutAufzeichnungsZeit.addWidget(lAufzeichnungsZeitLabel)
        lAufzeichnungsZeitLabel.setFixedWidth(200)
        
        self.sAufzeichnungsZeitSpinner = QDoubleSpinBox()
        layoutAufzeichnungsZeit.addWidget(self.sAufzeichnungsZeitSpinner)
        self.sAufzeichnungsZeitSpinner.setDecimals(0)
        self.sAufzeichnungsZeitSpinner.setSingleStep(1)
        self.sAufzeichnungsZeitSpinner.setValue(self.DEFAULT_ZEIT_AUFZEICHNUNG_MIN)
        self.sAufzeichnungsZeitSpinner.setMinimum(1)
        self.sAufzeichnungsZeitSpinner.setMaximum(10000)
        self.sAufzeichnungsZeitSpinner.setFixedWidth(150)
        self.sAufzeichnungsZeitSpinner.valueChanged.connect(self.calc_initFluss)
        
        layoutAufzeichnungsZeit.addStretch(1)
        layoutAufzeichnungsZeit.setContentsMargins(0,0,0,0)

        
        # GesamtGasMenge
        groupMenge = QWidget()
        layoutMenge = QHBoxLayout()
        groupMenge.setLayout(layoutMenge)
        self.layoutConfig.addWidget(groupMenge)
        
        lMengeLabel = QLabel("Menge [g]")
        layoutMenge.addWidget(lMengeLabel)
        lMengeLabel.setFixedWidth(200)
        
        self.sMengeSpinner = QDoubleSpinBox()
        layoutMenge.addWidget(self.sMengeSpinner)
        self.sMengeSpinner.setDecimals(1)
        self.sMengeSpinner.setSingleStep(0.1)
        self.sMengeSpinner.setMinimum(0.4)
        self.sMengeSpinner.setMaximum(10000) 
        self.sMengeSpinner.setValue(self.DEFAULT_MASSE_G)
        self.sMengeSpinner.setFixedWidth(150)
        self.sMengeSpinner.valueChanged.connect(self.calc_initFluss)
        
        groupMenge.setContentsMargins(0,0,0,0)
        
        layoutMenge.addStretch(1)
        layoutMenge.setContentsMargins(0,0,0,0)
        
        
        # Zeit für Rampe
        groupStartzeit = QWidget()
        layoutStartzeit = QHBoxLayout()
        groupStartzeit.setLayout(layoutStartzeit)
        self.layoutConfig.addWidget(groupStartzeit)
        
        lStartzeitLabel = QLabel("Rampenzeit [s]")
        layoutStartzeit.addWidget(lStartzeitLabel)
        lStartzeitLabel.setFixedWidth(200)
        
        self.sStartzeitSpinner = QDoubleSpinBox()
        layoutStartzeit.addWidget(self.sStartzeitSpinner)
        self.sStartzeitSpinner.setDecimals(0)
        self.sStartzeitSpinner.setValue(self.DEFAULT_RAMPENZEIT_S)
        self.sStartzeitSpinner.setMinimum(0)
        self.sStartzeitSpinner.setMaximum(300)
        self.sStartzeitSpinner.setFixedWidth(150)
        
        layoutStartzeit.addStretch(1)
        layoutStartzeit.setContentsMargins(0,0,0,0)
                
        
        # Ermittelter Intialfluss
        groupInitFluss = QWidget()
        layoutInitFluss = QHBoxLayout()
        groupInitFluss.setLayout(layoutInitFluss)
        self.layoutConfig.addWidget(groupInitFluss)
        
        lInitFlussLabel = QLabel("Reglerdurchschnittswert [g/min]")
        layoutInitFluss.addWidget(lInitFlussLabel)
        lInitFlussLabel.setFixedWidth(200)
        
        self.lInitFlussLabel = QLabel()
        layoutInitFluss.addWidget(self.lInitFlussLabel)
        self.lInitFlussLabel.setFixedWidth(350)

        layoutInitFluss.addStretch(1)
        layoutInitFluss.setContentsMargins(0,0,0,0)
        
           

    ######################################################
    # Reglerparameter
    ###########

        self.groupParametrierung = ParametrierungUI(self.sgr)
        self.mainLayout.addWidget(self.groupParametrierung)
        
    ####################################################
    # DURCHFÜHRUNG
    ###############
        
        self.groupRun = QGroupBox("Durchführung")
        self.layoutRun = QVBoxLayout()
        self.groupRun.setLayout(self.layoutRun)
        self.mainLayout.addWidget(self.groupRun)        
        
        # Prüfzeit
        groupRunZeit = QGroupBox("")
        layoutRunZeit = QHBoxLayout()
        groupRunZeit.setLayout(layoutRunZeit)
        self.layoutRun.addWidget(groupRunZeit)
        
        lRunZeitLabel = QLabel("Prüflaufzeit")
        layoutRunZeit.addWidget(lRunZeitLabel)
        lRunZeitLabel.setFixedWidth(200)
        
        self.lRunZeitValue = QLabel()
        layoutRunZeit.addWidget(self.lRunZeitValue)
        self.lRunZeitValue.setText("--:--:--")
        self.lRunZeitValue.setFixedWidth(350)
        
        layoutRunZeit.addStretch(1)
        
        # Ermittelter Gesamtfluss
        groupRunMenge = QGroupBox("")
        layoutRunMenge = QHBoxLayout()
        groupRunMenge.setLayout(layoutRunMenge)
        self.layoutRun.addWidget(groupRunMenge)
        
        lRunMengeLabel = QLabel("Gesamtmenge [g]")
        layoutRunMenge.addWidget(lRunMengeLabel)
        lRunMengeLabel.setFixedWidth(200)
        
        self.lRunMengeValue = QLabel()
        layoutRunMenge.addWidget(self.lRunMengeValue)
        self.lRunMengeValue.setText("----.--")        
        self.lRunMengeValue.setFixedWidth(350)   
        
        layoutRunMenge.addStretch(1)
        
        #####################################################
        # CONTROLS
        ############
        
        # Controls
        #   START/STOP
        #       PrüfungButtons
        #           Start
        #           Stop
        #       AufzeichnungButtons
        #           Start
        #           Stop
        # Export

        # Control

        groupPruefControls = QGroupBox()
        layoutPruefControls = QHBoxLayout()
        layoutPruefControls.setContentsMargins(0,0,0,0)
        groupPruefControls.setLayout(layoutPruefControls)
        self.mainLayout.addWidget(groupPruefControls)
        
        # START / STOP

        groupStartStopControls = QGroupBox()
        layoutStartStopControls = QVBoxLayout()
        layoutStartStopControls.setContentsMargins(0,0,0,0)
        groupStartStopControls.setLayout(layoutStartStopControls)
        layoutPruefControls.addWidget(groupStartStopControls)

        # Prüfung

        groupPruefButtons = QGroupBox()
        layoutPruefButtons = QHBoxLayout()
        layoutPruefButtons.setContentsMargins(0,0,0,0)
        groupPruefButtons.setLayout(layoutPruefButtons)
        layoutStartStopControls.addWidget(groupPruefButtons)

        # Start Prüfung
        
        self.pbStartPruefung = QPushButton("Einströmung starten")
        layoutPruefButtons.addWidget(self.pbStartPruefung)
        self.pbStartPruefung.clicked.connect(self.start_pruefungClicked)
        self.pbStartPruefung.setEnabled(False)
        
        # Prüfung Abbrechen
        
        self.pbCancelPruefung = QPushButton("Einströmung abbrechen")
        layoutPruefButtons.addWidget(self.pbCancelPruefung)
        self.pbCancelPruefung.clicked.connect(self.cancel_pruefungClicked)
        self.pbCancelPruefung.setVisible(False)

        # Aufzeichnung

        groupAufzeichnungButtons = QGroupBox()
        layoutAufzeichnungButtons = QHBoxLayout()
        layoutAufzeichnungButtons.setContentsMargins(0,0,0,0)
        groupAufzeichnungButtons.setLayout(layoutAufzeichnungButtons)
        layoutStartStopControls.addWidget(groupAufzeichnungButtons)

        # Start Aufzeichnung
        
        self.pbStartAufzeichnung = QPushButton("Aufzeichnung starten")
        layoutAufzeichnungButtons.addWidget(self.pbStartAufzeichnung)
        self.pbStartAufzeichnung.clicked.connect(self.start_aufzeichnungClicked)
        self.pbStartAufzeichnung.setEnabled(True)
        
        # Aufzeichnung Abbrechen
        
        self.pbCancelAufzeichnung = QPushButton("Aufzeichnung beenden und speichern")
        layoutAufzeichnungButtons.addWidget(self.pbCancelAufzeichnung)
        self.pbCancelAufzeichnung.clicked.connect(self.stop_aufzeichnungClicked)
        self.pbCancelAufzeichnung.setVisible(False)
        
        # Save PDF
        self.buttonSavePDF = QPushButton("PDF exportieren...")
        self.buttonSavePDF.clicked.connect(self.buttonSavePDF_clicked)
        self.buttonSavePDF.setFixedWidth(150)
        self.buttonSavePDF.setEnabled(False)
        layoutPruefControls.addWidget(self.buttonSavePDF)
        
        ###############
        # Berechne Initialwerte
        
        self.calc_initFluss()
        
        
    
    def buttonSavePDF_clicked(self):
        self.exportPruefPDF("protokolle/")

    
    def calc_initFluss(self):
        
        # Bestimme regelmäßigen Fluss, um Menge über Zeit zu erreichen
        fluss = self.sMengeSpinner.value() / self.sZeitSpinner.value()
        
        # Bestimme ReglerAuswahl
        reglerAuswahl = self.sgr.calc_reglerAuswahl(fluss)
        
        ####
        # Bestimme thoretische Flüsse pro Regler
        abSum = 0
        for r in reglerAuswahl:
            abSum += reglerAuswahl[r]
        
        # Anteil Stellwert an Gesamtarbeitsbereich
        anteil = 0
        if(abSum > 0):
            anteil = fluss / abSum
            
        # Theoretische Flüsse je Regelstellglied
        theoFlows = {}
        stringFlows = ""
        for r in reglerAuswahl:
            theoFlows[r] = reglerAuswahl[r] * anteil
            stringFlows += self.sgr._ports[r].get_name() + ": " + '{0:.3f}'.format(theoFlows[r]) + " "
            
        self.lInitFlussLabel.setText('{0:.2f}'.format(fluss) + "    (" + stringFlows + ")")

        # Berechne neu Parameter und zeige sie an
        params = parametrierung.calc_parameter(theoretischeFluesse=theoFlows)
        # print (params)
        self.groupParametrierung.update_Params(params)

    

    ##################
    # AUFZEICHNUNG


    def start_aufzeichnungClicked(self):
        self.pruefung = Pruefung(self.sgr, self.sms, self.sZeitSpinner.value(), self.sMengeSpinner.value(), self.sStartzeitSpinner.value())
        self.init_aufzeichnung() 


    
    def init_aufzeichnung(self):
        
        self.pbStartAufzeichnung.setVisible(False)
        self.pbStartAufzeichnung.setEnabled(False)
        self.pbCancelAufzeichnung.setVisible(True)     
        self.buttonSavePDF.setEnabled(False)

        self.lock_configButtons()

        # Datamanager zurücksetzen
        self.sgr.reset()

        # Aufzeichnung starten
        self.pruefung.start_aufzeichnung()

        # Timer zum Beenden der Prüfung
        self.timer_endAufzeichnung.setInterval(int(self.sAufzeichnungsZeitSpinner.value() * 60000))
        self.timer_endAufzeichnung.start()

        # Graph Update aktivieren
        self.mw.graphWidget.set_update(True)
        self.mw.graphWidget_gasSensorik.set_update(True)



    def stop_aufzeichnungClicked(self):
        self.stop_aufzeichnung()


    def stop_aufzeichnung(self):
    
        self.pruefung.stop_aufzeichnung()
        self.timer_endAufzeichnung.stop()

        # Graph Aktualisierung aussetzen
        self.mw.graphWidget.stop_update()
        self.mw.graphWidget_gasSensorik.stop_update()

        # PDF exportieren
        self.reportPruefung()

        self.pbStartAufzeichnung.setVisible(True)
        self.pbCancelAufzeichnung.setVisible(False)
        self.buttonSavePDF.setEnabled(True)

        if(not self.pruefung.is_busy()):
            self.pbStartAufzeichnung.setEnabled(True)

            self.reset_configButtons()

            self.pbStartPruefung.setVisible(True)
            self.pbCancelPruefung.setVisible(False)
            self.pbCancelPruefung.setEnabled(True)
            




    #################
    # PRÜFUNG

        
    def start_pruefungClicked(self):
        
        self.pruefung = Pruefung(self.sgr, self.sms, self.sZeitSpinner.value(), self.sMengeSpinner.value(), self.sStartzeitSpinner.value())

        # Check: Übertragung der PIDs        
        if(not self.groupParametrierung.send_Params()):
            self.sgr.protokoll.append(cw.ProtokollEintrag("Einströmung konnte nicht gestartet werden! Regler-PID-Werte konnten nicht übertragen werden! Kommunikationsverbindung zu Regelstellgliedern prüfen!", typ=cw.ProtokollEintrag.TYPE_FAILURE))
            return False
        
        # Check: Stellglieder auf 0?
        if(not self.sgr.safetyCheck_allConnectedAndZero()):
            self.sgr.protokoll.append(cw.ProtokollEintrag("Einströmung konnte nicht gestartet werden! Vor Start müssen alle Regelstellglieder in der 0-Position sein!", typ=cw.ProtokollEintrag.TYPE_FAILURE))
            return False
        
        # Go
        self.init_pruefung()
        self.init_aufzeichnung() 

        # Buttons resetten, wenn Prüfung fertig.
        self.pruefung._sig_pruefCanceled.connect(self.reset_configButtons)

        # Flaschenzuschaltungen zurücksetzen wenn canceled or ended
        self.pruefung._sig_pruefCanceled.connect(self.mw.smsWidget.clear_allFlaschenZuschaltungen)
        self.pruefung._sig_pruefEnded.connect(self.mw.smsWidget.clear_allFlaschenZuschaltungen)
        
            

    def init_pruefung(self):

        if(self.pruefung.prepare_pruefung()):

            self.pbStartPruefung.setVisible(False)
            self.pbCancelPruefung.setVisible(True)

            self.mw.dataTable.clear_table()
            
            print ("Einströmung wird gestartet ...")
            # Starten der Messschleife          
            self.sgr._start_MessSchleife()
            
            self.timer_startPruefung.setInterval(self.pruefung.DEFAULT_ZEIT_START)
            self.timer_startPruefung.start()
            self.sgr.protokoll.append(cw.ProtokollEintrag("Einströmung wird gestartet... ", typ=cw.ProtokollEintrag.TYPE_STANDARD))

            # öffne Magnetventile
            self.sms.write_sms_zuschaltungen()

            return True

        return False
        

    def start_pruefung(self):
        """
        Nach Ablauf der Vorlaufzeit getriggert durch Timer
        """

        if(self.pruefung.start_pruefung()):
            
            # Timer zum Beenden der Prüfung
            self.timer_finishPruefung.setInterval(int(self.sZeitSpinner.value() * 60000))
            self.timer_finishPruefung.start()
            print ("Einströmung läuft")
            self.sgr.protokoll.append(cw.ProtokollEintrag("Einströmung läuft", typ=cw.ProtokollEintrag.TYPE_SUCCESS))
            
            # print ("Set Graph Range: " + str(self.pruefung.get_gesZeit() * 60))
            # self.mw.set_GraphRange(self.pruefung.get_gesZeit() * 60 + 5)

        else:
            self.sgr.protokoll.append(cw.ProtokollEintrag("Starten der Einströmung fehlgeschlagen!", typ=cw.ProtokollEintrag.TYPE_FAILURE))
            self.cancel_pruefung()
            
        
            
    def cancel_pruefungClicked(self):     
        self.cancel_pruefung()

    
    def cancel_pruefung(self):
        
        if(self.pruefung != None):
            # Prüfung läuft bereits -> Prüfung abbrechen
            if(self.pruefung.is_busy()):
                print ("Einströmung abgebrochen!")
                self.pruefung.cancel_pruefung()
                # Halte Finish Timer an.
                # self.timer_finishPruefung.disconnect()
                self.timer_finishPruefung.stop()
                # self.timer_endPruefung.stop()     # Oder lieber Abbrechen unterbinden?
                self.timer_startPruefung.stop()
                
                self.sgr.protokoll.append(cw.ProtokollEintrag("Einströmung abgebrochen!", typ=cw.ProtokollEintrag.TYPE_STANDARD))
            
                self.pbCancelPruefung.setEnabled(False)

                if(not self.pruefung.is_recording()):
                    self.pbStartAufzeichnung.setEnabled(True)

                    self.reset_configButtons()

                    self.pbStartPruefung.setVisible(True)
                    self.pbCancelPruefung.setVisible(False)
                    self.pbCancelPruefung.setEnabled(True)

                return        

        
    def finishPruefung(self):
        if(self.pruefung != None):

            self.pbCancelPruefung.setEnabled(False)

            self.pruefung.finalize_pruefung()
            
            self.lRunZeitValue.setText(self.format_timeString(self.pruefung.get_gesZeit() * 60) + "  (100%)")
            menge = self.pruefung.get_pruefLaufMenge()
            mengeAnteil = menge / self.pruefung.get_gesMenge()
            self.lRunMengeValue.setText(("%.2f" % (menge)) + "  (" +  ("%.2f" % (mengeAnteil * 100))  +"%)")
        
            # Abschließen der Prüfung
            self.timer_endPruefung.setInterval(self.pruefung.DEFAULT_ZEIT_ENDE) #
            self.timer_endPruefung.start()
        
    
    def endPruefung(self):
        if(self.pruefung != None):
            print("Einströmung beendet.")
            self.pruefung.end_pruefung()

            if(not self.pruefung.is_recording()):
                self.pbStartAufzeichnung.setEnabled(True)

                self.reset_configButtons()

                self.pbStartPruefung.setVisible(True)
                self.pbCancelPruefung.setVisible(False)
                self.pbCancelPruefung.setEnabled(True)


    
    def reportPruefung(self):
            
        self.exportPruefPDF("protokolle/")           
        print("Prüf-Report erstellt.")
        
    
    def exportPruefPDF(self, parentDir=""):

        if(self.pruefung): # and self.pruefung._state == self.pruefung.PRUEF_STATE_DONE):  
            
            result = ""
            try:

                fn, _ = QtWidgets.QFileDialog.getSaveFileName(
                    self, "Export PDF", parentDir
                )
                
                if fn:
                    if QtCore.QFileInfo(fn).suffix() == "":
                        fn += ".pdf"
                        
                    c = canvas.Canvas(fn)
                    c.setFont("Courier", 12)
                    
                    offsetX = 50
                    lineHeight = 18
                
                    
                    # Titel
                    c.drawString(offsetX, 800, "SimGas Prüfprotokoll - " + datetime.fromtimestamp(time.time()).strftime('%d.%m.%Y %H:%M:%S'))
                    
                    # Prüfparameter
                    offsetParams = 770
                    c.drawString(offsetX, offsetParams, "Prüfparameter:")
                    c.drawString(offsetX, offsetParams - 1 * lineHeight, "Soll Prüfgasmenge: " + str(self.pruefung.get_gesMenge()) + "g")
                    c.drawString(offsetX, offsetParams - 2 * lineHeight, "Soll Prüfzeit: " + str(self.pruefung.get_gesZeit()) + "min")
                              
                    # Prüfergebnisse
                    offsetErgebnisse = 700
                    c.drawString(offsetX, offsetErgebnisse,"Prüfergebnisse:")
                    c.drawString(offsetX, offsetErgebnisse - 1 * lineHeight, "Ist Prüfgasmenge: " + str("%.1f" % self.pruefung.get_pruefLaufMenge()) + "g")
                                                 
                    # Graph Gasfluss
                    offsetGraphZufuhr = 620
                    c.drawString(offsetX, offsetGraphZufuhr,"Zeitverlauf Gaszufuhr:")
                    offsetGraph_Gasfluss = 290
                    exporterGasfluss = pyexp.ImageExporter(self.mw.graphWidget.graphWidget.plotItem)
                    # imgNameGas = QtCore.QFileInfo(fn).baseName() + ".png"
                    imgNameGas = QtCore.QFileInfo(fn).absoluteFilePath() + QtCore.QFileInfo(fn).baseName() + "gaszufuhr.png"
                    # Erstelle Plot
                    self.mw.graphWidget.pltDataImage(self.pruefung.get_recordEndTime(), imgNameGas, ["GES_SOLL", "GES_IST"], "Zeitstempel [s]", "g/min")
                    # Zeichne Plot in PDF
                    c.drawImage(imgNameGas, offsetX , offsetGraph_Gasfluss, width = 17 * cm, preserveAspectRatio=True)
                    # Entferne zwischengespeicherte Plot Datei
                    os.remove(imgNameGas)
                                     
                    # Graph MGS Boxen
                    offsetGraphKonzentration = 330
                    c.drawString(offsetX, offsetGraphKonzentration,"Zeitverlauf Gaskonzentration:")
                    offsetGraph_Sensorik = -20
                    exporterSensorik = pyexp.ImageExporter(self.mw.graphWidget_gasSensorik.graphWidget.plotItem)
                    # imgNameSens = QtCore.QFileInfo(fn).baseName() + ".png"
                    imgNameSens = QtCore.QFileInfo(fn).absoluteFilePath() + QtCore.QFileInfo(fn).baseName() + "sensorik.png"
                    # Bestimme ausgewählte Sensoren
                    vizSensors = self.mw.graphWidget_gasSensorik.graphWidget.getVisibileCurves()
                    selectedMGS = False
                    selectedGG = False
                    
                    for v in vizSensors:
                        if(str(v).startswith("MGS")):
                            selectedMGS = True
                        if(str(v).startswith("GG")):
                            selectedGG = True
                            
                    # print(selectedMGS,selectedGG)
                    
                    yLabel = ""
                    if(selectedMGS):
                        yLabel = "ppm"
                    if(selectedGG):
                        yLabel = "%"
                    
                    sensorLabels = {}
                    for s in exportConfig.channelExportConfigs:
                        sensorLabels[s] = exportConfig.channelExportConfigs[s]["user_label"]

                    # Erstelle Plot
                    self.mw.graphWidget_gasSensorik.pltDataImage(self.pruefung.get_recordEndTime(), imgNameSens, vizSensors, "Zeitstempel [s]", yLabel, channelLabels=sensorLabels, yMax=exportConfig.Y_MAX, yStep=exportConfig.Y_STEP, numLegendCols=exportConfig.N_COLS)
                    # Zeichne Plot in PDF
                    c.drawImage(imgNameSens, offsetX , offsetGraph_Sensorik, width = 17 * cm, preserveAspectRatio=True)
                    # Entferne zwischengespeicherte Plot Datei
                    os.remove(imgNameSens)
                    
                    c.showPage()
                    c.save()                      
                    
                    self._sig_pdfSaved.emit(fn)     
                
            except Exception as e:
                print(e)
                print("Schreiben der Prüf-PDF fehlgeschlagen!")
                
                self._sig_pdfSaved.emit(result)
                
        else:
            print("Kann nur von abgeschlossenen Prüfungen PDF erstellen!")
        
    
    def lock_configButtons(self):

        self.groupConfig.setEnabled(False)
        self.mw.set_ManualModeEnabled(False)
    

    def reset_configButtons(self):

        if(not self.pruefung.is_busy()):
            self.groupConfig.setEnabled(True)
            self.mw.set_ManualModeEnabled(True)

        
    def update_pruefWidget(self, data):
        if(self.pruefung != None):
            # Update Prüfung
            # print ("PW: Update Pruefung!")
            
            # Update Anzeige
            
            if(self.pruefung._state == self.pruefung.PRUEF_STATE_STARTING):
                self.pbCancelPruefung.setEnabled(True)
                self.lRunMengeValue.setText("---")
                self.lRunZeitValue.setText("---")
            
            elif(self.pruefung._state == self.pruefung.PRUEF_STATE_RUNNING):
                self.pbCancelPruefung.setEnabled(True)
                zeit = self.pruefung.get_pruefLaufZeit()
                zeitAnteil = zeit / (self.pruefung.get_gesZeit() * 60)
                self.lRunZeitValue.setText(self.format_timeString(zeit) + "  (" +  ("%.2f" % (zeitAnteil * 100))  +"%)")
                menge = self.pruefung.get_pruefLaufMenge()
                mengeAnteil = menge / self.pruefung.get_gesMenge()
                self.lRunMengeValue.setText(("%.2f" % (menge)) + "  (" +  ("%.2f" % (mengeAnteil * 100))  +"%)")
            
            elif(self.pruefung._state == self.pruefung.PRUEF_STATE_ENDING):
                self.pbCancelPruefung.setEnabled(False)
    
    
    def set_extendedFunctionVisibility(self, extendedVis):
        self.groupParametrierung.setVisible(extendedVis)

        
    def updateFlaschenZuschaltung(self):
        enableStart = False
        for s in self.sms.zuschaltung:
            if(self.sms.zuschaltung[s] == True):
                enableStart = True
                
        # Prüfung verhindern, wenn keine Zuschaltung aktiv:
        self.pbStartPruefung.setEnabled(enableStart) 
        
        
            
            
    def format_timeString(self, timeSeconds) -> str:
        
            s = ((int(timeSeconds) % 86400) % 3600) % 60	
            m = int(((int(timeSeconds) % 86400) % 3600) / 60)		
            h = int((int(timeSeconds) % 86400) / 3600)
            d = int(int(timeSeconds) / 86400)
            
            
            
            return ("%.2d:%.2d:%.2d:%.2d" % (d, h, m, s))	