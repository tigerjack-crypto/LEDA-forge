"""Given a list (in csv) of leda values, output the ISD attack list"""
import os
from multiprocessing import Manager, Pool
from sys import argv

from isdleda.launchers.launcher_utils import (OUT_DIR, get_kra1_from_leda,
                                              get_kra2_from_leda,
                                              get_kra3_from_leda,
                                              get_mra_from_leda,
                                              get_pass_counter,
                                              set_pass_counter)
from isdleda.utils.export.export import (ISDValueEncoder,
                                         from_csv_to_ledavalue, save_to_json)


def worker(level, input_dir, isd_values):
    # Modify the shared list (safe across processes)
    filename = f"{input_dir}/cat_{level}_region"
    print(f"Analayzing {filename}")
    ledavalues = from_csv_to_ledavalue(f"{filename}.csv")
    print(f"Found {len(ledavalues)} in {filename}")

    for leda_val in ledavalues:
        isd_values.append(get_mra_from_leda(leda_val))
        isd_values.append(get_kra1_from_leda(leda_val))

        # KRA 2
        if leda_val.n0 != 2:
            isd_values.append(get_kra2_from_leda(leda_val))
        isd_values.append(get_kra3_from_leda(leda_val))


def get_output_filename(output_dir, counter):
    _tmp = os.path.join(output_dir, f"{counter}_leda2isd")
    if os.path.exists(_tmp):
        print("path {_tmp} already existing")
        # if the counter is X and there's X_leda2isd, it means we still didn't
        # go beyond this pass, and we can use the same dir
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
    # /cat_{level}_region
    levels = [1, 3, 5]
    with Manager() as manager:
        isd_values = manager.list()  # This is a shared list between processes
        args = [(level, input_dir, isd_values) for level in levels]
        with Pool() as pool:
            pool.starmap(worker, args)

        print(f"{len(isd_values)} before removing duplicates")
        isd_vals = list(set(isd_values))
        del isd_values
        print(f"{len(isd_vals)} after removing duplicates")

        filename = os.path.join(_tmp, "isd_values.json")
        print(f"Output file {filename}")
        save_to_json(filename, isd_vals, cls=ISDValueEncoder)
        set_pass_counter(output_dir, counter)


if __name__ == '__main__':
    main()
