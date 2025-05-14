"""Launch the classical ISD estimator (CE for short) from TII
"""
import argparse
import collections
import functools
import logging
import os
import time
from datetime import datetime
from multiprocessing import Pool
from typing import Iterable, Optional, Sequence

import psutil
from cryptographic_estimators.SDEstimator import SDEstimator
from isdleda.launchers.launcher_utils import (MemAccess,
                                              argparse_check_positive,
                                              get_git_commit, get_no_of_files,
                                              init_logger)
from isdleda.utils.common import ISDValue, dict_to_isd_value
from isdleda.utils.export.export import (load_from_json, save_to_json,
                                         save_to_pickle)
from isdleda.utils.paths import OUT_DIR, OUT_FILES_PART_FMT

# BallCollision, BJMM, BJMMdw, BJMMpdw, BJMMplus, BothMay, Dumer, MayOzerov, Prange, Stern
# from cryptographic_estimators.SDEstimator import (
#     # Prange,
#     # Dumer,
#     # Stern,
#     BJMMdw,
#     MayOzerov,
#     BJMM,
#     BallCollision,
#     BJMMpdw,
#     BJMMplus,
#     BothMay,
#     )

OUT_FILES_CE_TYPE_DIR: str = os.path.join(OUT_DIR, "CE", "{ce_commit}",
                                           "{out_type}")
OUT_FILES_CE_DIR: str = os.path.join(OUT_FILES_CE_TYPE_DIR, "{memaccess}")
OUT_FILES_CE_FMT: str = os.path.join(OUT_FILES_CE_DIR, OUT_FILES_PART_FMT)

LOGGER = logging.getLogger(__name__)
LOG_DIR = "logs"
LOG_PATH = f"{LOG_DIR}/CE.log"


def parse_arguments():

    parser = argparse.ArgumentParser("Launch Classical ISD estimator")
    parser.add_argument(
        '-p',
        '--poolsize',
        default=1,
        type=argparse_check_positive,
        help="Multiprocess pool size. Default is 1 for fully sequential.")
    parser.add_argument('--max-tasks',
                        type=argparse_check_positive,
                        help="Multiprocess max tasks per child")
    parser.add_argument('--chunksize',
                        type=argparse_check_positive,
                        default=2,
                        help="Multiprocess chunk size")
    parser.add_argument("--skip-existing",
                        action="store_true",
                        help="Skip complexity files if existing")
    parser.add_argument("--out-format", choices=["pkl", "json"], default="pkl")
    parser.add_argument("--input",
                        help="Input file name containing the isd values")
    return parser


def _get_out_file(mem_access, out_type, value, file_ext, ce_commit):
    out_file = OUT_FILES_CE_FMT.format(memaccess=mem_access.name,
                                        out_type=out_type,
                                        n=value.n,
                                        k=value.k,
                                        w=value.w,
                                        ext=file_ext,
                                        ce_commit=ce_commit[:6])
    return out_file


def _process_value(value: ISDValue, out_type: str, file_ext: str,
                   ce_commit: str):
    to_skip = True
    for mem_access in (
            MemAccess.MEM_CONST,
            MemAccess.MEM_LOG,
            MemAccess.MEM_SQRT,
            MemAccess.MEM_CBRT,
    ):
        out_file = _get_out_file(mem_access, out_type, value, file_ext,
                                 ce_commit)
        if to_skip and os.path.isfile(out_file):
            LOGGER.debug(f"{out_file} already existing, skipping")
            # continue
        else:
            to_skip = False
            break
    return not to_skip


def _group_by_n_k(values: Iterable[ISDValue]):
    values_dict = collections.defaultdict(list)
    for value in values:
        key = hash(str(value.n) + '|' + str(value.k))
        values_dict[key].append(value)
    LOGGER.debug("Finished grouping by n and k")
    return values_dict


def isd_compute(arg, out_type: str, file_ext: str, ce_commit: str):
    # should be a list of values having same n and r
    # excluded_algorithms_by_default = [BJMMd2, BJMMd3, MayOzerovD2, MayOzerovD3]
    pid = os.getpid()
    process = psutil.Process(pid)
    mem_mb = process.memory_info().rss / (1024 * 1024)  # Convert to MB
    LOGGER.info(f"Starting task with PID={pid}, memory={mem_mb:.2f} MB")
    values_grouped: Sequence[ISDValue] = arg
    LOGGER.debug(f"Computing {values_grouped}")
    # skip_algos = [
    #     BJMM, BallCollision, BJMMdw, BJMMpdw, BJMMplus, BothMay, MayOzerov
    # ] + SDEstimator.excluded_algorithms_by_default
    skip_algos = SDEstimator.excluded_algorithms_by_default
    t0 = time.perf_counter()
    for value in values_grouped:
        # The idea is that Prange is not influenced much by the memory
        # cost, so we can compute it only once, and reuse the results later
        # prange = None
        for (mem_access, additional_skip) in (
            (MemAccess.MEM_CONST, ()),
            (MemAccess.MEM_LOG, ()),
            (MemAccess.MEM_SQRT, ()),
            (MemAccess.MEM_CBRT, ()),
        ):
            out_file = _get_out_file(mem_access, out_type, value, file_ext,
                                     ce_commit)
            sd = SDEstimator(value.n,
                             value.k,
                             value.w,
                             excluded_algorithms=skip_algos +
                             list(additional_skip),
                             memory_access=mem_access.value)
            results = sd.estimate()
            min_time = min(results.items(),
                           key=lambda algo: algo[1]['estimate']['time'])
            results['MinimumTime'] = min_time
            results['params'] = {
                'n': value.n,
                'k': value.k,
                'w': value.w,
                'mem': mem_access.name
            }
            match file_ext:
                case 'pkl':
                    save_to_pickle(out_file, results)
                case 'json':
                    save_to_json(out_file, results)
                case _:
                    raise Exception(f"{file_ext} saving not implemented yet")
            # save_to_pickle(out_file, min_time)
    te = time.perf_counter()
    mem_mb = process.memory_info().rss / (1024 * 1024)  # Convert to MB
    LOGGER.info(
        f"Ending task with PID={pid}, memory={mem_mb:.2f} MB, time {te - t0}")
    # return (values_grouped, len(values_grouped) * 4)
    return len(values_grouped) * 4


def main(raw_args: Optional[list[str]] = None):
    print("#" * 80)
    if not os.path.exists(LOG_DIR):
        os.mkdir(LOG_DIR)
    init_logger(LOGGER, LOG_PATH)
    parser = parse_arguments()
    if raw_args and len(raw_args) != 0:
        namespace = parser.parse_args(raw_args)
    else:
        namespace = parser.parse_args()
    LOGGER.debug(namespace)
    LOGGER.debug("#" * 80)

    #
    out_type = 'pkl' if namespace.out_format == 'bin' else namespace.out_format
    match out_type:
        case 'bin':
            file_ext = 'pkl'
        case 'pkl':
            file_ext = 'pkl'
        case 'json':
            file_ext = 'json'
        case _:
            raise AttributeError(f"Wrong value for out_type: {out_type} ")

    # t0 = datetime.now()
    # LOGGER.debug(f"Starting data filtering at {t0}")

    isd_values: Sequence[ISDValue] = [
        dict_to_isd_value(x) for x in load_from_json(namespace.input)
    ]

    tot = len(isd_values) * len(MemAccess)
    LOGGER.debug("#" * 80)
    LOGGER.debug("Fresh start")
    LOGGER.debug("#" * 80)
    LOGGER.debug(f"Total points to compute (estimate): {tot}")
    LOGGER.debug(f"Skip existing is: {namespace.skip_existing}")

    # main_commit = get_git_commit('.')
    ce_commit = get_git_commit('./submodules/cryptographic_estimators')
    print(f"CE commit: {ce_commit}")

    if namespace.skip_existing:
        no_of_files = get_no_of_files(OUT_FILES_CE_TYPE_DIR, out_type)
        to_process_no = tot - no_of_files
        filter_fun = functools.partial(
            _process_value,
            out_type=out_type,
            file_ext=file_ext,
            ce_commit=ce_commit,
        )
        LOGGER.debug(f"No. of already existing files: {no_of_files}")
        to_process_list = filter(filter_fun, isd_values)
    else:
        to_process_no = tot
        to_process_list = isd_values
    # all values grouped by n and r. It improves performance bcz m4ri is
    # computed only taking into account n and n-k (that is, r).
    to_process_group_nr = _group_by_n_k(to_process_list)
    del to_process_list

    acc = 0
    # t0 = datetime.now()
    # LOGGER.debug(f"Starting processing at {t0}")

    isd_compute_partial = functools.partial(isd_compute,
                                            out_type=out_type,
                                            file_ext=file_ext,
                                            ce_commit=ce_commit)
    print(f"Using: {namespace.poolsize} processes ")
    print(f"ISD values no: {len(isd_values)} for each MEM level")
    ts = datetime.now()
    print(ts)
    if namespace.poolsize == 1:
        for _, value in enumerate(to_process_group_nr.values()):
            computations = isd_compute_partial(value)
            acc += computations
            print(
                f"done {acc}/{to_process_no} (out of {tot}) -> {acc /to_process_no:%} ({acc /tot:%})",
                end='\r')
    else:
        with Pool(namespace.poolsize,
                  maxtasksperchild=namespace.max_tasks) as p:
            for _, result in enumerate(
                    p.imap_unordered(
                        isd_compute_partial,
                        to_process_group_nr.values(),
                        chunksize=namespace.chunksize,
                    )):
                computations = result
                acc += computations
                print(
                    f"done {acc}/{to_process_no} (out of {tot}) -> {acc /to_process_no:%} ({acc /tot:%})",
                    end='\r')
                # LOGGER.info(f"Computed {values}, real time: {time} seconds")

    te = datetime.now()
    LOGGER.info(f"Ending processing at {te}")


if __name__ == '__main__':
    main()
