# -*- coding: utf-8 -*-
"""

@author: paulb

v2.1
Last changed: 2023-05-26

"""

from PyQt5 import QtCore
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import  QHeaderView, QWidget, QVBoxLayout, QHBoxLayout, QTableView, QPushButton, QLabel, QLCDNumber, QSpinBox, QLineEdit
from PyQt5.QtCore import Qt

from datamanager import DataManager

class MessdatenTableWidget(QWidget):
    """
    Stellt die Messdaten in einer Tabelle dar.
    """

    def __init__(self, datamanager):
        super().__init__()
        self._dm = datamanager
        self._rowCount = 0
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        ###########
        # Datentabelle
        
        # Header
        self.__header = []
        for k in self._dm.get_DataDict().keys():
            self.__header.append(k)
        
  
        stylesheet = "::section{Background-color:rgb(200,200,255);}"
                
        self.__tableModel = QStandardItemModel(0, len(self.__header))
        self.__tableModel.setHorizontalHeaderLabels(self.__header)
        
        self.__datenView = QTableView()
        layout.addWidget(self.__datenView)
        self.__datenView.setModel(self.__tableModel)
        self.__datenView.horizontalHeader().setStyleSheet(stylesheet)
        self.__datenView.horizontalHeader().setMinimumSectionSize(80)
        self.__datenView.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.__datenView.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        
        for i in range(len(self.__header)):
            self.__datenView.setColumnWidth(i, 100)
        
                
        ##########
        # Infos
        
        bottomLayout = QHBoxLayout()
        layout.addLayout(bottomLayout)
        bottomLayout.addStretch()
        bottomLayout.addWidget(QLabel("# Zeilen: "))
        self.anzZeilenEdit = QLineEdit("0")
        self.anzZeilenEdit.setFixedWidth(100)
        bottomLayout.addWidget(self.anzZeilenEdit)
        
        
        ##############	
        
        # Füge neuankommende Daten dem Table hinzu
        self._dm.sig_newDataReceived.connect(self.add_data)

        
        
    def add_data(self, data):

        rowData = []
        for c in self.__header:		
            if(c == DataManager.TIME_LABEL): # Zeit relativ zum Start
                s = ((int(data[c]) % 86400) % 3600) % 60	
                m = int(((int(data[c]) % 86400) % 3600) / 60)		
                h = int((int(data[c]) % 86400) / 3600)
                d = int(int(data[c]) / 86400)	
                text = "%.2d:%.2d:%.2d:%.2d" % (d, h, m, s)	

                cell = QStandardItem(text)
                cell.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                cell.setTextAlignment(QtCore.Qt.AlignCenter)
                rowData.append(cell)
    
            else:
                # print (data[c])
                cell = QStandardItem("%.2f" % data[c] if c in data else "")
                #cell = QStandardItem(str(round(data[c], self.NACHKOMMA_STELLEN)))
                cell.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                cell.setTextAlignment(QtCore.Qt.AlignCenter)
                rowData.append(cell)
                
                
        #self.__tableModel.appendRow(rowData)
        self.__tableModel.insertRow(0, rowData)
        self._rowCount += 1
        self.anzZeilenEdit.setText(str(self._rowCount))	
        
        
    def clear_table(self):
        while(self.__tableModel.rowCount() > 0):
            self.__tableModel.removeRow(0)
        self._rowCount = 0