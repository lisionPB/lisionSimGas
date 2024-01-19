# -*- coding: utf-8 -*-
"""

@author: paulb

v2.1
Last changed: 2023-05-26

"""

from PyQt5 import QtCore
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import  QMainWindow, QDialog, QHeaderView, QWidget, QVBoxLayout, QHBoxLayout, QTableView, QPushButton, QLabel, QLCDNumber, QSpinBox, QLineEdit
from PyQt5.QtCore import Qt

from regler_dvr import Regler_Dvr

class ReglerReadOutputLog(QMainWindow):
    """
    Stellt den Regleroutput in als Text dar.
    """

    def __init__(self, parent, r):
        super().__init__(parent)
        self._r = r
        
        self.setWindowTitle(r.get_name())
        
        # layout = QVBoxLayout()
        # self.setLayout(layout)
        
        ###########
        # Datentabelle
        
        
        
        # Header
        self.__header = []
        self.__header.append("time")    
        self.__header.append("line")   
  
        stylesheet = "::section{Background-color:rgb(200,200,255);}"
                
        self.__tableModel = QStandardItemModel(0, len(self.__header))
        self.__tableModel.setHorizontalHeaderLabels(self.__header)
        
        self.__datenView = QTableView()
        
        self.setCentralWidget(self.__datenView)
        self.__datenView.setModel(self.__tableModel)
        self.__datenView.horizontalHeader().setStyleSheet(stylesheet)
        self.__datenView.horizontalHeader().setMinimumSectionSize(80)
        self.__datenView.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.__datenView.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        
        self.__datenView.setColumnWidth(0, 5)
        self.__datenView.setColumnWidth(1, 200)
        
        
        ##############	
        
        # Füge neuankommende Daten dem Table hinzu
        self._r.sig_newMsgReceived.connect(self.add_line)


        self.show()
        
        
    def add_line(self, line):

        rowData = []
        for c in self.__header:		
            if(c == "time"): # Zeit relativ zum Start
                cell = QStandardItem("")
                cell.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                cell.setTextAlignment(QtCore.Qt.AlignCenter)
                rowData.append(cell)
    
            else:
                # print (data[c])
                cell = QStandardItem(line.decode("utf-8"))
                #cell = QStandardItem(str(round(data[c], self.NACHKOMMA_STELLEN)))
                cell.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                cell.setTextAlignment(QtCore.Qt.AlignCenter)
                rowData.append(cell)
                
                
        #self.__tableModel.appendRow(rowData)
        self.__tableModel.insertRow(0, rowData)
        
        if(self.__tableModel.rowCount() > 5) :
            self.__tableModel.removeRow(5)
            
            
            
        
        
    def clear_table(self):
        while(self.__tableModel.rowCount() > 0):
            self.__tableModel.removeRow(0)
        self._rowCount = 0