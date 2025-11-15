# -*- coding: utf-8 -*-
"""
Created on Mon Sep 12 19:15:31 2022

@author: Paul Benz

v2.3 (Verwende Label statt Namen aus Datamanager)
"""


from PyQt5 import QtCore
from PyQt5.QtWidgets import QWidget, QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QDoubleSpinBox, QLabel, QCheckBox

import pyqtgraph as pg
import pyqtgraph.exporters as pyexp

import random

import time

from datamanager import DataManager
from messdatenUI import MessdatenUI

from PyQt5.QtCore import pyqtSignal

import pandas as pd
import matplotlib.pylab as plt
from matplotlib.ticker import StrMethodFormatter


class MessdatenGraphWidget(QGroupBox):
    """
    Beinhaltet einen Graph zur Anzeige von Messdaten inklusive Control-Buttons zum Handling des Graphen
    """
    
    sig_closeExternal = pyqtSignal()    # wenn externe Ansicht geschlossen wird
    _sig_pdfSaved = pyqtSignal(str) # "" wenn fehler, sonst Filename
    
    
    def __init__(self, parent, dataMan, chNames=None):
        super().__init__()
        
        self.parent = parent
        self.openedExtern = False

        
        ##########
        # Main Layout
        self.mainLayout = QVBoxLayout()
        self.setLayout(self.mainLayout)
    
        # Graph Layout
    
        self.graphWidget = MessdatenGraphPlot(dataMan, chNames)
        self.mainLayout.addWidget(self.graphWidget)
        
        ##########
        # Bottom Layout
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
        self.referenzSpinner.setEnabled(True)
        
        self.refLineLabel = QLabel("Ref. Linie")
        self.refLineLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        
        self.controlLayout.addWidget(self.refLineLabel, 1)
        self.controlLayout.addWidget(self.referenzSpinner, 1)
             

    def set_dataManager(self, dm, channels=None):
        self.graphWidget.set_dataManager(dm, channels)

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


    def pltDataImage(self, path, channels, xLabel, yLabel, channelLabels=None, yMax=None, yStep=None):
        self.graphWidget.pltDataImage(path, channels, xLabel, yLabel, channelLabels, yMax, yStep)
        

    # TODO: mit exportImg zusammenführen
    def buttonSavePNG_clicked(self):
        
        exporter = pyexp.ImageExporter(self.graphWidget.plotItem)
        
        fName = "test.png"
        fName_plt = "test_plt.png"
        result = ""
        result_plt = ""
        
        try:
            exporter.export(fName)
            result = fName
        except:
            print("Schreiben des Graphen in Datei fehlgeschlagen!")
            
        self._sig_pdfSaved.emit(result)


    def buttonOpenExtern_clicked(self):
        if(not self.openedExtern):
            mdui = MessdatenUI(self.parent, self)
            mdui.sig_close.connect(self.close_External)
            self.set_openedExtern(True)
            
    
    def close_External(self):
        self.sig_closeExternal.emit()
        self.set_openedExtern(False)
    
        
    def set_openedExtern(self, enabled):
        self.buttonOpenExtern.setEnabled(not enabled)
        self.openedExtern = enabled
        
    
    def set_selectedChannelNames(self, chNames):
        self.graphWidget.set_selectedChannelNames(chNames)
        
    
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
    
    DEFAULT_CURVE_PENS = [
        pg.mkPen(220,0,220, width=1),       #   lila
        pg.mkPen(250,100,250, width=1),     #   rosa  
        pg.mkPen(0,220,220, width=1),       #  blaugrün
        pg.mkPen(100,220,220, width=1),     #   hellblaugrün
        pg.mkPen(0,220,0, width=1),         #   grün
        pg.mkPen(100,220,100, width=1),     #   hellgrün     
        
        pg.mkPen(0,170,0, width=1),         #   grün        GES_IST
        pg.mkPen(255,0,0, width=1),       #   rot         GES_SOLL
        pg.mkPen(0,0,255, width=1),       #   blau        FP GAS 1  
        pg.mkPen(255,0,255, width=1),       #   lila        FP GAS 2    
        pg.mkPen(0,255,255, width=1),       #   türkis      FP GAS 3         
        
        pg.mkPen(0,170,0, width=1),       #   grün    MGS 1 1
        pg.mkPen(255,0,0, width=1),       #   rot    MGS 1 2
        pg.mkPen(0,0,255, width=1),       #   blau    MGS 2 1
        pg.mkPen(255,0,255, width=1),       #   lila    MGS 2 2
        pg.mkPen(0,170,0, width=1),       #   grün    GG 1
        pg.mkPen(255,0,0, width=1),       #   rot     GG 2
        pg.mkPen(0,0,255, width=1),       #   blau    GG 3
        pg.mkPen(255,0,255, width=1),       #   lila    GG 4
        pg.mkPen(0,255,255, width=1),       #   türkis    GG 5 
        pg.mkPen(200,200,0, width=1),       #   orange    GG 6 
        pg.mkPen(0,0,0, width=1),            #   schwarz    GG 7 
        pg.mkPen(150,150,150, width=1),       #   grau    GG 8 
        
        pg.mkPen(0,0,0, width=1),            #   schwarz     ? 
        pg.mkPen(0,0,0, width=1),            #   schwarz     ? 
        pg.mkPen(0,0,0, width=1)           #   schwarz      ? 
        
        

    ]
    
    def __init__(self, dataMan, chNames=None):	       
        super().__init__(axisItems={'bottom': FmtXAxisItem(orientation='bottom')})

        self.__update = True

        self.__dataMan = dataMan
        self.__chNames = chNames if chNames != None else dataMan.get_channelNames()
        self.__timeRangeOnFokus = 60
        self.__timeRange = 60 # [s] -> 86400 = zeige die Messungen des letzten Tages an
        self.__sampleTime = 1
        
        self.__showLast = True
        
        self.__lastUpdateTime = 0
        self.__maxUpdateRate = 0.5 # Zeit in Sekunden, die mindestens zwischen zwei Datenupdates des Graphen vergehen muss.
        
        self.__floatingWindow = True
        self.__show_only_data_in_range = False        

        ########
        # Axen
        
        self.getPlotItem().getAxis("left").setWidth(40)
        self.getPlotItem().getAxis("left").setPen(pg.mkPen(50,50,50))
        self.getPlotItem().getAxis("left").setTextPen(pg.mkPen(50,50,50))
        
        self.getPlotItem().getAxis("bottom").setHeight(40)
        self.getPlotItem().getAxis("bottom").setPen(pg.mkPen(50,50,50))
        self.getPlotItem().getAxis("bottom").setTextPen(pg.mkPen(50,50,50))

        ###########
        # Legende
        self.addLegend()
        self.getPlotItem().legend.setColumnCount(12)
        anchorx = 0
        anchory = 0
        anchor = (anchorx, anchory)
        self.getPlotItem().legend.anchor(itemPos=anchor, parentPos=anchor, offset=[0,0])
        self.getPlotItem().legend.setLabelTextColor(50,50,50)
         
        ########
        # Plots
        

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
        
        self.init_curves()
        
        self.showGrid(x=True,y=True)
        self.getPlotItem().getViewBox().setDefaultPadding(0.05)
        self.setBackground((255,255,255))                      
        self.resetFokus()
        
    
    def init_curves(self):
                
        xInit = []        
        yInit = []
        
        self.clear()
        
        self.plotVis = dict()
        self.curves = dict()
        
        # Daten 
        # print("init channels: ")
        for i,k in enumerate(self.__dataMan.get_channelNames()):
            if(k in self.__chNames):
                self.plotVis[k] = True                
                self.curves[k]  = self.plot(xInit, yInit, name=self.__dataMan.get_channelLabels()[k], pen=self.DEFAULT_CURVE_PENS[i])   
    
    
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


    def set_selectedChannelNames(self, chNames):
        self.__chNames = chNames
        self.init_curves()


    def set_curveNames(self, curveNames:dict):

        for c in curveNames:
            if c in self.curves:
                self.curves[c].name = curveNames[c]
        self.getPlotItem().legend.update()

        

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
                self.plotVis = visibilities
            
            t = time.time()
            update = t - self.__lastUpdateTime > self.__maxUpdateRate
            if(update):
                # Interne Updaterate
            
                self.__lastUpdateTime = t
                
                datarange = int(self.__timeRange / (sampletime / 1000))
                
                for k in self.curves.keys():
                    if(k in self.__chNames):
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
                        
                
                
    def setCurveVisibility(self, visibilities):
        for c in visibilities:
            if(c in self.curves):
                self.curves[c].setVisible(bool(visibilities[c]))     
        
                
    def getCurveVisibility(self):
        visibilities = {}       
        for c in self.curves:
            visibilities[c] = self.curves[c].isVisible()
        return visibilities
    
    
    def getVisibileCurves(self):
        vizs = []
        for c in self.curves:
            if(self.curves[c].isVisible()):
                vizs.append(c)
        return vizs        

    """              
    def toggle_plotVisibility(self, channel):
        # unused?
        self.plotVis[channel] = not self.plotVis[channel]
    """

        
    def set_plotVisibility_global(self, visibility):
        for k in self.plotVis.keys():
            self.plotVis[k] = visibility
            
    
        
    def set_referenzLinie(self, pos):
        self.refLinie.setPos(pos)
        
        
    def get_graphdata(self):
        return self.__dataMan.get_DataDict()
    
    
    
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
                
                
    
    def pltDataImage(self, path, channels, xLabel, yLabel, channelLabels, yMax = None, yStep=None):

        df = pd.DataFrame.from_dict(self.__dataMan.get_DataDict())
        df.set_index(self.__dataMan.TIME_LABEL, inplace=True)
        df = df[channels]
        
        # Rename columns to use channel labels
        if (channelLabels != None):
            rename_dict = {ch: channelLabels[ch] for ch in channels if ch in channelLabels}
            df.rename(columns=rename_dict, inplace=True)
        
        df.plot()        
        
        # Plot Settings
        plt.legend(loc="upper left", bbox_to_anchor=(1,1))
        plt.xlabel(xLabel)
        plt.ylabel(yLabel)

        if(yMax != None):
            plt.ylim(0, yMax * 1.04)
    
            if(yStep != None):
                plt.yticks(range(0, int(yMax + yStep), int(yStep)))

        plt.grid()
        
        plt.gca().yaxis.set_major_formatter(StrMethodFormatter('{x:,.2f}')) # 2 decimals
        plt.gcf().set_size_inches(10, 4.5)
        plt.savefig(path, bbox_inches='tight', pad_inches=0)


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