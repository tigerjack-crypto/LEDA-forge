import argparse
import logging
import numpy as np
import os
import csv
from enum import IntEnum
from typing import Optional, List

from isdleda.utils.common import ISDValue

OUT_DIR = os.path.join("..", "leda_design", "stime_ISD")

# Official levels
LEVELS = (128, 192, 256)
# Official NIST values
AES_LAMBDAS = (143, 207, 272)
# Best values obtained for Jan+22 Ph.D. Thesis, table 6.5 (Jan+22).
QAES_LAMBDAS = (154, 219, 283)
# Values from Jaques, used by NIST in additional signature calls
# QAES_LAMBDAS = (157, 221, 285)


class MemAccess(IntEnum):
    MEM_CONST = 0
    MEM_LOG = 1
    MEM_SQRT = 2
    MEM_CBRT = 3


def argparse_check_positive(value):
    try:
        value = int(value)
        if value <= 0:
            raise argparse.ArgumentTypeError(
                "{} is not a positive integer".format(value))
    except ValueError:
        raise Exception("{} is not an integer".format(value))
    return value


def get_pass_counter(dir_path: str) -> int:
    counter_file = os.path.join(dir_path, "counter.txt")
    if not os.path.exists(counter_file):
        raise FileNotFoundError(f"No counter file in {dir_path}")

    with open(counter_file, 'r') as f:
        current_pass = int(f.read().strip())

    return current_pass


def set_pass_counter(dir_path: str, value: int):
    counter_file = os.path.join(dir_path, "counter.txt")

    with open(counter_file, 'w') as f:
        f.write(f"{value}")


def get_no_of_files(directory: str, out_format: str):
    total = 0
    # for root, dirs, files in os.walk("out/cisd"):
    search_dir = directory.format(out_type=out_format)
    for _, _, files in os.walk(search_dir):
        total += len(files)
    return total


def init_logger(logger, out_file: str, log_level: Optional[str] = None):
    if not log_level or log_level == "":
        log_level = os.getenv("LOG_LEVEL")
    if not log_level:
        # default level
        log_level = "error"
    print(f"Got level {log_level}")
    # logging_level = logging._nameToLevel.get(log_level, "ERROR")
    logging_level = logging.getLevelName(log_level.upper())
    if type(logging_level) != int:
        logging_level = 30  # Warning
    print(f"log level is {logging_level}")
    # handler = logging.StreamHandler()
    handler = logging.FileHandler(out_file)
    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d %(module)-4s %(levelname)-5s %(funcName)-12s %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging_level)


def get_proper_leda_primes() -> List[int]:
    proper_primes = []
    with open('./isdleda/assets/proper_primes.csv', 'r',
              newline='') as csvfile:
        reader = csv.reader(csvfile)
        # actually there's just one row
        for row in reader:
            proper_primes = list(map(int, row))
    return proper_primes


def get_mra_from_leda(leda_val):
    n = leda_val.p * leda_val.n0
    k = leda_val.p * (leda_val.n0 - 1)
    t = leda_val.t
    return ISDValue(n, n - k, t, msgs=[f"MRA"])


def get_kra1_from_leda(leda_val):
    n = leda_val.p * leda_val.n0  #
    k = leda_val.p * (leda_val.n0 - 1)  #
    t = leda_val.v * 2
    return ISDValue(n, n - k, t, msgs=[f"KRA1"])


def get_kra2_from_leda(leda_val):
    n = 2 * leda_val.p
    k = leda_val.p
    t = leda_val.v * 2
    return ISDValue(n, n - k, t, msgs=[f"KRA2"])


def get_kra3_from_leda(leda_val):
    n = leda_val.p * leda_val.n0
    k = leda_val.p
    t = leda_val.v * leda_val.n0
    return ISDValue(n, n - k, t, msgs=[f"KRA3"])


def get_qc_reduction_mra(leda_val):
    return np.log2(leda_val.p) / 2


def get_qc_reduction_kra1(leda_val):
    return np.log2(leda_val.p) + np.log2(
        leda_val.n0) + np.log2(leda_val.n0 - 1) - 1,


def get_qc_reduction_kra2(leda_val):
    return np.log2(leda_val.p) + np.log2(leda_val.n0)


def get_qc_reduction_kra3(leda_val):
    return np.log2(leda_val.p)

