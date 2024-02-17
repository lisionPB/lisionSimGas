# -*- coding: utf-8 -*-
"""
Created on Mon Sep 12 19:15:31 2022

@author: Paul Benz

v2.3 (Verwende Label statt Namen aus Datamanager)
"""

from PyQt5 import QtCore
from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QDoubleSpinBox, QLabel, QCheckBox

import pyqtgraph as pg
import pyqtgraph.exporters as pyexp

import random

import time

from datamanager import DataManager
from messdatenUI import MessdatenUI

from PyQt5.QtCore import pyqtSignal



class MessdatenGraphWidget(QGroupBox):
    """
    Beinhaltet einen Graph zur Anzeige von Messdaten inklusive Control-Buttons zum Handling des Graphen
    """
    
    _sig_pdfSaved = pyqtSignal(str) # "" wenn fehler, sonst Filename
    
    
    def __init__(self, parent, dataMan):
        super().__init__()
        
        self.parent = parent
        self.openedExtern = False
        
        self.mainLayout = QVBoxLayout()
        self.setLayout(self.mainLayout)
    
        self.graphWidget = MessdatenGraphPlot(dataMan)
        self.mainLayout.addWidget(self.graphWidget)
        
        self.bottomGroup = QGroupBox()
        self.bottomLayout = QVBoxLayout()
        self.bottomGroup.setLayout(self.bottomLayout)
        self.mainLayout.addWidget(self.bottomGroup)
        
        self.controlLayout = QHBoxLayout()
        self.bottomLayout.addLayout(self.controlLayout)
        
        # Reset Fokus
        self.buttonResetFokus = QPushButton("Reset Fokus")
        self.buttonResetFokus.clicked.connect(self.graphWidget.resetFokus)
        self.controlLayout.addWidget(self.buttonResetFokus)
        self.buttonResetFokus.setFixedWidth(200)
              
        # update
        self.cbUpdate = QCheckBox("Update Graph")
        self.cbUpdate.setChecked(True)
        self.cbUpdate.stateChanged.connect(self.cbUpdate_stateChanged)
        self.controlLayout.addWidget(self.cbUpdate)
        
        # Open Extern
        self.buttonOpenExtern = QPushButton("Diagramm maximieren")
        self.buttonOpenExtern.clicked.connect(self.buttonOpenExtern_clicked)
        self.buttonOpenExtern.setFixedWidth(185)
        self.controlLayout.addWidget(self.buttonOpenExtern) 
        
        # Spacing
        self.controlLayout.addSpacing(1) 
        
        # Referenz Linie
        self.referenzSpinner = QDoubleSpinBox()
        self.referenzSpinner.setDecimals(1)
        self.referenzSpinner.setSingleStep(0.1)
        self.referenzSpinner.setValue(0)
        self.referenzSpinner.setFixedWidth(100)
        self.referenzSpinner.valueChanged.connect(self.set_referenzLinie)
        
        self.refLineLabel = QLabel("Ref. Linie")
        self.refLineLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        
        self.controlLayout.addWidget(self.refLineLabel, 1)
        self.controlLayout.addWidget(self.referenzSpinner, 1)
             
            
              
    def update_MessGraphWidget(self, visibilities=None, sampletime=1000):
        self.graphWidget.update_MessGraphPlot(visibilities, sampletime)
    
    def set_referenzLinie(self, pos):
        self.graphWidget.refLinie.setPos(pos)
        
    def set_floatingWindowEnabled(self, enabled):
        self.graphWidget.set_floatingWindowEnabled(enabled)
        
    def set_timeRangeOnFocus(self, timeRange):
        """Setzt den Anzeigebereich der x-Achse 

        Args:
            timeRange (float): [s]
        """
        self.graphWidget.set_timeRangeOnFocus(timeRange)


    def buttonSavePNG_clicked(self):
        
        exporter = pyexp.ImageExporter(self.graphWidget.plotItem)
        fName = "test.png"
        result = ""
        
        try:
            exporter.export(fName)
            result = fName
        except:
            print("Schreiben des Graphen in Datei fehlgeschlagen!")
            
        self._sig_pdfSaved.emit(result)


    def buttonOpenExtern_clicked(self):
        if(not self.openedExtern):
            mdui = MessdatenUI(self.parent, self)
            self.set_openedExtern(True)
        
        
    def set_openedExtern(self, enabled):
        self.buttonOpenExtern.setEnabled(not enabled)
        self.openedExtern = enabled
        
        
    def set_curveNames(self, names):
        self.graphWidget.set_curveNames(names)
        
        
    def set_update(self, update):
        self.cbUpdate.setChecked(update)
        
        
    def stop_update(self):
        self.cbUpdate.setChecked(False)
        
        
    def cbUpdate_stateChanged(self):
        self.graphWidget.set_update(self.cbUpdate.isChecked())
        

class MessdatenGraphPlot(pg.PlotWidget):
    """
    Widget zur Darstellung von Messdaten mehrerer Datenquellen
    
    Verwaltet werden die Daten über einen Datenmanager, der bei der Initialisierung mit übergeben werden muss.
    
    Verwende update_MessGraphWidget(self, visibilities, sampletime) um neue Daten zu übergeben.
    Verwende set_timeRangeOnFokus(int) [s] Zur Einstellung der x-Range bei Autofokus

    Args:
        DataManager: Datamanager, von dem sich das Widget die Daten holt.
    """
    
    def __init__(self, dataMan):	       
        super().__init__(axisItems={'bottom': FmtXAxisItem(orientation='bottom')})

        self.__update = True

        self.__dataMan = dataMan
        self.__timeRangeOnFokus = 60
        self.__timeRange = 60 # [s] -> 86400 = zeige die Messungen des letzten Tages an
        self.__sampleTime = 1
        
        self.__showLast = True
        
        self.__lastUpdateTime = 0
        self.__maxUpdateRate = 0.5 # Zeit in Sekunden, die mindestens zwischen zwei Datenupdates des Graphen vergehen muss.
        
        self.__floatingWindow = True
        self.__show_only_data_in_range = False        
        
        xInit = []        
        yInit = []
        
        self.getPlotItem().getAxis("left").setWidth(40)
        self.getPlotItem().getAxis("bottom").setHeight(40)

        self.addLegend()
         
        ########
        # Plots
        
        self.plotVis = dict()
        self.curves = dict()
        
        # Referenzlinie
        self.refLinie = pg.InfiniteLine()
        self.refLinie.setAngle(0)
        self.refLinie.setPos(0)
        self.refLinie.setPen(pg.mkPen(255,0,0))
        self.addItem(self.refLinie)
        
        
        # 2. Graph auf rechter yAchse
        """
        y2Init = []      
        self.p2 = pg.ViewBox()
        
        self.showAxis("right")
        self.plotItem.addItem(self.p2)
        self.getPlotItem().getAxis("right").linkToView(self.p2)
        self.p2.setXLink(self)
        self.getPlotItem().getAxis("right").setLabel("Test")
        self.updateViews()
        self.plotItem.vb.sigResized.connect(self.updateViews)
        """
        
        
        # Daten 
        for k in self.__dataMan.get_channelNames():
            self.plotVis[k] = True                
            self.curves[k]  = self.plot(xInit, yInit, name=self.__dataMan.get_channelLabels()[k], pen=pg.mkPen((random.randint(30, 250),random.randint(30, 250),random.randint(30, 250)), width=1))                
        
        
        self.showGrid(x=True,y=True)
        
        self.getPlotItem().getViewBox().setDefaultPadding(0.05)
                        
        self.resetFokus()
        
    
    
    def set_rightAxisLabels(self, labels):
        pass
    
                
    def set_showOnlyDateInRange(self, enabled):
        self.__show_only_data_in_range = enabled
        
        
    def set_timeRange(self, r):
        self.__timeRange = r

    
    def set_timeRangeToDay(self):
        self.__timeRange = 86400
        
        
    def set_timeRangeOnFocus(self, r):
        self.__timeRangeOnFokus = r


    def set_floatingWindowEnabled(self, enabled):
        self.__floatingWindow = enabled


    def set_curveNames(self, curveNames):
        self.__curveNames = curveNames


    def set_update(self, update):
        self.__update = update
    

    def wheelEvent(self, ev):
        if(self.__showLast == True):
            self.loseFokus()
        super().wheelEvent(ev)
        
    def mousePressEvent(self, ev):
        if(self.__showLast == True):
            self.loseFokus()
        super().mousePressEvent(ev)


    def update_MessGraphPlot(self, visibilities=None, sampletime=1000):
        """
        Lässt den Graph aktualisierte Daten vom DataManager holen und stellt sie dar.
        
        @Params:
            - visibilities Boolean[]
            - sampletime [ms]
        """
        #print (data)
        #print (visibilities)
        
        if(self.__update):
            # Graph Freeze?
        
            self.__sampleTime = sampletime
            if(visibilities != None):
                #TODO: Check auf richtige Länge von visibilities
                self.plotVis = visibilities
            
            t = time.time()
            update = t - self.__lastUpdateTime > self.__maxUpdateRate
            #print (update)
            if(update):
                # Interne Updaterate
            
                self.__lastUpdateTime = t
                #print ("timerange: " + str(self.__timeRange))
                
                datarange = int(self.__timeRange / (sampletime / 1000))
                #print ("datarange: " + str(datarange))
                
                for k in self.curves.keys():
                    if(self.plotVis[k] == True):
                        x = []
                        y = []
                        if(self.__show_only_data_in_range):
                            x = self.__dataMan.get_Data(DataManager.TIME_LABEL)[-datarange:]
                            y = self.__dataMan.get_Data(k)[-datarange:]
                        else:
                            x = self.__dataMan.get_Data(DataManager.TIME_LABEL)
                            y = self.__dataMan.get_Data(k)
                        
                        if(len(x) == len(y)):
                            self.curves.get(k).setData(x,y)
                            
                        else:
                            print ("GRAPH FRAME SKIPPED !!! ")
                            print (k)
                        
                        
                    else:
                        self.curves.get(k).clear()		
                        
                # setze View auf letzten Datensatz
                    if(self.__showLast):
                        if(len(self.__dataMan.get_Data(DataManager.TIME_LABEL)) > 0):
                            if(self.__floatingWindow):
                                r = self.__dataMan.get_Data(DataManager.TIME_LABEL)[-1]
                                self.getPlotItem().getViewBox().setXRange(r - self.__timeRangeOnFokus, r, padding=0.0)
                            else:
                                self.getPlotItem().getViewBox().setXRange(0, self.__timeRangeOnFokus, padding=0.0)
                
                #print ("Graph updated")
                        
                
                
            
    def toggle_plotVisibility(self, channel):
        self.plotVis[channel] = not self.plotVis[channel]
        
        
        
        
    def set_plotVisibility_global(self, visibility):
        for k in self.plotVis.keys():
            self.plotVis[k] = visibility
            
    
        
    def set_referenzLinie(self, pos):
        self.refLinie.setPos(pos)
    
    
    
    def resetFokus(self):	
        self.__timeRange = self.__timeRangeOnFokus # Setze Datenfenster auf timeRangeOnFokus Sekunden
        self.getPlotItem().getViewBox().enableAutoRange(x=False, y=True)
        self.__showLast = True

        if(DataManager.TIME_LABEL in self.__dataMan.get_DataDict()):
            if(len(self.__dataMan.get_Data(DataManager.TIME_LABEL)) > 0):		
                if(self.__floatingWindow):
                    r = self.__dataMan.get_Data(DataManager.TIME_LABEL)[-1]
                    self.getPlotItem().getViewBox().setXRange(r - self.__timeRangeOnFokus, r, padding = 0)
                else:
                    self.getPlotItem().getViewBox().setXRange(0, self.__timeRangeOnFokus, padding = 0)
                
    
    def loseFokus(self):
        # Wird aufgerufen, wenn man mit der Maus den Ausschnitt verschiebt
        self.__showLast = False
        self.set_timeRangeToDay()
        
        datarange = int(self.__timeRange / (self.__sampleTime / 1000))
        #print ("datarange: " + str(datarange))
        
        for k in self.curves.keys():
            if(self.plotVis[k] == True):
                self.curves.get(k).setData(self.__dataMan.get_Data(DataManager.TIME_LABEL)[-datarange:], self.__dataMan.get_Data(k)[-datarange:])
            else:
                self.curves.get(k).clear()
                
    
        
class FmtXAxisItem(pg.AxisItem):    
    """
    Formatierungsklasse für die Darstellung der X-Achse als Laufzeit
    """
    
    def __init__(self, *args, **kwargs):    
        super().__init__(*args, **kwargs)
    
    def tickStrings(self, values, scale, spacing):
        
        tickStrings = []
        
        for v in values:
            
            s = ((int(v) % 86400) % 3600) % 60	
            m = int(((int(v) % 86400) % 3600) / 60)		
            h = int((int(v) % 86400) / 3600)
            d = int(int(v) / 86400)
            
            tickStrings.append("%.2d:%.2d:%.2d:%.2d" % (d, h, m, s))	
        
        return tickStrings
    