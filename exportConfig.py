import json

FILE_CONFIG_DIAGRAMM = "config_diagramm.json"

# Gas Sensoren
channelExportConfigs = {}
Y_MAX = 100.0   # %
Y_STEP = 5.0    # %
N_COLS = 4

def save_diagrammConfig():

    config = {
        "y_max" : Y_MAX,
        "y_step": Y_STEP,
        "n_cols": N_COLS
    }

    with open(FILE_CONFIG_DIAGRAMM, "w") as outfile:
        json.dump(config, outfile, indent=4)
    

def load_diagrammConfig():

    f = open(FILE_CONFIG_DIAGRAMM)
    conf = json.load(f)

    global Y_MAX
    global Y_STEP
    global N_COLS

    Y_MAX = conf["y_max"] if "y_max" in conf else 100
    Y_STEP = conf["y_step"] if "y_step" in conf else 5
    N_COLS = conf["n_cols"] if "n_cols" in conf else 10
