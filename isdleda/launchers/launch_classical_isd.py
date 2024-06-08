import argparse
import itertools
import logging
import os
import time
from enum import IntEnum
from multiprocessing import Pool
from typing import Optional, Sequence

# BallCollision, BJMM, BJMMdw, BJMMpdw, BJMMplus, BothMay, Dumer, MayOzerov, Prange, Stern
from cryptographic_estimators.SDEstimator import (BJMM, BallCollision, BJMMdw,
                                                  BJMMpdw, BJMMplus, BothMay,
                                                  MayOzerov, Prange,
                                                  SDEstimator)
from isdleda.utils.common import Value
from isdleda.utils.export.export import load_from_pickle, save_to_pickle
from isdleda.utils.paths import ISD_VALUES_FILE_PKL, OUT_FILES_CLASSICAL_FMT

SKIP_EXISTING = False
COUNTER = 0

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

    parser = argparse.ArgumentParser("Launch Lee-Brickell")
    parser.add_argument('-p',
                        '--poolsize',
                        required=True,
                        type=_check_positive,
                        help="Multiprocess pool size")
    parser.add_argument('--chunksize',
                        type=_check_positive,
                        default=2,
                        help="Multiprocess chunk size")
    parser.add_argument("--skip-existing",
                        action="store_true",
                        help="Skip quantum complexity files if existing")
    parser.add_argument("--out-format", choices=["txt", "bin"], default="bin")
    return parser


def isd_compute(arg):
    value = arg
    # excluded_algorithms_by_default = [BJMMd2, BJMMd3, MayOzerovD2, MayOzerovD3]
    skip_algos = [
        BJMM, BallCollision, BJMMdw, BJMMpdw, BJMMplus, BothMay, MayOzerov
    ]
    # skip_algos, memory_access, out_file
    # SDEstimator requires n,k,t as params
    val = 0

    # The idea is that Prange is not influenced much by the memory
    # cost, so we can compute them only once
    prange = None
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
        if SKIP_EXISTING and os.path.isfile(out_file):
            val += 1
            continue
        t0 = time.perf_counter()
        sd = SDEstimator(value.n,
                         value.n - value.r,
                         value.t,
                         excluded_algorithms=skip_algos +
                         list(additional_skip),
                         memory_access=mem_access.value)
        results = sd.estimate()
        te = time.perf_counter()
        if mem_access == MemAccess.MEM_CONST:
            prange = results['Prange']
        else:
            assert prange is not None, "prange is none"
            results['Prange'] = prange
        min_time = min(results.items(),
                       key=lambda algo: algo[1]['estimate']['time'])

        save_to_pickle(out_file, min_time)
        LOGGER.info(
            f"Computed {value}, MEM: {mem_access.name}, real time: {te - t0} seconds"
        )
    return val


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

    # TODO improve
    global SKIP_EXISTING
    SKIP_EXISTING = namespace.skip_existing

    isd_values: Sequence[Value] = load_from_pickle(ISD_VALUES_FILE_PKL)

    tot = len(isd_values) * len(MemAccess)
    LOGGER.info("#" * 80)
    LOGGER.info("Fresh start")
    LOGGER.info("#" * 80)
    LOGGER.info(f"Total points to compute (estimate): {tot}")
    LOGGER.info(f"Skip existing is: {SKIP_EXISTING}")

    if namespace.poolsize == 1:
        for i, value in enumerate(isd_values):
            result = isd_compute(value)
            tot -= result
            print(f"done {i+1}/{tot} -> {(i+1)/tot:%}", end='\r')
            # print(f"done {i+1}/{tot} -> {(i+1)/tot:%}")
        return

    #
    with Pool(namespace.poolsize, maxtasksperchild=400) as p:
        # frp.map_async(
        for i, result in enumerate(
                p.imap_unordered(
                    isd_compute,
                    # itertools.product(isd_values, MemAccess),
                    isd_values,
                    chunksize=namespace.chunksize,
                )):
            tot -= result
            # print(f"done {i+1}/{tot} -> {(i+1)/tot:%}", end='\r')
            print(f"done {i+1}/{tot} -> {(i+1)/tot:%}")

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
