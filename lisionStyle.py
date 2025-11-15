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


	LISION_GLOBAL_STYLE_SHEET = """
        QPushButton {
            background-color: #0094da;
            border-radius: 4px;
            color: white;
            padding: 4px;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: #0065b3;
        }
        QPushButton:disabled {
            background-color: #b0b0b0;
        }

        """