"""Given a list (in csv) of leda values, output the ISD attack list (json)"""
import argparse
import os
from itertools import chain
from multiprocessing import Pool
from typing import List

from ledaforge.launchers.launcher_utils import (
    get_kra1_from_leda, get_kra2_from_leda, get_kra3_from_leda,
    get_mra_from_leda, get_pass_counter, set_pass_counter)
from ledaforge.utils.common import ISDValue
from ledaforge.utils.export.export import (ISDValueEncoder,
                                           from_csv_to_ledavalue, save_to_json)
from ledaforge.utils.paths import OUT_DIR


def worker(level, input_dir):
    isd_values: List[ISDValue] = []
    # Modify the shared list (safe across processes)
    filename = f"{input_dir}/cat_{level}_region"
    print(f"Analayzing {filename}")
    ledavalues = from_csv_to_ledavalue(f"{filename}.csv")
    print(f"Found {len(ledavalues)} in {filename}")

    for i, leda_val in enumerate(ledavalues):
        if i % 123456 == 0:
            print(f"Level {level}: Processed {i} ledavals")
        isd_values.append(get_mra_from_leda(leda_val))
        isd_values.append(get_kra1_from_leda(leda_val))

        # KRA 2
        if leda_val.n0 != 2:
            isd_values.append(get_kra2_from_leda(leda_val))
        isd_values.append(get_kra3_from_leda(leda_val))

    print(f"Level {level}: Finished worker, processed all ledavals")
    return list(set(isd_values))


def get_output_filename(output_dir, counter):
    _tmp = os.path.join(output_dir, f"{counter}_leda2isd")
    if os.path.exists(_tmp):
        print(f"path {_tmp} already existing")
        # if the counter is X and there's X_leda2isd, it means we still didn't
        # go beyond this iteration, and we can use the same dir
    else:
        _tmp = os.path.join(output_dir, f"{counter}_leda2isd")
    if not os.path.exists(_tmp):
        os.mkdir(_tmp)
    return _tmp


def main():
    parser = argparse.ArgumentParser(
        description="Generate ISD values from LEDA values.")

    parser.add_argument("--stage",
                        "-s",
                        type=int,
                        required=True,
                        help="The stage in which we are in.")
    parser.add_argument(
        "--input-dir",
        "-i",
        type=str,
        required=True,
        help="Directory containing the CSV files of LEDA values.")
    parser.add_argument("--update-counter",
                        "-u",
                        action="store_true",
                        help="Boolean. Update the counter.txt file.")

    args = parser.parse_args()

    output_dir = os.path.join(f"{OUT_DIR}", "orchestra",
                              f"S{args.stage}")
    counter = get_pass_counter(output_dir)
    _tmp = get_output_filename(output_dir, f"{counter:03}")

    print(f"Results will be in {_tmp}")
    levels = [1, 3, 5]

    fun_args = [(level, args.input_dir) for level in levels]
    with Pool() as pool:
        results = pool.starmap(worker, fun_args)  # results is a list of lists
    all_values = list(chain.from_iterable(results))  # Native memory, fast
    print(f"{len(all_values)} before removing duplicates")
    isd_vals = list(set(all_values))
    print(f"{len(isd_vals)} after removing duplicates")

    filename = os.path.join(_tmp, "isd_values.json")
    print(f"Output file {filename}")
    save_to_json(filename, isd_vals, cls=ISDValueEncoder)
    if args.update_counter:
        set_pass_counter(output_dir, counter + 1)


if __name__ == '__main__':
    main()
