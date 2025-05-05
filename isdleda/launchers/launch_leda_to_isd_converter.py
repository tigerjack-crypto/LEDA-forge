"""Given a list (in csv) of leda values, output the ISD attack list"""

import os
from sys import argv
from typing import List

from isdleda.launchers.launcher_utils import get_pass_counter, OUT_DIR, set_pass_counter
from isdleda.utils.common import ISDValue
from isdleda.utils.export.export import (ISDValueEncoder,
                                         from_csv_to_ledavalue, save_to_json)


def main():
    stage = argv[1]  # the stage in which we are in
    input_dir = argv[2]  # The directory containing the CSV files
    output_dir = os.path.join(f"{OUT_DIR}", "isd-leda", "values", f"S{stage}")
    # /cat_{level}_region
    isd_values: List[ISDValue] = []
    for level in (1, 3, 5):
        filename = f"{input_dir}/cat_{level}_region"
        print(f"Analayzing {filename}")
        ledavalues = from_csv_to_ledavalue(f"{filename}.csv")

        for leda_val in ledavalues:
            # MRA
            n = leda_val.p * leda_val.n0
            k = leda_val.p * (leda_val.n0 - 1)
            t = leda_val.t
            isd_values.append(ISDValue(n, n - k, t, msgs=[f"MRA"]))

            # KRA 1
            n = leda_val.p * leda_val.n0  #
            k = leda_val.p * (leda_val.n0 - 1)  #
            t = leda_val.v * 2
            isd_values.append(ISDValue(n, n - k, t, msgs=[f"KRA 1"]))

            # KRA 2
            if leda_val.n0 != 2:
                n = 2 * leda_val.p
                k = leda_val.p
                t = leda_val.v * 2
                isd_values.append(ISDValue(n, n - k, t, msgs=[f"KRA 2"]))

            # KRA 3
            n = leda_val.p * leda_val.n0
            k = leda_val.p
            t = leda_val.v * leda_val.n0

            isd_values.append(ISDValue(n, n - k, t, msgs=[f"KRA 3"]))

    print(len(isd_values))
    counter = get_pass_counter(output_dir)
    _tmp =  os.path.join(output_dir, f"{counter}_leda2isd")
    if os.path.exists(_tmp):
        print("path {_tmp} already existing")
        # if the counter is X and there's X_leda2isd, it means we still didn't
        # go beyond this pass, and we can use the same dir
        pass
    else:
        counter += 1
        _tmp =  os.path.join(output_dir, f"{counter}_leda2isd")
    filename = os.path.join(_tmp, "isd_values.json")
    print(f"Output file {filename}")
    save_to_json(filename, isd_values, cls=ISDValueEncoder)
    set_pass_counter(output_dir, counter)


if __name__ == '__main__':
    main()
