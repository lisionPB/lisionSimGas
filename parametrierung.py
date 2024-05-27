
def calc_parameter(theoretischeFluesse):
    
    # print(theoretischeFluesse)
    
    R1_startSollwert = theoretischeFluesse["COM1"] if "COM1" in theoretischeFluesse else 0
    R2_startSollwert = theoretischeFluesse["COM2"] if "COM2" in theoretischeFluesse else 0
    R3_startSollwert = theoretischeFluesse["COM3"] if "COM3" in theoretischeFluesse else 0
    
    # Initial-Parametersatz
    
    Regler1_Kp = 10.0
    Regler1_Ti = 0.1       
    Regler2_Kp = 50.0
    Regler2_Ti = 0.3
    Regler3_Kp = 15.0
    Regler3_Ti = 0.4
    
    ######################################################
    # Bereichsabhängige Parameter
    
    # Regler 1
    
    if((R1_startSollwert >= 0.0) and (R1_startSollwert < 5.0)):
        Regler1_Kp = 160.0
        Regler1_Ti = 0.025
        
    elif ((R1_startSollwert >= 5.0) and (R1_startSollwert < 10.0)):
        Regler1_Kp = 50
        Regler1_Ti = 0.05
        
    elif ((R1_startSollwert >= 10.0) and (R1_startSollwert < 20.0)):
        Regler1_Kp = 15
        Regler1_Ti = 0.05

    elif ((R1_startSollwert >= 20.0) and (R1_startSollwert < 50.0)):
        Regler1_Kp = 15
        Regler1_Ti = 0.05
        
    elif ((R1_startSollwert >= 50.0) and (R1_startSollwert < 70.0)):
        Regler1_Kp = 15
        Regler1_Ti = 0.1
        
    elif ((R1_startSollwert >= 70.0) and (R1_startSollwert < 80.0)):
        Regler1_Kp = 12
        Regler1_Ti = 0.1
        
    elif ((R1_startSollwert >= 80.0) and (R1_startSollwert < 90.0)):
        Regler1_Kp = 10
        Regler1_Ti = 0.1
        
    elif ((R1_startSollwert >= 90.0)):
        Regler1_Kp = 8
        Regler1_Ti = 0.2
        
        
    # Regler 2
    
    if((R2_startSollwert >= 40.0) and (R2_startSollwert < 80.0)):
        Regler2_Kp = 50
        Regler2_Ti = 0.3
        
    elif ((R2_startSollwert >= 80.0) and (R2_startSollwert < 200.0)):
        Regler2_Kp = 50
        Regler2_Ti = 0.3

    elif ((R2_startSollwert >= 200.0) and (R2_startSollwert < 400.0)):
        Regler2_Kp = 50
        Regler2_Ti = 0.3
        
    elif ((R2_startSollwert >= 400.0)):
        Regler2_Kp = 50
        Regler2_Ti = 0.3
        
        
    # Regler 3
    
    if((R3_startSollwert >= 400.0) and (R3_startSollwert < 600.0)):
        Regler3_Kp = 15
        Regler3_Ti = 0.4
        
    elif ((R3_startSollwert >= 600.0) and (R3_startSollwert < 900.0)):
        Regler3_Kp = 15
        Regler3_Ti = 0.5

    elif ((R3_startSollwert >= 900.0) and (R3_startSollwert < 1300.0)):
        Regler3_Kp = 15
        Regler3_Ti = 0.4
        
    elif ((R3_startSollwert >= 1300.0)):
        Regler3_Kp = 15
        Regler3_Ti = 0.4

        
    return {"COM1": {"Kp" : Regler1_Kp, "Ti": Regler1_Ti}, "COM2": {"Kp" : Regler2_Kp, "Ti": Regler2_Ti}, "COM3": {"Kp" : Regler3_Kp, "Ti": Regler3_Ti}}
