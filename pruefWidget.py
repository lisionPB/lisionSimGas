from PyQt5 import QtCore, QtGui, QtWidgets, QtPrintSupport
from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QDoubleSpinBox, QLabel
from PyQt5.QtCore import QTimer, pyqtSignal


import pyqtgraph as pg
import pyqtgraph.exporters as pyexp

import random

import time
from datetime import datetime

from reportlab.pdfgen import canvas
from reportlab.lib import utils
from reportlab.lib.units import cm
from reportlab.platypus import Frame, Image

#from PIL import Image 

from datamanager import DataManager
from pruefung import Pruefung
import consoleWidget as cw



class PruefWidget(QGroupBox):
    
    DEFAULT_ZEIT_MIN = 1
    DEFAULT_MASSE_G = 8
    DEFAULT_TOTZEIT_S = 10
    DEFAULT_VORLAUFZEIT_S = 10
    
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
        self.sMengeSpinner.setMaximum(1250) 
        self.sMengeSpinner.setValue(self.DEFAULT_MASSE_G)
        self.sMengeSpinner.setFixedWidth(150)
        self.sMengeSpinner.valueChanged.connect(self.calc_initFluss)
        
        # Totzeit für Reglernachführung
        groupTotzeit = QGroupBox("")
        layoutTotzeit = QHBoxLayout()
        groupTotzeit.setLayout(layoutTotzeit)
        self.layoutConfig.addWidget(groupTotzeit)
        
        lTotzeitLabel = QLabel("Totzeit [s]")
        layoutTotzeit.addWidget(lTotzeitLabel)
        lTotzeitLabel.setFixedWidth(200)
        
        self.sTotzeitSpinner = QDoubleSpinBox()
        layoutTotzeit.addWidget(self.sTotzeitSpinner)
        self.sTotzeitSpinner.setDecimals(0)
        self.sTotzeitSpinner.setValue(self.DEFAULT_TOTZEIT_S)
        self.sTotzeitSpinner.setMinimum(0)
        self.sTotzeitSpinner.setMaximum(300)
        self.sTotzeitSpinner.setFixedWidth(150)
        
        # Faktor Reglerstartwert
        groupInitFaktor = QGroupBox("")
        layoutInitFaktor = QHBoxLayout()
        groupInitFaktor.setLayout(layoutInitFaktor)
        self.layoutConfig.addWidget(groupInitFaktor)
        
        lInitFaktor = QLabel("Faktor Reglerstartwert")
        layoutInitFaktor.addWidget(lInitFaktor)
        lInitFaktor.setFixedWidth(200)
        
        self.sInitFaktor = QDoubleSpinBox()
        layoutInitFaktor.addWidget(self.sInitFaktor)
        self.sInitFaktor.setDecimals(2)
        self.sInitFaktor.setMinimum(0.1)
        self.sInitFaktor.setMaximum(2.0)
        self.sInitFaktor.setValue(0.9)
        self.sInitFaktor.setFixedWidth(150)
        self.sInitFaktor.setSingleStep(0.1)
        
        # Vorlauf Zeit
        groupVorlaufZeit = QGroupBox("")
        layoutVorlaufZeit = QHBoxLayout()
        groupVorlaufZeit.setLayout(layoutVorlaufZeit)
        self.layoutConfig.addWidget(groupVorlaufZeit)
        
        lVorlaufZeitLabel = QLabel("Vorlaufzeit Magnetventil[s]")
        layoutVorlaufZeit.addWidget(lVorlaufZeitLabel)
        lVorlaufZeitLabel.setFixedWidth(200)
        
        self.sVorlaufZeitSpinner = QDoubleSpinBox()
        layoutVorlaufZeit.addWidget(self.sVorlaufZeitSpinner)
        self.sVorlaufZeitSpinner.setDecimals(0)
        self.sVorlaufZeitSpinner.setSingleStep(1)
        self.sVorlaufZeitSpinner.setValue(self.DEFAULT_VORLAUFZEIT_S)
        self.sVorlaufZeitSpinner.setMinimum(0)
        self.sVorlaufZeitSpinner.setMaximum(100)
        self.sVorlaufZeitSpinner.setFixedWidth(150)
        
        
        
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
        # self.reglerAuswahl = self.sgr.select_reglerStellglieder_zentriert(fluss)
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
        
        self.pruefung = Pruefung(self.sgr, self.sms, self.sZeitSpinner.value(), self.sMengeSpinner.value(), self.sTotzeitSpinner.value(), self.sInitFaktor.value())
        
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
            
            self.timer_startPruefung.setInterval(int(self.sVorlaufZeitSpinner.value() * 1000))
            self.timer_startPruefung.start()
            self.sgr.protokoll.append(cw.ProtokollEintrag("Prüfung wird gestartet... ", typ=cw.ProtokollEintrag.TYPE_STANDARD))

        else:
            self.sgr.protokoll.append(cw.ProtokollEintrag("Prüfung konnte nicht gestartet werden! Konfiguration überprüfen!", typ=cw.ProtokollEintrag.TYPE_FAILURE))

        
        
        
    def cmd_start_pruefung(self):
        if(self.pruefung.start_pruefung()):
            
            # Daten Reset
            self.sgr.reset()
            
            self.timer_finishPruefung.setInterval(int(self.sZeitSpinner.value() * 60000))
            self.timer_finishPruefung.start()
            self.sgr.protokoll.append(cw.ProtokollEintrag("Prüfung gestartet!", typ=cw.ProtokollEintrag.TYPE_SUCCESS))
            
            # print ("Set Graph Range: " + str(self.pruefung.get_gesZeit() * 60))
            self.mw.set_GraphRange(self.pruefung.get_gesZeit() * 60 + self.sVorlaufZeitSpinner.value() + 5)
        else:
            self.sgr.protokoll.append(cw.ProtokollEintrag("Starten der Prüfung fehlgeschlagen!", typ=cw.ProtokollEintrag.TYPE_FAIILURE))
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
            self.timer_endPruefung.setInterval(2000)
            self.timer_endPruefung.start()
        
    
    def endPruefung(self):
        if(self.pruefung != None):
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
                    self, "Export PDF", None, "PDF files (.pdf);;All Files()"
                )
                
                if fn:
                    if QtCore.QFileInfo(fn).suffix() == "":
                        fn += ".pdf"
                        
                    c = canvas.Canvas(fn)
                    c.setFont("Courier", 12)
                    
                    offsetX = 50
                    lineHeight = 20
                
                    
                    # Titel
                    c.drawString(offsetX, 800, "SimGas Prüfprotokoll - " + self.format_timeString(time.time()))
                    
                    # Prüfparameter
                    offsetParams = 750
                    c.drawString(offsetX, offsetParams, "Prüfparameter:")
                    c.drawString(offsetX, offsetParams - 1 * lineHeight, "Soll Prüfgasmenge: " + str(self.pruefung.get_gesMenge()) + "g")
                    c.drawString(offsetX, offsetParams - 2 * lineHeight, "Soll Prüfzeit: " + str(self.pruefung.get_gesZeit()) + "min")
                              
                    # Prüfergebnisse
                    offsetErgebnisse = 650
                    c.drawString(offsetX, offsetErgebnisse,"Prüfergebnisse:")
                    c.drawString(offsetX, offsetErgebnisse - 1 * lineHeight, "Ist Prüfgasmenge: " + str(self.pruefung.get_pruefLaufMenge()) + "g")
                                                 
                    # Graph
                    exporter = pyexp.ImageExporterExporter(self.mw.graphWidget.graphWidget.plotItem)
                    imgName = QtCore.QFileInfo(fn).baseName() + ".png"
                    exporter.parameters()["invertValue"] = True
                    exporter.export(imgName)
                    c.drawImage(imgName, offsetX , 0, width = 17 * cm, preserveAspectRatio=True)
                    
                    

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
            self.pruefung.update_pruefung(data)
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
        
