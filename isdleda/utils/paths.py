from os.path import join

OUT_DIR = join("..", "leda_design", "stime_ISD")
OUT_FILES_PART_FMT = ("{n:06}_{k:06}_{w:03}.{ext}")
# if TYPE_CHECKING:
#     from measures.common import ValueDicts  # , Code, SecurityLevels

# # Quantum format
# OUT_FILES_Q_PART_FMT = ("{n:06}_{k:06}_{t:03}.{ext}")
# # Classical format
# # Formula-only format
# OUT_FILE_FORMULA = ("0_symbolic")
# OUT_FILE_FORMULA_FMT = (OUT_FILE_FORMULA + ".{ext}")

# OUT_FILES_QLB_DIR: str = join(".", "out", "qlb", "{out_type}")
# OUT_FILES_QLB_FMT: str = join(OUT_FILES_QLB_DIR, OUT_FILES_Q_PART_FMT)
# OUT_FILES_QLB_SYMBOLIC: str = join(OUT_FILES_QLB_DIR, OUT_FILE_FORMULA)

# Classical, EsserBellini Tool

# Classical, Leda Tool
# OUT_FILES_CLEDA_TYPE_DIR: str = join(".", "out", "cisd_leda", "{out_type}")
# OUT_FILES_CLEDA_FMT: str = join(OUT_FILES_CLEDA_TYPE_DIR, OUT_FILES_C_PART_FMT)

# LEDA parameters
OUT_FILES_LEDA_PARAMS: str = join(".", "out", "values", "from_restrictions", "leda_values.json")

# PRIMES_PATH = "isdleda/assets/proper_primes.csv"
PRIMES_FILE_CSV = join("assets", "proper_primes.csv")

# ISD_VALUES_FILE_PKL = join("out", "isd_values.pkl")
ISD_VALUES_FILE_JSON = join("out", "values", "isd_values.json")

# Figures
OUT_PLOTS_DIR = join("out", "plots")
OUT_PLOTS_DATA_DIR = join(OUT_PLOTS_DIR, "data")
