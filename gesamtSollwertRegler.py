import time
from datetime import datetime


from datamanager import DataManager

class GesamtSollwertRegler:
    """
    Regelt den nötigen Gesamtfluss, um nach geg. Zeit eine geg. Gassmenge zu erhalten.
    Hat keine Informationen über HW-Setup, sondern dient ausschließlich der Berechnung!
    """
    
    ENABLE_LOG = True


    def __init__(self, finalTime, finalFlowSum, totZeit, initFaktor):
        """
        Legt den GesamtSollwertRegler an

        Args:
            finalTime (float): [min]
            finalFlowSum (float): [g]
            totZeit (float): [s]
        """
        self.reset_Regler()
        
        self.finalTime = finalTime * 60     # Gesamtlaufzeit, nach welcher finalFlowSum erreicht werden muss [s]
        self.finalFlowSum = finalFlowSum    # Gasmasse, die nach finalTime geflossen sein muss [g].
        self.totZeit = totZeit
        self.initFaktor = initFaktor        # Faktor auf ersten Stellwert zum Ausgleich des Einschwingverhaltens
        
        self.lastUpdate_SystemTime = 0
                
        
    def start_Regler(self, log=True) -> float:
        """Startet den Regler -> Werte werden zurückgesetzt
        
        Returns:
            (float): Fluss [g/min], um in Zielzeit, die Ziel-Gasmenge zu erreichen. 
        """
        
        self.reset_Regler()

        if(log):
            self.create_logFile()
        
        # Lege erste Messung ab.
        self.lastUpdate_SystemTime = time.time()
        
        self.lastFlow = 0
        self.lastDataTime = 0
        self.startTime = self.lastDataTime # [s]
        self.endTime = self.startTime + self.finalTime # [s]
        
        # Bestimme ersten Stellwert
        self.calc_stellwert(0)

        if(log):
            self.log_gesamtSollwertRegler()

        # Gibt ersten in calc_stallwert() berechneten theoretischen Sollfluss zurück
        return self.lastTheoFlow

            
##################################################################
#
# Interner Regler zum Nachführen des Gesamtsollwertes

    def update_Regler(self, data) -> float:
        """
        Aktualisiert den internen Regler zum Nachführen des Gesamtsollwertes

        Args:
            data (dict): Dictionary mit Kanalname + Messwert der Regelstellglieder [g/min]
            
        Returns:
            (float): -1: wenn Stellwert nicht angepasst wird
                    sonst: Fluss [g/min], um in Restzeit, die Rest-Gasmenge zu erreichen. 
            
        """
        
        # Aktualisiere bisher erreichte Gasmenge
        self.update_totalFlowSum(data)

        self.lastUpdate_SystemTime = time.time()
        timeStamp = data[DataManager.TIME_LABEL]
        update = -1
        # Wenn Zeit zwischen Stellwertkorrekturen abgelaufen ist, berechne neuen Gesamtsollwert
        if(timeStamp - self.lastKorrTime > self.totZeit):
            update = self.calc_stellwert(timeStamp)
        
        self.log_gesamtSollwertRegler()
        
        return update
        
        
        
    def finalize_Regler(self):
        lastTime = time.time()
        deltaT = lastTime - self.lastUpdate_SystemTime
        
        deltaFlow = self.lastFlow * (deltaT/60.0) # Gasfluss seit letzter Messung in Gramm mit linearer Approx.
        self.totalFlowSum  += deltaFlow
        
        
    def calc_stellwert(self, timeStamp):
        
        # Bestimme Restdauer und Gasmenge
        timeLeft = self.endTime - timeStamp
        massLeft = self.finalFlowSum - self.totalFlowSum
        
        self.lastKorrTime = timeStamp
        
        # Berechne theoretischen Fluss
        self.lastTheoFlow = calc_theoreticalStaticFlow(timeLeft, massLeft)
        # print ("theoFlow: " + str(massLeft) + "/" + str(timeLeft) + " = " + str(theoFlow))
        
        # print("LastTheoFlow: " + str(self.lastTheoFlow))
        
        # Multipliziere Startstellwert mit initFaktor zum Ausgleich von Einschwingverhalten
        if(timeStamp == 0):
            self.lastTheoFlow = self.lastTheoFlow * self.initFaktor
        
        return self.lastTheoFlow
    
    
    def update_totalFlowSum(self, data):

        # Verarbeite Messung wenn es nicht die erste ist.
        t = data[DataManager.TIME_LABEL]
        dt = t - self.lastDataTime # [s]
        
        self.lastDataTime = t
        
        currentFlow = calc_dataSum(data)
        deltaFlow = (self.lastFlow + currentFlow) / 2.0 * (dt/60.0) # Gasfluss seit letzter Messung in Gramm mit linearer Approx.
        self.totalFlowSum  += deltaFlow
        
        self.lastFlow = currentFlow
            
    
    
    
    def reset_Regler(self):
        """
        Setzt den Regler zurück, sodass keine Informationen über die vergangenen Messungen vorhanden sind.
        """
        self.lastFlow = 0
        self.lastKorrTime = -float("inf")
        self.lastDataTime = 0
        self.totalFlowSum = 0
        self.startTime = 0
        self.endTime = 0
        
        
        
        
        
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
        
            
        
def calc_dataSum(data) -> float:
    """Summiert den Fluss aller Regel-Stellglieder auf

    Args:
        data (dict): Fluss-Messwerte der Regel-Stellglieder

    Returns:
        float: Summe der Flüsse aller Regel-Stellglieder [g/min]
    """
    messSum = 0
    
    for d in data:
        if d != DataManager.TIME_LABEL:
            messSum += data[d]
    return messSum        


    
def calc_theoreticalStaticFlow(time, mass):
    """
    Berechnet den theoretischen Fluss, der vorliegen muss, um nach finalTime finalFlowSum Gasmenge zu erhalten.
    
    Args:
        time (float): Gesamtlaufzeit, nach welcher finalFlowSum erreicht werden muss [s]
        mass (float): Gasmasse, die nach finalTime geflossen sein muss [g].
    """
    if(time > 0):
        return mass / (time / 60.0)
    
    return 0
            
        
        
    