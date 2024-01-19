import pandas as pd

def open_log(datamanager, path):
    """
    Lege Datei mit Spaltenbezeichnungen entsprechend der Kanal-Label an.

    Args:
        datamanager (DataManager)
    """

    
    cNames = []
    cNames.append(datamanager.TIME_LABEL)
    
    for cn in datamanager.get_channelNames():
        cNames.append(cn)
    
    
    mf = pd.DataFrame(dict(), columns=cNames)
    
    mf.to_csv(path , index = False, header=True)
        
    
    
    
    
def log_csvDataLine(datamanager, path):
    """
    Schreibt die aktuellsten Daten des Datamanagers in die Logdatei am Ort path

    Args:
        datamanager (DataManager): Datamanager des Setups
        path (str): Pfad zur Log-Datei
    """
    
    lastData = datamanager.get_LastData()

    out = ""

    out += (format_zeitstempel(lastData[datamanager.TIME_LABEL])) + ","
    
    for cn in datamanager.get_channelNames():
        out += ("%.2f" % lastData[cn]) + ","
    
    out = out[:-1]
    out += "\n"
    
    try:    
        with open(path, 'a') as file:
            file.write(out)
    except:
        print ("Schreiben in LOG-Datei fehlgeschlagen.")




def format_zeitstempel(t):
    s = ((int(t) % 86400) % 3600) % 60	
    m = int(((int(t) % 86400) % 3600) / 60)		
    h = int((int(t) % 86400) / 3600)
    d = int(int(t) / 86400)	
    return "%.2d:%.2d:%.2d:%.2d" % (d, h, m, s)