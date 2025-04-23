import os
import sys
import time

class Logger():

    def __init__(self):
        pass

    def startExternalLogging(self, folder):
        # Öffne Logfile
        self.logFile = open (os.path.join(folder , self.createTimeStamp() + ".txt"), "w")
        self.errFile = open (os.path.join(folder , self.createTimeStamp() + "-err.txt"), "w")
        self.origStdOut = sys.stdout
        self.origStdErr = sys.stderr
        sys.stdout = self.logFile
        sys.stderr = self.errFile
                    
    def stopExternalLogging(self):
        # Schließen der Log-Files und zurücksetzen des StdOuts
        self.logFile.close()
        self.errFile.close()
        sys.stdout = self.origStdOut
        sys.stderr = self.origStdErr
                    
    def createTimeStamp(self):
        out = time.strftime("%Y%m%d_%H%M", time.localtime())
        return out
    

if __name__ == "__main__":
    l = Logger()
    l.startExternalLogging("log")
    print(l.createTimeStamp())
    10/0
    l.stopExternalLogging()
    
        