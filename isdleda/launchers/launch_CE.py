"""Launch the classical ISD estimator from TII
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

# BallCollision, BJMM, BJMMdw, BJMMpdw, BJMMplus, BothMay, Dumer, MayOzerov, Prange, Stern
from cryptographic_estimators.SDEstimator import MayOzerov  # Prange,
from cryptographic_estimators.SDEstimator import (BJMM, BallCollision, BJMMdw,
                                                  BJMMpdw, BJMMplus, BothMay,
                                                  SDEstimator)
from isdleda.launchers.launcher_utils import (MemAccess,
                                              argparse_check_positive,
                                              get_no_of_files, init_logger)
from isdleda.utils.common import ISDValue, dict_to_isd_value
from isdleda.utils.export.export import (load_from_json, save_to_json,
                                         save_to_pickle)
from isdleda.utils.paths import (ISD_VALUES_FILE_JSON, OUT_FILES_CEB_FMT,
                                 OUT_FILES_CEB_TYPE_DIR)

LOGGER = logging.getLogger(__name__)


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
                        help="Skip quantum complexity files if existing")
    parser.add_argument("--out-format", choices=["pkl", "json"], default="pkl")
    return parser


def _process_value(value: ISDValue, out_type: str, file_ext: str):
    to_skip = True
    for mem_access in (
            MemAccess.MEM_CONST,
            MemAccess.MEM_LOG,
            MemAccess.MEM_SQRT,
            MemAccess.MEM_CBRT,
    ):
        out_file = OUT_FILES_CEB_FMT.format(memaccess=mem_access.name,
                                            out_type=out_type,
                                            n=value.n,
                                            r=value.r,
                                            t=value.t,
                                            ext=file_ext)
        if to_skip and os.path.isfile(out_file):
            LOGGER.info(f"{out_file} already existing, skipping")
            # continue
        else:
            to_skip = False
            break
    return not to_skip


def _group_by_n_k(values: Iterable[ISDValue]):
    values_dict = collections.defaultdict(list)
    for value in values:
        key = hash(str(value.n) + '|' + str(value.r))
        values_dict[key].append(value)
    LOGGER.info("Finished grouping by n and r")
    return values_dict


def isd_compute(arg, out_type: str, file_ext: str):
    # should be a list of values having same n and r
    # excluded_algorithms_by_default = [BJMMd2, BJMMd3, MayOzerovD2, MayOzerovD3]
    values_grouped: Sequence[ISDValue] = arg
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
            (MemAccess.MEM_CONST, ()),
            (MemAccess.MEM_LOG, ()),
            (MemAccess.MEM_SQRT, ()),
            (MemAccess.MEM_CBRT, ()),
        ):
            out_file = OUT_FILES_CEB_FMT.format(memaccess=mem_access.name,
                                                out_type=out_type,
                                                n=value.n,
                                                k=value.n - value.r,
                                                t=value.t,
                                                ext=file_ext)
            sd = SDEstimator(value.n,
                             value.n - value.r,
                             value.t,
                             excluded_algorithms=skip_algos +
                             list(additional_skip),
                             memory_access=mem_access.value)
            results = sd.estimate()
            min_time = min(results.items(),
                           key=lambda algo: algo[1]['estimate']['time'])
            results['MinimumTime'] = min_time
            results['params'] = {
                'n': value.n,
                'r': value.r,
                'k': value.n - value.r,
                't': value.t,
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
    return (values_grouped, len(values_grouped) * 4, te - t0)


def main(raw_args: Optional[list[str]] = None):
    print("#" * 80)
    init_logger(LOGGER, 'logs/cisd.log')
    parser = parse_arguments()
    if raw_args and len(raw_args) != 0:
        namespace = parser.parse_args(raw_args)
    else:
        namespace = parser.parse_args()
    LOGGER.info(namespace)
    LOGGER.info("#" * 80)

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

    t0 = datetime.now()
    LOGGER.info(f"Starting data filtering at {t0}")

    isd_values: Sequence[ISDValue] = [
        dict_to_isd_value(x) for x in load_from_json(ISD_VALUES_FILE_JSON)
    ]

    tot = len(isd_values) * len(MemAccess)
    LOGGER.info("#" * 80)
    LOGGER.info("Fresh start")
    LOGGER.info("#" * 80)
    LOGGER.info(f"Total points to compute (estimate): {tot}")
    LOGGER.info(f"Skip existing is: {namespace.skip_existing}")

    if namespace.skip_existing:
        no_of_files = get_no_of_files(OUT_FILES_CEB_TYPE_DIR, out_type)
        to_process_no = tot - no_of_files
        filter_fun = functools.partial(_process_value,
                                       out_type=out_type,
                                       file_ext=file_ext)
        LOGGER.info(f"No. of already existing files: {no_of_files}")
        to_process_list = filter(filter_fun, isd_values)
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

    isd_compute_partial = functools.partial(isd_compute,
                                            out_type=out_type,
                                            file_ext=file_ext)
    if namespace.poolsize == 1:
        for _, value in enumerate(to_process_group_nr.values()):
            values, computations, _ = isd_compute_partial(value)
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


if __name__ == '__main__':
    main()
