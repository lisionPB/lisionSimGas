import time
import math

def sim_flussMessung_lin(t, a, y0):

    """Generiert Messwerte nach linearer Funktion


    Args:
        t (float): zeit

        a (float): steigung

        y0 (float): y-Achsen Abschnitt
    """
    
    return y0 + a * t

def sim_flussMessung_sin(t, f, a, y0):
    return y0 + math.sin(t * f) * a
    
    