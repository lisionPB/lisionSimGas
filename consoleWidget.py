# -*- coding: utf-8 -*-
"""
Created on Mon Jan 18 15:15:31 2023

@author: Paul Benz

v1.0
"""

from PyQt5 import QtCore
from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTextEdit, QGroupBox, QPushButton, QLabel, QLCDNumber, QDoubleSpinBox, QLineEdit
from PyQt5.QtCore import QTimer, pyqtSignal

import time
from datetime import datetime

class ConsoleWidget(QWidget):
	def __init__(self, _protokoll):
		super().__init__()
		
		self.__protokoll = _protokoll
		
		self.fTimeFormat = "%d.%m.%Y - %H:%M.%S"

		layout = QVBoxLayout()
		self.setLayout(layout)
		
		layout.setContentsMargins(0,0,0,0)
		
		self.consoleText = QTextEdit()
		layout.addWidget(self.consoleText)
		
		self.consoleText.setReadOnly(True)
		self.consoleText.ensureCursorVisible()

		self.__nextIndex = 0 # Index für den nächsten erwarteten Protokolleintrag
		
		
	
	def update_Console(self):
				
		for i in range (self.__nextIndex, len(self.__protokoll)):
			self.consoleText.moveCursor(QTextCursor.End)
			self.add_ConsoleLine(self.__protokoll[i].get_time(), self.__protokoll[i].get_text(), self.__protokoll[i].get_type())
			
		self.__nextIndex = len(self.__protokoll)
				
	
	def add_ConsoleLine(self, timeStamp, line, typ):
		
		timeText = datetime.fromtimestamp(timeStamp).strftime(self.fTimeFormat)
		timeSpan = "<span style='" + self.calc_messageColorStyle(typ) + "'>[" + timeText + "]</span>"
		line = "" + timeSpan + " " + line + "<br>"

		self.consoleText.insertHtml(line)
		
	def calc_messageColorStyle(self, typ):
		
		if(typ == ProtokollEintrag.TYPE_STANDARD):
			return "color: blue;"
		elif (typ == ProtokollEintrag.TYPE_WARNING):
			return "color: orange;"
		elif (typ == ProtokollEintrag.TYPE_SUCCESS):
			return "color: green;"
		elif (typ == ProtokollEintrag.TYPE_FAILURE):
			return "color: red;"


class ProtokollEintrag():
	
	TYPE_STANDARD = 0
	TYPE_WARNING = 1
	TYPE_FAILURE = 2
	TYPE_SUCCESS = 3
	
	def __init__(self, eintrag, typ=0):
		self.__time = time.time()
		self.__text = eintrag
		self.__type = typ
		
	def get_time(self):
		return self.__time
	
	def get_text(self):
		return self.__text
	
	def get_type(self):
		return self.__type