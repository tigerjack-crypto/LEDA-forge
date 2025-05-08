"""Given a list (in csv) of leda values, output the ISD attack list"""
import os
from itertools import chain
from multiprocessing import Pool
from sys import argv
from typing import List

from isdleda.launchers.launcher_utils import (
    OUT_DIR, get_kra1_from_leda, get_kra2_from_leda, get_kra3_from_leda,
    get_mra_from_leda, get_pass_counter, set_pass_counter)
from isdleda.utils.common import ISDValue
from isdleda.utils.export.export import (ISDValueEncoder,
                                         from_csv_to_ledavalue, save_to_json)


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
    print(f"Level {level}: Finished worker")
    return list(set(isd_values))


def get_output_filename(output_dir, counter):
    _tmp = os.path.join(output_dir, f"{counter}_leda2isd")
    if os.path.exists(_tmp):
        print(f"path {_tmp} already existing")
        # if the counter is X and there's X_leda2isd, it means we still didn't
        # go beyond this iteration, and we can use the same dir
    else:
        counter += 1
        _tmp = os.path.join(output_dir, f"{counter}_leda2isd")
    if not os.path.exists(_tmp):
        os.mkdir(_tmp)
    return _tmp


def main():
    stage = argv[1]  # the stage in which we are in
    input_dir = argv[2]  # The directory containing the CSV files

    output_dir = os.path.join(f"{OUT_DIR}", "isd-leda", "values", f"S{stage}")
    counter = get_pass_counter(output_dir)
    _tmp = get_output_filename(output_dir, counter)

    print(f"Results will be in {_tmp}")
    levels = [1, 3, 5]

    args = [(level, input_dir) for level in levels]
    with Pool() as pool:
        results = pool.starmap(worker, args)  # results is a list of lists
    all_values = list(chain.from_iterable(results))  # Native memory, fast
    print(f"{len(all_values)} before removing duplicates")
    isd_vals = list(set(all_values))
    print(f"{len(isd_vals)} after removing duplicates")

    filename = os.path.join(_tmp, "isd_values.json")
    print(f"Output file {filename}")
    save_to_json(filename, isd_vals, cls=ISDValueEncoder)
    set_pass_counter(output_dir, counter)


if __name__ == '__main__':
    main()
