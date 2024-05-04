import os

from PyQt5 import QtCore, QtGui, QtWidgets, QtPrintSupport
from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QDoubleSpinBox, QLabel
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



class PruefWidget(QGroupBox):
    
    DEFAULT_ZEIT_MIN = 1
    DEFAULT_MASSE_G = 8
    DEFAULT_RAMPENZEIT_S = 5
    
    FILE_CONFIG_DEFAULTS = "config_pruefung.json"
    
    _sig_pdfSaved = pyqtSignal(str) # "" wenn fehler, sonst Filename
    
    def __init__(self, rs, sms, mw):
        """
        Arguments:
            rs (ReglerSetup): zugrundliegendes reglerSetup 
        """
        
        super().__init__()
        
        self.sgr = rs
        self.sms = sms
        self.mw = mw
        
        self._load_pruefConfig()
        
        self.mainLayout = QVBoxLayout()
        self.setLayout(self.mainLayout)
        
        self.setTitle("Prüfung")
        
        self.init_UI()
        
        self.pruefung = None
        
        # Prüfzeit-Time
        self.timer_startPruefung = QTimer()
        self.timer_startPruefung.setSingleShot(True)
        self.timer_startPruefung.timeout.connect(self.cmd_start_pruefung)
        
        self.timer_finishPruefung = QTimer()
        self.timer_finishPruefung.setSingleShot(True)
        self.timer_finishPruefung.timeout.connect(self.finishPruefung)
        
        self.timer_endPruefung = QTimer()
        self.timer_endPruefung.setSingleShot(True)
        self.timer_endPruefung.timeout.connect(self.endPruefung)
        
    
    
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
        
        
        # Gesamtzeit
        groupZeit = QGroupBox("")
        layoutZeit = QHBoxLayout()
        groupZeit.setLayout(layoutZeit)
        self.layoutConfig.addWidget(groupZeit)
        
        lZeitLabel = QLabel("Zeit [min]")
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
            
        
        # GesamtGasMenge
        groupMenge = QGroupBox("")
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
        
        
        # Zeit für Rampe
        groupStartzeit = QGroupBox("")
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
        
        
        
        # Ermittelter Intialfluss
        groupInitFluss = QGroupBox("")
        layoutInitFluss = QHBoxLayout()
        groupInitFluss.setLayout(layoutInitFluss)
        self.layoutConfig.addWidget(groupInitFluss)
        
        lInitFlussLabel = QLabel("Reglerdurchschnittswert [g/min]")
        layoutInitFluss.addWidget(lInitFlussLabel)
        lInitFlussLabel.setFixedWidth(200)
        
        self.lInitFlussLabel = QLabel()
        layoutInitFluss.addWidget(self.lInitFlussLabel)
        self.lInitFlussLabel.setText(str(self.sMengeSpinner.value() / self.sZeitSpinner.value()))
        self.lInitFlussLabel.setFixedWidth(150)
           

        
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
        self.lRunZeitValue.setFixedWidth(150)    
        
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
        self.lRunMengeValue.setFixedWidth(150)   
        
        
        #####################################################
        # CONTROLS
        ############
        
        groupPruefControls = QGroupBox()
        layoutPruefControls = QHBoxLayout()
        groupPruefControls.setLayout(layoutPruefControls)
        self.mainLayout.addWidget(groupPruefControls)
        
        # Start Prüfung
        
        self.pbStartPruefung = QPushButton("Prüfung starten")
        layoutPruefControls.addWidget(self.pbStartPruefung)
        self.pbStartPruefung.clicked.connect(self.start_pruefungClicked)
        
        # Prüfung Abbrechen
        
        self.pbCancelPruefung = QPushButton("Prüfung abbrechen")
        layoutPruefControls.addWidget(self.pbCancelPruefung)
        self.pbCancelPruefung.clicked.connect(self.cancel_pruefungClicked)
        self.pbCancelPruefung.setVisible(False)
        
        
        # Save PDF
        self.buttonSavePDF = QPushButton("PDF exportieren...")
        self.buttonSavePDF.clicked.connect(self.buttonSavePDF_clicked)
        self.buttonSavePDF.setFixedWidth(200)
        self.buttonSavePDF.setEnabled(False)
        layoutPruefControls.addWidget(self.buttonSavePDF)
        
        
    
    def buttonSavePDF_clicked(self):
        self.exportPruefPDF()

    
    
    def calc_initFluss(self):
        fluss = self.sMengeSpinner.value() / self.sZeitSpinner.value()
        self.lInitFlussLabel.setText(str(fluss))
        # TODO: Reglerauswahl visualisieren ???
        
        
        
    def start_pruefungClicked(self):
        
        # Check: Stellglieder auf 0?
        if(self.sgr.safetyCheck_allConnectedAndZero()):
            self.evt_startPruefung()
            # Graph Update aktivieren
            self.mw.graphWidget.set_update(True)
            self.pruefung._sig_pruefCanceled.connect(self.mw.graphWidget.stop_update)
            # Buttons resetten, wenn Prüfung fertig.
            self.pruefung._sig_pruefCanceled.connect(self.resetPruefButtons)
            # Graph Aktualisierung aussetzen wenn Prüfung nicht mehr läuft.
            self.pruefung._sig_pruefCanceled.connect(self.mw.graphWidget.stop_update)
            self.pruefung._sig_pruefEnded.connect(self.mw.graphWidget.stop_update)
            self.pruefung._sig_pruefEnded.connect(self.reportPruefung)
        else: # SafetyCheck Connect And Zero Failed
            self.sgr.protokoll.append(cw.ProtokollEintrag("Prüfung konnte nicht gestartet werden!", typ=cw.ProtokollEintrag.TYPE_FAILURE))

        
    def cancel_pruefungClicked(self):     
        self.evt_cancelPruefung()
        
    
    def evt_startPruefung(self):
        self.cmd_init_pruefung()


    def cmd_init_pruefung(self):
        
        self.buttonSavePDF.setEnabled(False)
        
        self.pruefung = Pruefung(self.sgr, self.sms, self.sZeitSpinner.value(), self.sMengeSpinner.value(), self.sStartzeitSpinner.value())
        
        if(self.pruefung.prepare_pruefung()):
            # Neue Prüfung starten
            self.sgr.reset()
            # Starten einer neuen Prüfung nach Start verhindern: Startknopf ausblenden
            self.pbStartPruefung.setVisible(False)
            self.pbCancelPruefung.setVisible(True)
            self.pbCancelPruefung.setEnabled(False)
            self.groupConfig.setEnabled(False)
            
            self.mw.set_ManualModeEnabled(False)
            self.mw.dataTable.clear_table()
            
            print ("Prüfung wird gestartet ...")
            # Starten der Messschleife          
            self.sgr._start_MessSchleife()
            
            self.timer_startPruefung.setInterval(0)
            self.timer_startPruefung.start()
            self.sgr.protokoll.append(cw.ProtokollEintrag("Prüfung wird gestartet... ", typ=cw.ProtokollEintrag.TYPE_STANDARD))

            return True

        return False
        
        
        
    def cmd_start_pruefung(self):
        if(self.pruefung.start_pruefung()):
            
            # Daten Reset
            self.sgr.reset()
            
            # Timer zum Beenden der Prüfung
            self.timer_finishPruefung.setInterval(int(self.sZeitSpinner.value() * 60000))
            self.timer_finishPruefung.start()
            self.sgr.protokoll.append(cw.ProtokollEintrag("Prüfung gestartet!", typ=cw.ProtokollEintrag.TYPE_SUCCESS))
            
            # print ("Set Graph Range: " + str(self.pruefung.get_gesZeit() * 60))
            self.mw.set_GraphRange(self.pruefung.get_gesZeit() * 60 + 5)
        else:
            self.sgr.protokoll.append(cw.ProtokollEintrag("Starten der Prüfung fehlgeschlagen!", typ=cw.ProtokollEintrag.TYPE_FAILURE))
            self.evt_cancelPruefung()
            
        

    
    def evt_cancelPruefung(self):
        
        if(self.pruefung != None):
            # Prüfung läuft bereits -> Prüfung abbrechen
            if(self.pruefung._state == Pruefung.PRUEF_STATE_RUNNING or self.pruefung._state == Pruefung.PRUEF_STATE_STARTING or self.pruefung._state == Pruefung.PRUEF_STATE_ENDING):
                print ("Prüfung abgebrochen!")
                self.pruefung.cancel_pruefung()
                # Halte Finish Timer an.
                # self.timer_finishPruefung.disconnect()
                self.timer_finishPruefung.stop()
                self.timer_startPruefung.stop()
                # Sichtbarkeiten setzen
                self.pbCancelPruefung.setVisible(False)
                self.pbStartPruefung.setVisible(True)
                self.groupConfig.setEnabled(True)
                self.mw.set_ManualModeEnabled(True)
                
                self.sgr.protokoll.append(cw.ProtokollEintrag("Prüfung abgebrochen!", typ=cw.ProtokollEintrag.TYPE_STANDARD))
            
                return        
        
    
    def resetPruefButtons(self):
        self.pbCancelPruefung.setVisible(False)
        self.pbStartPruefung.setVisible(True)
        self.groupConfig.setEnabled(True)
        self.mw.set_ManualModeEnabled(True)
        
        
        
    def finishPruefung(self):
        if(self.pruefung != None):
            
            self.pruefung.finalize_pruefung()
            
            self.lRunZeitValue.setText(self.format_timeString(self.pruefung.get_gesZeit() * 60) + "  (100%)")
            menge = self.pruefung.get_pruefLaufMenge()
            mengeAnteil = menge / self.pruefung.get_gesMenge()
            self.lRunMengeValue.setText(("%.2f" % (menge)) + "  (" +  ("%.2f" % (mengeAnteil * 100))  +"%)")
        
            # Abschließen der Prüfung
            self.timer_endPruefung.setInterval(int(2000)) # 2 Sekunde verzögert. Evtl geht auch 0 aber testen!
            self.timer_endPruefung.start()
        
    
    def endPruefung(self):
        if(self.pruefung != None):
            print("Prüfung endet ...")
            self.pruefung.end_pruefung()
            self.resetPruefButtons()
        
            
    
    def reportPruefung(self):
        if(self.pruefung._state == self.pruefung.PRUEF_STATE_DONE):
            self.buttonSavePDF.setEnabled(True)
            self.exportPruefPDF("protokolle/")
            
        print("Prüf-Report erstellt.")
    
    
    def exportPruefPDF(self, parentDir=""):
        
        if(self.pruefung and self.pruefung._state == self.pruefung.PRUEF_STATE_DONE):  
            
            result = ""
            try:

                fn, _ = QtWidgets.QFileDialog.getSaveFileName(
                    self, "Export PDF", parentDir, "PDF files (.pdf);;All Files()"
                )
                
                if fn:
                    if QtCore.QFileInfo(fn).suffix() == "":
                        fn += ".pdf"
                        
                    c = canvas.Canvas(fn)
                    c.setFont("Courier", 12)
                    
                    offsetX = 50
                    lineHeight = 20
                
                    
                    # Titel
                    c.drawString(offsetX, 800, "SimGas Prüfprotokoll - " + datetime.fromtimestamp(time.time()).strftime('%d.%m.%Y %H:%M:%S'))
                    
                    # Prüfparameter
                    offsetParams = 750
                    c.drawString(offsetX, offsetParams, "Prüfparameter:")
                    c.drawString(offsetX, offsetParams - 1 * lineHeight, "Soll Prüfgasmenge: " + str(self.pruefung.get_gesMenge()) + "g")
                    c.drawString(offsetX, offsetParams - 2 * lineHeight, "Soll Prüfzeit: " + str(self.pruefung.get_gesZeit()) + "min")
                              
                    # Prüfergebnisse
                    offsetErgebnisse = 650
                    c.drawString(offsetX, offsetErgebnisse,"Prüfergebnisse:")
                    c.drawString(offsetX, offsetErgebnisse - 1 * lineHeight, "Ist Prüfgasmenge: " + str("%.1f" % self.pruefung.get_pruefLaufMenge()) + "g")
                                                 
                    # Graph
                    exporter = pyexp.ImageExporter(self.mw.graphWidget.graphWidget.plotItem)
                    # imgName = QtCore.QFileInfo(fn).baseName() + ".png"
                    imgName = QtCore.QFileInfo(fn).absoluteFilePath() + QtCore.QFileInfo(fn).baseName() + ".png"
                    # exporter.parameters()["invertValue"] = True
                    exporter.export(imgName)
                    c.drawImage(imgName, offsetX , -200, width = 17 * cm, preserveAspectRatio=True)
                    os.remove(imgName)
                    
                    
                    #graphData = self.mw.graphWidget.get_graphdata()
                    #plt.plot(graphData)
                    #plt.savefig('foo.png')

                    # Speichern
                    c.showPage()
                    c.save()           
                    
                    self._sig_pdfSaved.emit(fn)     
                
            except Exception as e:
                print(e)
                print("Schreiben der Prüf-PDF fehlgeschlagen!")
                
                self._sig_pdfSaved.emit(result)
                
        else:
            print("Kann nur von abgeschlossenen Prüfungen PDF erstellen!")
        
    
        
    def update_pruefWidget(self, data):
        if(self.pruefung != None):
            # Update Prüfung
            # print ("PW: Update Pruefung!")
            
            # self.pruefung.update_pruefung(data) # Auskommentiert, weil Update Prüfung nun jedes mal ausgeführt wird, wenn neuer Messwert individueller Regler vorliegt
            
            self.pbCancelPruefung.setEnabled(True)
            
            # Update Anzeige
            
            if(self.pruefung._state == self.pruefung.PRUEF_STATE_STARTING):
                self.lRunMengeValue.setText("---")
                self.lRunZeitValue.setText("---")
            
            elif(self.pruefung._state == self.pruefung.PRUEF_STATE_RUNNING):
                zeit = self.pruefung.get_pruefLaufZeit()
                zeitAnteil = zeit / (self.pruefung.get_gesZeit() * 60)
                self.lRunZeitValue.setText(self.format_timeString(zeit) + "  (" +  ("%.2f" % (zeitAnteil * 100))  +"%)")
                menge = self.pruefung.get_pruefLaufMenge()
                mengeAnteil = menge / self.pruefung.get_gesMenge()
                self.lRunMengeValue.setText(("%.2f" % (menge)) + "  (" +  ("%.2f" % (mengeAnteil * 100))  +"%)")
    
    
    
    
    def set_ControlledModeEnabled(self, enabled):
        self.pbStartPruefung.setEnabled(enabled)    
        
            
            
    def format_timeString(self, timeSeconds) -> str:
        
            s = ((int(timeSeconds) % 86400) % 3600) % 60	
            m = int(((int(timeSeconds) % 86400) % 3600) / 60)		
            h = int((int(timeSeconds) % 86400) / 3600)
            d = int(int(timeSeconds) / 86400)
            
            
            
            return ("%.2d:%.2d:%.2d:%.2d" % (d, h, m, s))	