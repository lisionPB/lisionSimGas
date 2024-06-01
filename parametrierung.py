
def calc_parameter(theoretischeFluesse):
    
    # print(theoretischeFluesse)
    
    R1_startSollwert = theoretischeFluesse["COM1"] if "COM1" in theoretischeFluesse else 0
    R2_startSollwert = theoretischeFluesse["COM2"] if "COM2" in theoretischeFluesse else 0
    R3_startSollwert = theoretischeFluesse["COM3"] if "COM3" in theoretischeFluesse else 0
    
    # Initial-Parametersatz
    
    Regler1_Kp = 15.0
    Regler1_Ti = 0.05
    Regler2_Kp = 60.0
    Regler2_Ti = 0.38
    Regler3_Kp = 12.0
    Regler3_Ti = 0.55
    
    ######################################################
    # Bereichsabhängige Parameter
    
    # Regler 1
    
    if((R1_startSollwert >= 0.0) and (R1_startSollwert < 2.0)):
        Regler1_Kp = 160.0
        Regler1_Ti = 0.025
        
    elif ((R1_startSollwert >= 2.0) and (R1_startSollwert < 4.0)):
        Regler1_Kp = 50
        Regler1_Ti = 0.05
        
    elif ((R1_startSollwert >= 4.0) and (R1_startSollwert < 8.0)):
        Regler1_Kp = 15
        Regler1_Ti = 0.05

    elif ((R1_startSollwert >= 8.0) and (R1_startSollwert < 20.0)):
        Regler1_Kp = 15
        Regler1_Ti = 0.05
        
    elif ((R1_startSollwert >= 20.0) and (R1_startSollwert < 28.0)):
        Regler1_Kp = 15
        Regler1_Ti = 0.075
        
    elif ((R1_startSollwert >= 28.0) and (R1_startSollwert < 32.0)):
        Regler1_Kp = 12
        Regler1_Ti = 0.1
        
    elif ((R1_startSollwert >= 32.0) and (R1_startSollwert < 36.0)):
        Regler1_Kp = 10
        Regler1_Ti = 0.1
        
    elif (R1_startSollwert >= 36.0):
        Regler1_Kp = 8
        Regler1_Ti = 0.2
        
        
    # Regler 2
    
    if((R2_startSollwert >= 0.0) and (R2_startSollwert < 60.0)):
        Regler2_Kp = 250
        Regler2_Ti = 0.23
        
    elif ((R2_startSollwert >= 60.0) and (R2_startSollwert < 80.0)):
        Regler2_Kp = 160
        Regler2_Ti = 0.28

    elif ((R2_startSollwert >= 80.0) and (R2_startSollwert < 120.0)):
        Regler2_Kp = 80
        Regler2_Ti = 0.38
        
    elif ((R2_startSollwert >= 120.0) and (R2_startSollwert < 200.0)):
        Regler2_Kp = 60
        Regler2_Ti = 0.38
        
    elif ((R2_startSollwert >= 200.0) and (R2_startSollwert < 280.0)):
        Regler2_Kp = 60
        Regler2_Ti = 0.38
        
    elif ((R2_startSollwert >= 280.0) and (R2_startSollwert < 320.0)):
        Regler2_Kp = 10
        Regler2_Ti = 0.4
        
    elif ((R2_startSollwert >= 320.0) and (R2_startSollwert < 360.0)):
        Regler2_Kp = 10
        Regler2_Ti = 0.45
        
    elif (R2_startSollwert >= 360.0):
        Regler2_Kp = 10
        Regler2_Ti = 0.45
        
        
    # Regler 3
    
    if((R3_startSollwert >= 0.0) and (R3_startSollwert < 455.0)):
        Regler3_Kp = 15
        Regler3_Ti = 0.4
        
    elif ((R3_startSollwert >= 455.0) and (R3_startSollwert < 520.0)):
        Regler3_Kp = 15
        Regler3_Ti = 0.45

    elif ((R3_startSollwert >= 520.0) and (R3_startSollwert < 650.0)):
        Regler3_Kp = 12
        Regler3_Ti = 0.5
        
    elif ((R3_startSollwert >= 650.0) and (R3_startSollwert < 780.0)):
        Regler3_Kp = 4
        Regler3_Ti = 0.55
        
    elif ((R3_startSollwert >= 780.0) and (R3_startSollwert < 1040.0)):
        Regler3_Kp = 3
        Regler3_Ti = 0.6
        
    elif ((R3_startSollwert >= 1040.0) and (R3_startSollwert < 1170.0)):
        Regler3_Kp = 2
        Regler3_Ti = 0.6
        
    elif (R3_startSollwert >= 1170.0):
        Regler3_Kp = 2
        Regler3_Ti = 0.6

        
    return {"COM1": {"Kp" : Regler1_Kp, "Ti": Regler1_Ti}, "COM2": {"Kp" : Regler2_Kp, "Ti": Regler2_Ti}, "COM3": {"Kp" : Regler3_Kp, "Ti": Regler3_Ti}}
