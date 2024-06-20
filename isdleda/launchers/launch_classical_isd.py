import argparse
import functools
import itertools
import logging
import math
import os
import time
from enum import IntEnum
from math import comb, factorial
from multiprocessing import Pool
from typing import Optional, Sequence

# BallCollision, BJMM, BJMMdw, BJMMpdw, BJMMplus, BothMay, Dumer, MayOzerov, Prange, Stern
from cryptographic_estimators.SDEstimator import (BJMM, BallCollision, BJMMdw,
                                                  BJMMpdw, BJMMplus, BothMay,
                                                  Dumer, MayOzerov, Prange,
                                                  SDEstimator, Stern,
                                                  sd_helper)
from isdleda.utils.common import Value
from isdleda.utils.export.export import load_from_pickle, save_to_pickle
from isdleda.utils.paths import ISD_VALUES_FILE_PKL, OUT_FILES_CLASSICAL_FMT

LOGGER = logging.getLogger(__name__)


class MemAccess(IntEnum):
    MEM_CONST = 0
    MEM_LOG = 1
    MEM_SQRT = 2
    MEM_CBRT = 3


def parse_arguments():

    def _check_positive(value):
        try:
            value = int(value)
            if value <= 0:
                raise argparse.ArgumentTypeError(
                    "{} is not a positive integer".format(value))
        except ValueError:
            raise Exception("{} is not an integer".format(value))
        return value

    parser = argparse.ArgumentParser("Launch Classical ISD estimator")
    parser.add_argument('-p',
                        '--poolsize',
                        required=True,
                        type=_check_positive,
                        help="Multiprocess pool size")
    parser.add_argument('--max_tasks',
                        type=_check_positive,
                        help="Multiprocess max tasks per child")
    parser.add_argument('--chunksize',
                        type=_check_positive,
                        default=2,
                        help="Multiprocess chunk size")
    parser.add_argument("--skip-existing",
                        action="store_true",
                        help="Skip quantum complexity files if existing")
    parser.add_argument("--out-format", choices=["txt", "bin"], default="bin")
    parser.add_argument("--cache-gje", action="store_true")
    parser.add_argument("--cache-comb", action="store_true")
    parser.add_argument("--cache-factorial", action="store_true")
    return parser


@functools.cache
def _comb_cached(n: int, k: int):
    """
    binomial coefficient
    """
    return comb(n, k)


@functools.cache
def _factorial_cached(n: int):
    """
    binomial coefficient
    """
    return factorial(n)


# @functools.lru_cache(maxsize=262144)
@functools.cache
def _gaussian_elimination_complexity_cached(n: int, k: int, r: int):
    if r != 0:
        return (r**2 + 2**r + (n - k - r)) * int(((n + r - 1) / r))

    return (n - k)**2


def _process_value(value):
    to_skip = True
    for mem_access in (
            MemAccess.MEM_CONST,
            MemAccess.MEM_LOG,
            MemAccess.MEM_SQRT,
            MemAccess.MEM_CBRT,
    ):
        out_file = OUT_FILES_CLASSICAL_FMT.format(memaccess=mem_access.name,
                                                  out_type='pkl',
                                                  n=value.n,
                                                  r=value.r,
                                                  t=value.t,
                                                  ext='pkl')
        if to_skip and os.path.isfile(out_file):
            LOGGER.info(f"{out_file} already existing, skipping")
            continue
        else:
            to_skip = False
    return not to_skip


def _get_no_of_files():
    # TODO remove hardcoded dir
    total = 0
    # for root, dirs, files in os.walk("out/cisd"):
    for _, _, files in os.walk("out/cisd"):
        total += len(files)
    return total


def isd_compute(arg):
    value = arg
    # excluded_algorithms_by_default = [BJMMd2, BJMMd3, MayOzerovD2, MayOzerovD3]
    skip_algos = [
        BJMM, BallCollision, BJMMdw, BJMMpdw, BJMMplus, BothMay, MayOzerov
    ]

    # The idea is that Prange is not influenced much by the memory
    # cost, so we can compute it only once, and reuse the results later
    prange = None
    t0 = time.perf_counter()
    for (mem_access, additional_skip) in (
        (MemAccess.MEM_CONST, ()),
        (MemAccess.MEM_LOG, (Prange, )),
        (MemAccess.MEM_SQRT, (Prange, )),
        (MemAccess.MEM_CBRT, (Prange, )),
    ):
        out_file = OUT_FILES_CLASSICAL_FMT.format(memaccess=mem_access.name,
                                                  out_type='pkl',
                                                  n=value.n,
                                                  r=value.r,
                                                  t=value.t,
                                                  ext='pkl')
        sd = SDEstimator(value.n,
                         value.n - value.r,
                         value.t,
                         excluded_algorithms=skip_algos +
                         list(additional_skip) + SDEstimator.excluded_algorithms_by_default,
                         memory_access=mem_access.value)
        results = sd.estimate()
        if mem_access == MemAccess.MEM_CONST:
            prange = results['Prange']
        else:
            if prange is None:
                # prange was not computed bcz the file was already present
                # LOGGER.info("Computing Prange for MEM_CONST")
                _sd = SDEstimator(
                    value.n,
                    value.n - value.r,
                    value.t,
                    # Should execute only Prange
                    excluded_algorithms=skip_algos + [Stern, Dumer],
                    memory_access=MemAccess.MEM_CONST)
                _results = _sd.estimate()
                prange = _results['Prange']
                results['Prange'] = prange
        min_time = min(results.items(),
                       key=lambda algo: algo[1]['estimate']['time'])

        save_to_pickle(out_file, min_time)
    te = time.perf_counter()
    return (value, te - t0)


def main(raw_args: Optional[list[str]] = None):
    print("#" * 80)
    level = os.getenv("LOG_LEVEL")
    if level:
        print(f"Got level {level}")
        # logging_level = logging._nameToLevel.get(level, "ERROR")
        logging_level = logging.getLevelName(level.upper())
        if type(logging_level) != int:
            logging_level = 30  # Warning
        print(f"log level is {logging_level}")
        # handler = logging.StreamHandler()
        handler = logging.FileHandler('out/cisd.log')
        formatter = logging.Formatter(
            "%(asctime)s.%(msecs)03d %(module)-4s %(levelname)-5s %(funcName)-12s %(message)s"
        )
        handler.setFormatter(formatter)
        LOGGER.addHandler(handler)
        LOGGER.setLevel(logging_level)
    parser = parse_arguments()
    if raw_args and len(raw_args) != 0:
        namespace = parser.parse_args(raw_args)
    else:
        namespace = parser.parse_args()
    print(namespace)
    print("#" * 80)

    if namespace.cache_gje:
        sd_helper._gaussian_elimination_complexity = _gaussian_elimination_complexity_cached
    if namespace.cache_comb:
        math.comb = _comb_cached
    if namespace.cache_comb:
        math.factorial = _factorial_cached

    # Maybe global is the best solution after all, since the value
    # is initialized once and only accessed from processes. Note that each
    # process will have its own copy of global variable.
    # global SKIP_EXISTING
    # SKIP_EXISTING = namespace.skip_existing

    isd_values: Sequence[Value] = load_from_pickle(ISD_VALUES_FILE_PKL)

    tot = len(isd_values) * len(MemAccess)
    LOGGER.info("#" * 80)
    LOGGER.info("Fresh start")
    LOGGER.info("#" * 80)
    LOGGER.info(f"Total points to compute (estimate): {tot}")
    LOGGER.info(f"Skip existing is: {namespace.skip_existing}")

    if namespace.skip_existing:
        to_process_no = tot - _get_no_of_files()
        to_process_list = filter(_process_value, isd_values)
    else:
        to_process_no = tot
        to_process_list = isd_values

    if namespace.poolsize == 1:
        for i, value in enumerate(to_process_list):
            isd_compute(value)
            print(
                f"done {(i+1)*4}/{to_process_no} (out of {tot}) -> {(i+1) * 4 /to_process_no:%} ({(i+1) * 4 /tot:%})",
                end='\r')
        return

    with Pool(namespace.poolsize, maxtasksperchild=namespace.max_tasks) as p:
        for i, result in enumerate(
                p.imap_unordered(
                    isd_compute,
                    # itertools.product(isd_values, MemAccess),
                    # tuple((value, namespace.skip_existing) for value in filter(_process_value, isd_values)),
                    to_process_list,
                    chunksize=namespace.chunksize,
                )):
            value, time = result
            # * 4 is to model the 4 memory costs
            print(
                f"done {(i+1)*4}/{to_process_no} (out of {tot}) -> {(i+1) * 4 /to_process_no:%} ({(i+1) * 4 /tot:%})",
                end='\r')
            LOGGER.info(f"Computed {value}, real time: {time} seconds")

    print(f"Used: {namespace.poolsize} processes ")
    print(f"ISD values no: {len(isd_values)} processes ")


def test():
    p = 13232

    r = p
    t = 134
    skip_algos = [
        BJMM, BJMMpdw, BJMMplus, BJMMdw, BothMay, MayOzerov, BallCollision
    ]
    #skip_algos= [BJMM,BothMay]
    # skip_algos = []

    for (n0, mem_access) in itertools.product(range(2, 6), MemAccess):
        n = p * n0
        sd = SDEstimator(n,
                         n - r,
                         t,
                         excluded_algorithms=skip_algos,
                         memory_access=mem_access.value)
        results = sd.estimate()
        print(results)
        min_time = min(results.items(),
                       key=lambda algo: algo[1]['estimate']['time'])
        print(min_time)


if __name__ == '__main__':
    # test()
    main()
