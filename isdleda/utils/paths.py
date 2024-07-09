import os
# import re
# import pickle
# from typing import (
#     Any,
#     Callable,
#     Dict,
#     Iterator,
#     TYPE_CHECKING,
#     Sequence,
#     Union,
#     Optional,
# )
# import csv

# if TYPE_CHECKING:
#     from measures.common import ValueDicts  # , Code, SecurityLevels

# Lee-Brickell
OUT_FILES_QLB_PART_FMT = ("{n:06}_{r:06}_{t:03}.{ext}")
OUT_FILES_CLB_PART_FMT = ("{n:06}_{r:06}_{t:03}.{ext}")

OUT_FILES_QLB_DIR: str = os.path.join(".", "out", "qlb", "{out_type}")
OUT_FILES_QLB_FMT: str = os.path.join(OUT_FILES_QLB_DIR,
                                      OUT_FILES_QLB_PART_FMT)
OUT_FILES_QLB_SYMBOLIC: str = os.path.join(OUT_FILES_QLB_DIR, "0_symbolic")

OUT_FILES_CLASSICAL_TYPE_DIR: str = os.path.join(".", "out", "cisd", "{out_type}")
OUT_FILES_CLASSICAL_DIR: str = os.path.join(".", "out", "cisd", "{out_type}",
                                            "{memaccess}")
OUT_FILES_CLASSICAL_FMT: str = os.path.join(OUT_FILES_CLASSICAL_DIR,
                                            OUT_FILES_CLB_PART_FMT)

# PRIMES_PATH = "isdleda/assets/proper_primes.csv"
PRIMES_FILE_CSV = os.path.join("assets", "proper_primes.csv")

ISD_VALUES_FILE_PKL = os.path.join("out", "isd_values.pkl")
ISD_VALUES_FILE_JSON = os.path.join("out", "isd_values.json")
