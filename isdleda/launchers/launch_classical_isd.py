import argparse
from enum import IntEnum
from multiprocessing import Pool
from typing import Optional, Sequence
import time

from cryptographic_estimators.SDEstimator import (BJMM, BJMMdw, BJMMpdw,
                                                  BJMMplus, BothMay,
                                                  SDEstimator)
from isdleda.utils.common import Value
from isdleda.utils.export.export import load_from_pickle, save_to_pickle
from isdleda.utils.paths import ISD_VALUES_FILE_PKL, OUT_FILES_CLASSICAL_FMT


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
    parser.add_argument("--skip-existing",
                        action="store_true",
                        help="Skip quantum complexity files if existing")
    parser.add_argument("--out-format", choices=["txt", "bin"], default="bin")
    return parser


def isd_compute(value):
    skip_algos = [BJMM, BJMMpdw, BJMMplus, BJMMdw, BothMay]
    # skip_algos, memory_access, out_file
    # SDEstimator requires n,k,t as params
    for mem_access in MemAccess:
        sd = SDEstimator(value.n,
                         value.n - value.r,
                         value.t,
                         excluded_algorithms=skip_algos,
                         memory_access=mem_access.value)
        results = sd.estimate()
        min_time = min(results.items(),
                       key=lambda algo: algo[1]['estimate']['time'])

        out_file = OUT_FILES_CLASSICAL_FMT.format(memaccess=mem_access.name,
                                                  out_type='pkl',
                                                  n=value.n,
                                                  r=value.r,
                                                  t=value.t,
                                                  ext='.pkl')

        save_to_pickle(out_file, min_time)


def main(raw_args: Optional[list[str]] = None):
    print("#" * 80)
    parser = parse_arguments()
    if raw_args and len(raw_args) != 0:
        namespace = parser.parse_args(raw_args)
    else:
        namespace = parser.parse_args()
    print(namespace)

    isd_values: Sequence[Value] = load_from_pickle(ISD_VALUES_FILE_PKL)

    t0 = time.time()
    with Pool(namespace.poolsize) as p:
        # frp.map_async(
        for i, _ in enumerate(p.imap_unordered(
                isd_compute,
                isd_values,
        )):
            print(f"done {i/len(isd_values):%}", end='\r')

    te = time.time()
    print(f"Used: {namespace.poolsize} processes ")
    print(f"ISD values no: {len(isd_values)} processes ")
    print(f"Execution time: {te - t0} seconds")

# def test():
#     n0 = 2
#     p = 13232

#     n = p * n0
#     r = p
#     t = 134
#     skip_algos = [BJMM, BJMMpdw, BJMMplus, BJMMdw, BothMay]
#     #skip_algos= [BJMM,BothMay]
#     # skip_algos = []

#     sd = SDEstimator(n,
#                      n - r,
#                      t,
#                      excluded_algorithms=skip_algos,
#                      memory_access=MemAccess.MEM_LOG)
#     results = sd.estimate()
#     print(results)
#     min_time = min(results.items(),
#                    key=lambda algo: algo[1]['estimate']['time'])

if __name__ == '__main__':
    main()
