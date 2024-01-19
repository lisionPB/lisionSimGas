# -*- coding: utf-8 -*-
"""
Created on Mon Jan 18 15:45:31 2023

@author: Paul Benz

v1.0
"""

from PyQt5.QtWidgets import QDialog, QLabel, QVBoxLayout

from PyQt5.QtGui import (QIcon, QPixmap)
from PyQt5.QtCore import (Qt)

class HelpDialog(QDialog):
	def __init__(self, titel, version, jahr):
		super().__init__()
		self.setWindowIcon(QIcon("symbols/lision.ico"))
		self.setWindowTitle("Hilfe")
		self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
		
		layout = QVBoxLayout()
		self.setLayout(layout)
		
		# Lision Logo
		bildLabel = QLabel("")
		bildLabel.setGeometry(0, 0, 56, 256)
		bildBild = QPixmap("symbols/lision.png")
		bildLabel.setPixmap(bildBild)
		layout.addWidget(bildLabel)
		
		
		titelLabel = QLabel(titel)
		titelLabel.setAlignment(Qt.AlignCenter)
		layout.addWidget(titelLabel)
		
		versionLabel = QLabel("Version " + version)
		versionLabel.setAlignment(Qt.AlignCenter)
		layout.addWidget(versionLabel)
		
		copyLabel = QLabel("© " + str(jahr) +  " | Lision GmbH")
		copyLabel.setAlignment(Qt.AlignCenter)
		layout.addWidget(copyLabel)
		
		emailLabel = QLabel("info@lision.de")
		emailLabel.setAlignment(Qt.AlignCenter)
		layout.addWidget(emailLabel)