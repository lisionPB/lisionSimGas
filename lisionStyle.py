# -*- coding: utf-8 -*-
"""
Created on Thu Oct  6 12:12:11 2022

@author: Paul Benz
"""

from PyQt5.QtGui import QFont

class LisionStyle():
	
	STYLE_SHEET = "border: none;"
	FONT = QFont("Helvetica [Cronyx]", 9)
 
	LABEL_FONT_BOLD = QFont("Helvetica [Cronyx]", 9, weight=600)
 
	GROUP_MARGIN_NONE = "margin: 0px;"