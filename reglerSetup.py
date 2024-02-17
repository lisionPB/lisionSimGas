# -*- coding: utf-8 -*-
"""
Created on Wed Jul 20 17:07:37 2022

@author: paulb
"""

from PyQt5 import QtWidgets

import json

import regler_dvr_modbus as rgl
import hwSetupModbus as hws
import consoleWidget as cw
import gesamtSollwertRegler as gsr


class SimGasRegler(hws.HWSetupModBus):
    """
    Stellt die Verwaltung der Hardware dar.

    Args:
        hws (_type_): _description_
    """
  
    CONFIG_FILE = "config_cori_modbus.json" 
    
    ALLOW_IGNORE_PUFFER = False
    
    
    def __init__(self, modbusCtrl):
        super().__init__( modbusCtrl )
        
        self.protokoll = []
        
        # Laden der Reglerkonfiguration und setzen zugehörigen Ports
        self._load_reglerConfig(self.CONFIG_FILE) # -> self._ports wird gefüllt.
        
        
        # TESTFUNKTION zu
        # self.test_reglerStellwerteBeiKonfiguration()
        
        # Definition der Channel über Reglerkonfig + Umgebungssensoren
        chNames = []
        chLabels = dict()
        for n in self._ports:
            chNames.append(n)
            chNames.append(n + "_SOLL")
            chLabels[n] = self._ports[n].get_name()
            chLabels[n + "_SOLL"] = self._ports[n].get_name() + " (soll)"
            
        chNames.append("GES_IST")
        chNames.append("GES_SOLL")
        chNames.append("FP")
            
        self.dm.set_channelNames(chNames)
        self.dm.set_channelLabels(chLabels)
        
        # Berechne Reglergrenzen aus Reglerkonfiguration
        self.__maxGesStellwert = self.calc_max_gesSollwert() 
        self.__minGesStellwert = self.calc_min_gesSollwert()
        
        self.__gesSoll = 0
        self.__reglerAuswahl = None
        
        # Sicherungseigenschaften
        # self.__safety_setZero = self.safetyCheck_allConnectedAndZero()
        
                
    
    def _load_reglerConfig(self, confFileURL):
        """
        Liest Regler-Konfiguration aus json-File
        """
        # TODO: Ausnahmebehandlung, wenn Config File nicht gefunden wurde oder File ungültiges Format hat!
        
        f = open(confFileURL)
        conf = json.load(f)
        
        for d in conf:
            kalib = [0.0, 1.0, 0.0, 0.0]
            if("kalibrierung" in conf[d]):
                kalib = conf[d]["kalibrierung"]
                
            r = rgl.Regler_Dvr_ModBus(d, conf[d]["bereich"], kalib, self.modBusCtrl)
            
            self._zuweisen_Port(d, r)

        f.close()


    def test_reglerStellwerteBeiKonfiguration(self):
        maxStellwert = 1300
        minStellwert = 0
        resolution = 10
        
        for s in range(minStellwert  * resolution, maxStellwert * resolution, 1):
            stellwert = s/resolution
            
            self.log_csv_stellwerte(stellwert, self.calc_reglerAuswahl(stellwert), "reglerauswahltest.csv")
            
        print ("regerauswahltest abgeschlossen.")
        
        
        
    def save_reglerConfig(self):
        conf = {}
        for p in self._ports:
            # print (p)
            config = {}
            config["bereich"] = self._ports[p].get_arbeitsBereich()
            config["kalibrierung"] = self._ports[p].get_kalibrierung()
            conf[self._ports[p].get_name()] = config
        
        with open(self.CONFIG_FILE, "w") as outfile:
            json.dump(conf, outfile, indent=4)
            
        print ("Regler-Konfiguration gespeichert.")
            
    
    

######################################
#
# Check Sicherungseigenschaften


    def safetyCheck_allConnectedAndZero(self):
        """
        Überprüft, ob alle Stellglieder verbunden un in 0-Position

        Returns:
            bool: True: Alle Stellglieder sind verbunden und in 0-Position
        """
        if (not self._testmode):
            for p in self._ports:
                soll = self._ports[p]._read_Sollwert()
                print ("Check Soll: " + str(soll))
                if(soll != 0 or soll == None):       
                    self.protokoll.append(cw.ProtokollEintrag("SAFETY-CHECK: Verbindung und 0-Position: FEHLGESCHLAGEN!", typ=cw.ProtokollEintrag.TYPE_FAILURE))
                    return False
                
        return True

            





###########################################################################
#
# Berechnung der ReglerAuswahl abhängig von Soll-Gesamtfluss 
    
    
    def calc_reglerAuswahl(self, totalSoll) -> dict:
        """ 
        Args:
            totalSoll (float): gesamt Sollwert [g/min]
        Returns:
            (dict): ports mit zugehörigem Max-Stellwert
        """
        
        return self.select_reglerStellglieder_zentriert(totalSoll)
    
    
    
    def select_reglerStellglieder_zentriert(self, totalSoll) -> dict:
        """
        Berechnet eine Auswahl aktiver Regler, unter der die Abweichung ihrer Stellwerte für den Gesamtsollwert der ausgewählten Stellglieder vom Mittel
        ihrer jeweiligen Arbeitsbereiche minimal ist.

        Args:
            totalSoll (float): gesamt Sollwert [g/min]
        Returns:
            dict: Reglerauswahl mit jeweiligem maxStellwert
        """
        # Interne Funktion zum Nehmen der Arbeitsbereiche von Ports
        def takeArbeitsbereich(portAB):
            return portAB[1]
        
        portArbeitsbereiche = [[p , self._ports[p].get_arbeitsBereich()[1]] for p in self._ports if self._ports[p].is_enabled()]  
        portArbeitsbereiche.sort(key=takeArbeitsbereich)
            
            
        if(totalSoll > 0):
            
            # Anzahl möglicher Reglerzusammenstellungen
            opts = 2 ** len(self._ports)
            
            bestSet = [False for i in range(len(portArbeitsbereiche))]
            bestPerc = 1.0
            
            # Gehe alle Reglerkonfigurationen durch und prüfe, ob sie die beste ist.
            for o in range(opts):
                if(o != 0):
                    
                    active =  [False for i in range(len(portArbeitsbereiche))] # Ob Stellglied aktiv
                    totalActiveMax = 0
                    
                    # Stelle Stellglieder zusammen
                    for i in range(len(portArbeitsbereiche)):
                        take = o & (2 ** i) > 0
                        active[i] =  take
                        totalActiveMax += portArbeitsbereiche[i][1] if take else 0
                    
                    
                    # Überprüfe ob Lösung besser ist als bisherige beste
                    if(totalActiveMax > 0):
                        perc = totalSoll / totalActiveMax
                        if(abs(bestPerc - 0.5) > abs(perc - 0.5)):
                            # Überprüfe, ob Lösung gültig
                            if (perc > rgl.Regler_Dvr_ModBus.ARBEITSBEREICH_PUFFER and perc <= 1.1): # TODO: Arbeitsbereich Überschreitung abstimmen
                                bestPerc = perc
                                for i in range (len(active)):
                                    bestSet[i] = active[i]
                            
                            
            # Setzt bestSolls
#            bestSolls = [] # Absolutstellwerte [Port, g/min]
#            for i in range(len(portArbeitsbereiche)):
#                bestSolls.append([portArbeitsbereiche[i][0], portArbeitsbereiche[i][1] * bestPerc if bestSet[i] else 0])

            auswahl = {}
            for i in range(len(portArbeitsbereiche)):
                if bestSet[i]:
                    auswahl[portArbeitsbereiche[i][0]] = portArbeitsbereiche[i][1]
            return auswahl
        
        else:
            return {}
        
    
    def set_reglerAuswahl(self, reglerAuswahl):
        self.__reglerAuswahl = reglerAuswahl
            
        
    def log_csv_stellwerte(self, totalSoll, stellwerte, pfad):
        """Testfunktion zur Auswahl der Regler nach gegebenem Sollwert

        Args:
            totalSoll (_type_): _description_
            stellwerte (_type_): _description_
            pfad (_type_): _description_
        """
                    
        # Visualisierung
        out = "{:4.2f}".format(totalSoll) + ";"
        total = 0
        for p in stellwerte:
            out += "{:4.2f}".format(stellwerte[p]) + ";"
            total += stellwerte[p]
        out += "{:4.2f}".format(total) + "\n"
        # print (out)
        
        
        # Schreibe CSV Line
        try:    
            with open(pfad, 'a') as file:
                file.write(out)
        except:
            print ("Schreiben in LOG-Datei fehlgeschlagen.")
           
           
           
           
           
           
##################################################################
#
# Setzen und Aufteilen des Gesamt-Sollwertes

    def set_allClosed(self) -> bool:
        """Schließt alle Regel-Stellglieder

        Returns:
            bool: False, wenn Schließen fehlschlägt. Sonst True.
        """
        
        # TODO: Hierarchie der Fehlermeldungen: Welche Fehler können auftreten, wie werde sie gemeldet und behandelt
        
        ok = True
        for p in self._ports:
            if(not self.set_Sollwert(p, 0)):
                ok = False
        if(ok == True):
            self.__gesSoll = 0
        return ok


    def set_GesamtSollwertAbsolut(self, stellwert, reglerAuswahl=None) -> bool:
        """Setzt des Gesamt-Sollwert als Absoluten Wert [g/min].

        Args:
            stellwert (float): Absoluter Gesamt-Sollwert [g/min]
            reglerAuswahl (dict, optional): [port] -> maxArbeitsbereich
            
           Falls eine Reglerauswahl übergeben wird, wird diese verwendet.
           Falls keine Reglerauswahl übergeben wird, werden alle Ports verwendet.

        Returns:
            bool: True, wenn Sollwert Setzen erfolgreich. Sonst False.
        """
        anteil = 0
        if(stellwert > 0):
            abSum = 0
            
            if(reglerAuswahl == None):
                reglerAuswahl = self._ports
                for r in reglerAuswahl:
                    abSum += reglerAuswahl[r].get_arbeitsBereich_max()
            elif(not reglerAuswahl):
                print ("Fehler beim Setzen des Sollwertes: keine valide Reglerauswahl gefunden!")
                return False
            else:
                print ("Setze Gesamtsollwert mit: ")
                for p in reglerAuswahl:
                    print (str(p) + ": " + str( reglerAuswahl[p]))
                    abSum += reglerAuswahl[p]
                
            anteil = stellwert / abSum
            
            return self.set_GesamtSollWert(anteil, reglerAuswahl)
        else:
            return self.set_GesamtSollWert(0, None)



    def set_GesamtSollWert(self, anteil, reglerAuswahl, pruefung=False) -> bool:
        """ 1. Schließen aller Regler, wenn anteil = 0
            2. Überprüfung ob Sollwert innerhalb der Systemgrenzen abgebildet werden kann
            3. Setzen der einzelnen Regelstellglieder  

        Args:
            anteil (_type_): _description_
            reglerAuswahl (_type_): _description_
            pruefung (bool, optional): _description_. Defaults to False.

        Returns:
            bool: True, wenn erfolgreich, False sonst.
        """
                
        if(anteil == 0):
            # Wenn Stellwert == 0 -> Setze alle Glieder auf 0 
            ok = True
            for p in self._ports:
                if(not self.set_Sollwert(p, 0)):
                    ok = False
            if(ok == True):
                self.__gesSoll = 0
            return ok
        
        
        # Überprüfung des Stellwertes auf Grenzen durch Arbeitsbereiche
        
        # print ("anteil: " + str(anteil))
        
        if(anteil < 0.02):
            if(not pruefung):
                # Stellwert zu klein
                self.protokoll.append(cw.ProtokollEintrag("Fehler beim Setzem des Sollwertes! Stellwert zu niedrig!", typ=cw.ProtokollEintrag.TYPE_FAILURE))
                print ("Fehler beim Setzen des Sollwertes: Sollwert liegt unterhalb des Gesamtarbeitsbereichs des Regelsystems!")
                return False
            else:
                # In Prüfung: Nicht abbrechen -> Setze Sollwert auf Minimum (0.02)                
                self.protokoll.append(cw.ProtokollEintrag("Warnung! Sollwert unterschreitet minimalen Stellwert! Stellwert auf untere Grenze gesetzt.", typ=cw.ProtokollEintrag.TYPE_WARNING))
                print ("Warnung! Sollwert unterschreitet minimalen Stellwert! Stellwert auf untere Grenze gesetzt.")
                anteil = 0.02
        
        if(anteil > 1.0):
            if (not pruefung):
                # Stellwert zu groß    
                self.protokoll.append(cw.ProtokollEintrag("Fehler beim Setzem des Sollwertes! Stellwert zu hoch!", typ=cw.ProtokollEintrag.TYPE_FAILURE))
                print ("Fehler beim Setzen des Sollwertes: Sollwert liegt oberhalb des Gesamtarbeitsbereichs des Regelsystems!")
                return False
            else:
                # In Prüfung: Nicht abbrechen -> Setze Sollwert auf Maximum (1.0)                
                self.protokoll.append(cw.ProtokollEintrag("Warnung! Sollwert überschreitet maximalen Stellwert! Stellwert auf obere Grenze gesetzt.", typ=cw.ProtokollEintrag.TYPE_WARNING))
                print ("Warnung! Sollwert überschreitet maximalen Stellwert! Stellwert auf obere Grenze gesetzt.")
                anteil = 1.0
        
    
        # Setze Stellglieder gleichmäßig Anteil an Gesamtarbeitsbereich
        
        gesSoll = 0
        for p in self._ports:
            if(p in reglerAuswahl):
                val = self._ports[p].get_arbeitsBereich()[1] * anteil
                gesSoll += val
                if(not self._ports[p]._set_Sollwert(val) and not self._testmode):
                    gesSoll = 0
                    return False
            else:
                if(not self._ports[p]._set_Sollwert(0) and not self._testmode):
                    return False
        
        self.__gesSoll = gesSoll
        return True
        
        

###################
     
    def _read_Messwerte(self):
        """Liest die Messwerte der Regelstellglieder aus.
        Erweitert und nutzt die Funktion _read_Messwerte() von hwSetup.py

        Returns:
            Float: Messwerte aller Regelstellglieder + Umgebungssensoren. None, falls keine gültigen Messwerte vorliegen
        """
        
        # --------------------------
        
        = # TODO: Triggern des Auslesens von ModBus FELDKOPPLER und Warten bis Messwerte bereitstehen
        
        #
        #   
        # --------------------------
        
        mess = super()._read_Messwerte()
        soll = {}
        
        
        # Summe aller aktiven Regler (Reglerauswahl bei Prüfung)
        messsum = 0 
        busy = False
        if(mess != None):
            for p in mess:
                if(self.__reglerAuswahl == None or p in self.__reglerAuswahl):
                    if (mess [p] != "BUSY"):
                        messsum += mess[p]
                    else:
                        busy = True
                soll[p + "_SOLL"] = self._ports[p].get_soll()
                
            for ps in soll:
                mess[ps] = soll[ps]
                
            if(not busy):
                mess["GES_IST"] = messsum
            else:
                
                if(len(self.dm.get_LastData()) > 0 and "GES_IST" in self.dm.get_LastData()): 
                    mess["GES_IST"] = self.dm.get_LastData()["GES_IST"]
                else:
                    mess["GES_IST"] = 0

            mess["GES_SOLL"] = self.__gesSoll
            
                            
            # Integriere Externe Daten
            for k in self.externData:
                mess[k] = self.externData[k]
                
                
        
        return mess 




#####################################################################
#
# Kalibrierung

    def set_current_GasEigenschaften(self, fp, tp):
        for p in self._ports:
            self._ports[p].set_current_pVordruck(fp)
            self._ports[p].set_current_TGas(tp)


##############################################################
#
# GesamtSystem Werte 

    def get_GesamtSollWert(self):
        """
        Summiert die bestätigten Sollwerte aller Regler
        """
        sum = 0
        for p in self._ports:
            sum += self._ports[p].get_soll()
        return sum
    
    
    def get_GesamtIstWert(self):
        """
        Summiert die bestätigten Messwerte aller Regler
        """
        sum = 0
        for p in self._ports:
            if(p != None):
                ist = self._ports[p].get_ist()
                sum += ist if ist != None else 0
        return sum
    
    
    def get_max_gesSollwert(self):
        """
        Gibt den maximalen durch die Regler-Konfiguration realisierbaren Gesamt-Stellwert zurück.

        Returns:
            float: max. Gesamtstellwert
        """
        return self.__maxGesStellwert
    
    
    def get_min_gesSollwert(self):
        """
        Gibt den minimalen durch die Regler-Konfiguration realisierbaren Gesamt-Stellwert  > 0 zurück.

        Returns:
            float: min. Gesamtstellwert
        """
        return self.__minGesStellwert
    
    
            
    def calc_max_gesSollwert(self):
        sum = 0
        for p in self._ports:
            sum += self._ports[p].get_arbeitsBereich()[1]
            
        return sum
    
    
    
    def calc_min_gesSollwert(self):
        minVal = float('inf')
        for p in self._ports:
            minVal = min(self._ports[p].get_arbeitsBereich()[0], minVal)
        return minVal
    
        
    
    def get_ges_arbeitsBereich(self):
        return [self.__minGesStellwert, self.__maxGesStellwert]
    
    
    
##############################################################
#
# Sollwerte von einzelnen Reglern
        
        
    
    def set_Sollwert(self, port, soll):
        return self._ports[port]._set_Sollwert(soll)
    
    
    def get_Sollwert(self, port):
        return self._ports[port]._read_Sollwert()


