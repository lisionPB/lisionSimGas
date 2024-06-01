import time
from datetime import datetime


from datamanager import DataManager

class GesamtSollwertRegler:
    """
    Regelt den nötigen Gesamtfluss, um nach geg. Zeit eine geg. Gassmenge zu erhalten.
    Hat keine Informationen über HW-Setup, sondern dient ausschließlich der Berechnung!
    """
    
    ENABLE_LOG = True
    SCHLUSS_SOLLWERT_FIXIERDAUER = 10 # [s]     Zeit vor Ende der Prüfung, ab der keine Anpassung des Sollwertes mehr vorgenommen wird.


    def __init__(self, finalTime, finalFlowSum, rampenzeit):
        """
        Legt den GesamtSollwertRegler an

        Args:
            finalTime (float): [min]
            finalFlowSum (float): [g]
        """
        self.reset_Regler()
        
        self.finalTime = finalTime * 60     # Gesamtlaufzeit, nach welcher finalFlowSum erreicht werden muss [s]
        self.finalFlowSum = finalFlowSum    # Gasmasse, die nach finalTime geflossen sein muss [g].
        self.initZeit = rampenzeit          # RampenZeit für Reglerwert [s]
        self.initFlow = calc_theoreticalStaticFlow(mass=finalFlowSum, time=self.finalTime)
        # print(self.initFlow)
        self.initDone = False
        
        self.lastUpdate_SystemTime = 0
                
        
    def start_Regler(self, reglerAuswahl, log=True) -> float:
        """Startet den Regler -> Werte werden zurückgesetzt
        
        Returns:
            (float): Fluss [g/min], um in Zielzeit, die Ziel-Gasmenge zu erreichen. 
        """
        
        self._reglerAuswahl = reglerAuswahl
        
        self.reset_Regler()

        if(log):
            self.create_logFile()
        
        # Lege erste Messung ab. 
        self.lastUpdate_SystemTime = time.time()
        
        self.lastFlow = 0
        self.lastDataTime = self.lastUpdate_SystemTime
        self.startTime = self.lastDataTime # [s]
        self.endTime = self.finalTime # [s]
        
        # Bestimme ersten Stellwert
        self.calc_stellwert(0)

        if(log):
            self.log_gesamtSollwertRegler()

        # Gibt ersten in calc_stallwert() berechneten theoretischen Sollfluss zurück
        return self.lastTheoFlow

            
##################################################################
#
# Interner Regler zum Nachführen des Gesamtsollwertes

    def update_Regler(self, gasmengen) -> float:
        """
        Aktualisiert den internen Regler zum Nachführen des Gesamtsollwertes

        Args:
            gasmengen (dict): Addierte Gesamtgasmenge, pro Regler, die durch die Regler geströmt ist [g]
            
        Returns:
            (float): -1: wenn Stellwert nicht angepasst wird
                    sonst: Fluss [g/min], um in Restzeit, die Rest-Gasmenge zu erreichen. 
            
        """
        
        # Aktualisiere bisher erreichte Gasmenge von aktiven Reglern
        self.update_totalFlowSum(gasmengen)

        # Bestimme TimeStamp
        self.lastUpdate_SystemTime = time.time()
        timeStamp = self.lastUpdate_SystemTime - self.startTime
        
        update = self.calc_stellwert(timeStamp)
        
        self.log_gesamtSollwertRegler()
        
        return update
        
        
        
    def finalize_Regler(self, gasmengen):
        self.update_totalFlowSum(gasmengen)
        
        
    def calc_stellwert(self, timeStamp, ignoreInit:bool = False):
        """
        Schreibt theoretischen Gesamtgasfluss zum Erreichen der Zielgasmenge in self.lastTheoFlow und gibt diesen zurück.

        Args:
            timeStamp (float): Zeit in [s] seit Start der Prüfung

        Returns:
            float: neuen Gesamtstellwert [g/min] 
        """
        
        # Bestimme ob Rampen-Zeit abgelaufen ist
        if(timeStamp > self.initZeit or self.initZeit == 0):
            self.initDone = True
        
        
        # Rampenfunktion
        if(not self.initDone and not ignoreInit):
            rampenZeitAnteil = timeStamp / self.initZeit          
            self.lastTheoFlow = max(self.initFlow * rampenZeitAnteil, sum(self._reglerAuswahl.values()) * 0.02)  
        
        else:
            # Bestimme Restdauer und Gasmenge
            timeLeft = self.endTime - timeStamp
            massLeft = self.finalFlowSum - self.totalFlowSum
            
            # Einfrieren des Sollwertes in letzten Sekunde der Prüfung, um Extremreaktionen des Reglers durch Teilen durch 0 zu verhindern.
            if (timeLeft > self.SCHLUSS_SOLLWERT_FIXIERDAUER):
            
                # Berechne theoretischen Fluss
                self.lastTheoFlow = calc_theoreticalStaticFlow(timeLeft, massLeft)
            
            
        return self.lastTheoFlow
    
    
    
    
    
    
    def update_totalFlowSum(self, gasmengen):
        self.totalFlowSum = self.calc_dataSum(gasmengen)
            
    
    
    
    def reset_Regler(self):
        """
        Setzt den GesamtsollwertRegler zurück, sodass keine Informationen über die vergangenen Messungen vorhanden sind.
        """
        self.lastFlow = 0
        self.lastDataTime = 0
        self.totalFlowSum = 0
        self.startTime = 0
        self.endTime = 0
        self.initDone = False   
        
        
        
        
    def create_logFile(self):
        
        if(self.ENABLE_LOG):

            ###################
            # lege Log-Datei an
            
            # Setze Dateipfad aus Aktueller Uhrzeit zusammen.       
            dt = datetime.now()
            dtString = dt.now().strftime('%d-%m-%Y-%H-%M-%S')
            self.dataRecordPath = "dataLogs/Regler_" + dtString + ".csv"
            
            # Erstellt die Log-Datei
            out = "t [s];f_ist [g/min];F_soll [g/min];m [g];mp [g];tp [s]\n"
            
            try:    
                with open(self.dataRecordPath, 'a') as file:
                    file.write(out)
            except:
                print ("Schreiben in LOG-Datei fehlgeschlagen.")
            
            
        
    def log_gesamtSollwertRegler(self):
        
        if (self.ENABLE_LOG):

            out = ""
            out += "{:4.2f}".format(self.lastDataTime).replace('.', ',') + ";"
            out += "{:4.2f}".format(self.lastFlow).replace('.', ',') + ";"
            out += "{:4.2f}".format(self.lastTheoFlow).replace('.', ',') + ";"
            out += "{:4.2f}".format(self.totalFlowSum).replace('.', ',') + ";"
            out += "{:4.2f}".format(self.finalFlowSum).replace('.', ',') + ";"
            out += "{:4.2f}".format(self.finalTime).replace('.', ',') + "\n"
            
            # out = "" + str(self.lastDataTime) + "," + str(self.lastFlow) + "," + str(self.lastTheoFlow) + "," + str(self.totalFlowSum) + "," + str(self.finalFlowSum) + "," + str(self.finalTime) + "\n"
            
            # print (out)
            
            try:    
                with open(self.dataRecordPath, 'a') as file:
                    file.write(out)
            except:
                print ("Schreiben in LOG-Datei fehlgeschlagen.")
        
                
            
    def calc_dataSum(self, gasmengen) -> float:
        """Summiert den Fluss aller aktiven Regel-Stellglieder auf

        Args:
            data (dict): Fluss-Messwerte der Regel-Stellglieder

        Returns:
            float: Summe der Flüsse aller Regel-Stellglieder [g/min]
        """
        messSum = 0
        
        # print (gasmengen)
        
        for p in gasmengen:
            if  p in self._reglerAuswahl:
                messSum += gasmengen[p]
                
        # print (messSum)
        
        return messSum        


    
def calc_theoreticalStaticFlow(time, mass):
    """
    Berechnet den theoretischen Fluss, der vorliegen muss, um nach finalTime finalFlowSum Gasmenge zu erhalten.
    
    Args:
        time (float): Gesamtlaufzeit, nach welcher finalFlowSum erreicht werden muss [s]
        mass (float): Gasmasse, die nach finalTime geflossen sein muss [g].
    """
    
    # print (f"m: {mass}, t: {time}")
    
    if(time > 0):
        return mass / (time / 60.0)
    
    return 0
            
        
        
    
