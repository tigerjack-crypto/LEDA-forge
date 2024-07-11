import argparse
import os
import logging
from typing import Optional


def argparse_check_positive(value):
    try:
        value = int(value)
        if value <= 0:
            raise argparse.ArgumentTypeError(
                "{} is not a positive integer".format(value))
    except ValueError:
        raise Exception("{} is not an integer".format(value))
    return value


def get_no_of_files(directory: str, out_format: str):
    total = 0
    # for root, dirs, files in os.walk("out/cisd"):
    search_dir = directory.format(out_type=out_format)
    for _, _, files in os.walk(search_dir):
        total += len(files)
    return total


def init_logger(logger, log_level: Optional[str] = None):
    if not log_level or log_level == "":
        log_level = os.getenv("LOG_LEVEL")
    print(f"Got level {log_level}")
    # logging_level = logging._nameToLevel.get(log_level, "ERROR")
    logging_level = logging.getLevelName(log_level.upper())
    if type(logging_level) != int:
        logging_level = 30  # Warning
    print(f"log level is {logging_level}")
    # handler = logging.StreamHandler()
    handler = logging.FileHandler('out/cisd.log')
    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d %(module)-4s %(levelname)-5s %(funcName)-12s %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging_level)
