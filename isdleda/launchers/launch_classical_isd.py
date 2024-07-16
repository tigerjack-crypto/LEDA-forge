"""Launch the classical ISD estimator from TII
"""
import argparse
import collections
import itertools
import logging
import os
import time
from datetime import datetime
from enum import IntEnum
from multiprocessing import Pool
from typing import Optional, Sequence

# BallCollision, BJMM, BJMMdw, BJMMpdw, BJMMplus, BothMay, Dumer, MayOzerov, Prange, Stern
from cryptographic_estimators.SDEstimator import (BJMM, BallCollision, BJMMdw,
                                                  BJMMpdw, BJMMplus, BothMay,
                                                  MayOzerov, Prange,
                                                  SDEstimator)
from isdleda.launchers.launcher_utils import (argparse_check_positive,
                                              get_no_of_files, init_logger)
from isdleda.utils.common import Value
from isdleda.utils.export.export import load_from_pickle, save_to_pickle
from isdleda.utils.paths import (ISD_VALUES_FILE_PKL, OUT_FILES_CLASSICAL_FMT,
                                 OUT_FILES_CLASSICAL_TYPE_DIR)

LOGGER = logging.getLogger(__name__)


class MemAccess(IntEnum):
    MEM_CONST = 0
    MEM_LOG = 1
    MEM_SQRT = 2
    MEM_CBRT = 3


def parse_arguments():

    parser = argparse.ArgumentParser("Launch Classical ISD estimator")
    parser.add_argument('-p',
                        '--poolsize',
                        required=True,
                        type=argparse_check_positive,
                        help="Multiprocess pool size")
    parser.add_argument('--max-tasks',
                        type=argparse_check_positive,
                        help="Multiprocess max tasks per child")
    parser.add_argument('--chunksize',
                        type=argparse_check_positive,
                        default=2,
                        help="Multiprocess chunk size")
    parser.add_argument("--skip-existing",
                        action="store_true",
                        help="Skip quantum complexity files if existing")
    parser.add_argument("--out-format", choices=["txt", "bin"], default="bin")
    return parser


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
            # continue
        else:
            to_skip = False
            break
    return not to_skip


def _group_by_n_k(values):
    values_dict = collections.defaultdict(list)
    for value in values:
        key = hash(str(value.n) + '|' + str(value.r))
        values_dict[key].append(value)
    LOGGER.info("Finished grouping by n and r")
    return values_dict


def isd_compute(arg):
    # should be a list of values having same n and r
    # excluded_algorithms_by_default = [BJMMd2, BJMMd3, MayOzerovD2, MayOzerovD3]
    values_grouped = arg
    LOGGER.info(f"Computing {values_grouped}")
    skip_algos = [
        BJMM, BallCollision, BJMMdw, BJMMpdw, BJMMplus, BothMay, MayOzerov
    ] + SDEstimator.excluded_algorithms_by_default
    # skip_algos = SDEstimator.excluded_algorithms_by_default
    t0 = time.perf_counter()
    for value in values_grouped:
        # The idea is that Prange is not influenced much by the memory
        # cost, so we can compute it only once, and reuse the results later
        # prange = None
        for (mem_access, additional_skip) in (
            (MemAccess.MEM_CONST, (Prange, )),
            (MemAccess.MEM_LOG, (Prange, )),
            (MemAccess.MEM_SQRT, (Prange, )),
            (MemAccess.MEM_CBRT, (Prange, )),
        ):
            out_file = OUT_FILES_CLASSICAL_FMT.format(
                memaccess=mem_access.name,
                out_type='pkl',
                n=value.n,
                r=value.r,
                t=value.t,
                ext='pkl')
            sd = SDEstimator(value.n,
                             value.n - value.r,
                             value.t,
                             excluded_algorithms=skip_algos +
                             list(additional_skip),
                             memory_access=mem_access.value)
            results = sd.estimate()
            # This was used when Prange was still in the game
            # if mem_access == MemAccess.MEM_CONST:
            #     prange = results['Prange']
            # else:
            #     if prange is None:
            #         # prange was not computed (bcz the file was already present).
            #         # We compute only prange here and store
            #         LOGGER.info("Computing Prange for MEM_CONST")
            #         _sd = SDEstimator(
            #             value.n,
            #             value.n - value.r,
            #             value.t,
            #             # Should execute only Prange
            #             excluded_algorithms=skip_algos + [Stern, Dumer],
            #             memory_access=MemAccess.MEM_CONST)
            #         _results = _sd.estimate()
            #         prange = results['Prange']
            #         results['Prange'] = prange
            min_time = min(results.items(),
                           key=lambda algo: algo[1]['estimate']['time'])
            results['MinimumTime'] = min_time
            save_to_pickle(out_file, results)
            # save_to_pickle(out_file, min_time)
    te = time.perf_counter()
    return (values_grouped, len(values_grouped) * 4, te - t0)


def main(raw_args: Optional[list[str]] = None):
    print("#" * 80)
    init_logger(LOGGER, 'out/cisd.log')
    parser = parse_arguments()
    if raw_args and len(raw_args) != 0:
        namespace = parser.parse_args(raw_args)
    else:
        namespace = parser.parse_args()
    LOGGER.info(namespace)
    LOGGER.info("#" * 80)
    t0 = datetime.now()
    LOGGER.info(f"Starting data filtering at {t0}")

    isd_values: Sequence[Value] = load_from_pickle(ISD_VALUES_FILE_PKL)

    tot = len(isd_values) * len(MemAccess)
    LOGGER.info("#" * 80)
    LOGGER.info("Fresh start")
    LOGGER.info("#" * 80)
    LOGGER.info(f"Total points to compute (estimate): {tot}")
    LOGGER.info(f"Skip existing is: {namespace.skip_existing}")

    if namespace.skip_existing:
        no_of_files = get_no_of_files(
            OUT_FILES_CLASSICAL_TYPE_DIR,
            'pkl' if namespace.out_format == 'bin' else namespace.out_format)
        to_process_no = tot - no_of_files
        LOGGER.info(f"No. of already existing files: {no_of_files}")
        to_process_list = filter(_process_value, isd_values)
    else:
        to_process_no = tot
        to_process_list = isd_values
    # all values grouped by n and r. It improves performance bcz m4ri is
    # computed only taking into account n and n-k (that is, r).
    to_process_group_nr = _group_by_n_k(to_process_list)
    del to_process_list

    acc = 0
    t0 = datetime.now()
    LOGGER.info(f"Starting processing at {t0}")
    if namespace.poolsize == 1:
        for _, value in enumerate(to_process_group_nr.values()):
            values, computations, _ = isd_compute(value)
            acc += computations
            print(
                f"done {acc}/{to_process_no} (out of {tot}) -> {acc /to_process_no:%} ({acc /tot:%})",
                end='\r')
    else:
        with Pool(namespace.poolsize,
                  maxtasksperchild=namespace.max_tasks) as p:
            for _, result in enumerate(
                    p.imap_unordered(
                        isd_compute,
                        to_process_group_nr.values(),
                        chunksize=namespace.chunksize,
                    )):
                values, computations, time = result
                acc += computations
                print(
                    f"done {acc}/{to_process_no} (out of {tot}) -> {acc /to_process_no:%} ({acc /tot:%})",
                    end='\r')
                LOGGER.info(f"Computed {values}, real time: {time} seconds")

    te = datetime.now()
    LOGGER.info(f"Ending processing at {te}")
    LOGGER.info(f"Used: {namespace.poolsize} processes ")
    LOGGER.info(f"ISD values no: {len(isd_values)} processes ")


def test():
    prime = 48371

    r = prime
    t = 131
    skip_algos = [
        BJMM, BJMMpdw, BJMMplus, BJMMdw, BothMay, MayOzerov, BallCollision
    ]
    #skip_algos= [BJMM,BothMay]
    # skip_algos = []

    for (n0, mem_access) in itertools.product(range(4, 5), MemAccess):
        n = prime * n0
        print(f"n {n}, n-k {r}, t {t}, mem_access {mem_access.name}")
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
