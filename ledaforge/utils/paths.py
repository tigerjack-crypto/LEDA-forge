from os.path import join

OUT_DIR = join("..", "leda_design", "stime_ISD", "out")
OUT_FILES_PART_FMT = ("{n:06}_{k:06}_{w:03}.{ext}")

PRIMES_FILE_CSV = join("assets", "proper_primes.csv")

# ISD_VALUES_FILE_PKL = join("out", "isd_values.pkl")
ISD_VALUES_FILE_JSON = join("out", "values", "isd_values.json")

# Figures
OUT_PLOTS_DIR = join("out", "plots")
OUT_PLOTS_DATA_DIR = join(OUT_PLOTS_DIR, "data")
