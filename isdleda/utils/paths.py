import os

# if TYPE_CHECKING:
#     from measures.common import ValueDicts  # , Code, SecurityLevels

# Quantum format
OUT_FILES_Q_PART_FMT = ("{n:06}_{r:06}_{t:03}.{ext}")
# Classical format
OUT_FILES_C_PART_FMT = ("{n:06}_{r:06}_{t:03}.{ext}")
# Formula-only format
OUT_FILE_FORMULA= ("0_symbolic")
OUT_FILE_FORMULA_FMT = (OUT_FILE_FORMULA + ".{ext}")

OUT_FILES_QLB_DIR: str = os.path.join(".", "out", "qlb", "{out_type}")
OUT_FILES_QLB_FMT: str = os.path.join(OUT_FILES_QLB_DIR,
                                      OUT_FILES_Q_PART_FMT)
OUT_FILES_QLB_SYMBOLIC: str = os.path.join(OUT_FILES_QLB_DIR, "0_symbolic")

# Classical, EsserBellini Tool
OUT_FILES_CEB_TYPE_DIR: str = os.path.join(".", "out", "cisd_eb", "{out_type}")
OUT_FILES_CEB_DIR: str = os.path.join(OUT_FILES_CEB_TYPE_DIR,
                                            "{memaccess}")
OUT_FILES_CEB_FMT: str = os.path.join(OUT_FILES_CEB_DIR,
                                            OUT_FILES_C_PART_FMT)

# PRIMES_PATH = "isdleda/assets/proper_primes.csv"
PRIMES_FILE_CSV = os.path.join("assets", "proper_primes.csv")

ISD_VALUES_FILE_PKL = os.path.join("out", "isd_values.pkl")
ISD_VALUES_FILE_JSON = os.path.join("out", "isd_values.json")

# Figures
OUT_PLOTS_DIR = os.path.join("out", "plots")
OUT_PLOTS_DATA_DIR = os.path.join(OUT_PLOTS_DIR, "data")
