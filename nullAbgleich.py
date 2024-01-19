import time

NULLABGLEICH_RUHEZEIT = 10.0  # [s]

STATE_INIT = 0
STATE_READY = 1
STATE_RUNNING = 2
STATE_DONE = 3

class NullAbgleich():
    """Ablaufsteuerung und Kommunikation (Senden der Befehle + Auslesen des Status) mit der Hardware
    """
    def __init__(self):
        self.startTime = 0
        self.state = STATE_INIT
        
        
    def confirm_ready(self):
        self.state = STATE_READY
        
    
    def start(self):
        self.startTime = time.time()
        self.state = STATE_RUNNING
        
        
    def complete(self):
        self.state = STATE_DONE
        
        
    def abort(self):
        self.state = STATE_INIT
    

    def update_and_get_process(self):
        if(self.state == STATE_RUNNING):
            val = (time.time() - self.startTime) / (NULLABGLEICH_RUHEZEIT)
            if(val >= 1):
                self.complete()
            return val
        elif(self.state == STATE_DONE):
            return 1.0
        else:
            return 0    