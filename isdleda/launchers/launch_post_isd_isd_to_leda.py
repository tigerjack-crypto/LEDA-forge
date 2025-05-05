"""It's just the restriction routine, but tailored for the new data format.
It should be merged with the restriction one.
"""
import csv
import os
from typing import Set

import numpy as np
from isdleda.launchers.launcher_utils import AES_LAMBDAS, OUT_DIR, QAES_LAMBDAS
from isdleda.utils.common import ISDValue
from isdleda.utils.export.export import (
    from_csv_to_ledavalue,
    load_from_json,
)

# the 0-th time this is launched
ITERATION_IN = "0"
ITERATION_OUT = "1_BJMM"

DATA_SET = os.path.join(OUT_DIR, "LT", "results", "json")
isd_values_to_compute: Set[ISDValue] = set()
# isd_values: List[ISDValue] = []


def write_to_csv(filename, values):
    header = [
        'n0', 'p', 't', 'v', 'c_mra', 'q_mra', 'c_kra1', 'q_kra1', 'c_kra2',
        'q_kra2', 'c_kra3', 'q_kra3', 'c_best', 'q_best'
    ]
    with open(f"{filename}.csv", 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(values)


def process():
    for level_idx, level in enumerate((1, 3, 5)):
        filename_in = f"{OUT_DIR}/post_dfr_in/{ITERATION_IN}/cat_{level}_region"
        leda_values = from_csv_to_ledavalue(f"{filename_in}.csv")
        c_lambda = AES_LAMBDAS[int(level_idx)]
        q_lambda = QAES_LAMBDAS[int(level_idx)]
        filename_out = f"{OUT_DIR}/post_dfr_in/{ITERATION_IN}/cat_{level}_attacks"
        csv_values = []

        for leda_val in leda_values:
            c_values = []
            q_values = []

            csv_value = []
            csv_value.append(leda_val.n0)
            csv_value.append(leda_val.p)
            csv_value.append(leda_val.v)
            csv_value.append(leda_val.t)

            # MRA
            n = leda_val.p * leda_val.n0
            k = leda_val.p * (leda_val.n0 - 1)
            t = leda_val.t
            c_aes, q_aes, _ = check_dataset(
                n=n,
                k=k,
                t=t,
                c_lambda=c_lambda,
                q_lambda=q_lambda,
                reduction=np.log2(leda_val.p) / 2,
                msg=f"MRA, {leda_val.p} {leda_val.n0} {leda_val.v}")
            assert c_aes is not None and q_aes is not None
            c_values.append(c_aes)
            q_values.append(q_aes)
            csv_value.append(c_aes)
            csv_value.append(q_aes)
            del n, k, t

            # KRA 1
            n = leda_val.p * leda_val.n0  #
            k = leda_val.p * (leda_val.n0 - 1)  #
            t = leda_val.v * 2
            c_aes, q_aes, _ = check_dataset(
                n=n,
                k=k,
                t=t,
                c_lambda=c_lambda,
                q_lambda=q_lambda,
                reduction=np.log2(leda_val.p) + np.log2(leda_val.n0) +
                np.log2(leda_val.n0 - 1) - 1,
                msg=f"KRA1, {leda_val.p} {leda_val.n0} {leda_val.v}")
            assert c_aes is not None and q_aes is not None
            c_values.append(c_aes)
            q_values.append(q_aes)
            csv_value.append(c_aes)
            csv_value.append(q_aes)
            del n, k, t

            # KRA 2
            if leda_val.n0 != 2:
                n = 2 * leda_val.p
                k = leda_val.p
                t = leda_val.v * 2
                c_aes, q_aes, _ = check_dataset(
                    n=n,
                    k=k,
                    t=t,
                    c_lambda=c_lambda,
                    q_lambda=q_lambda,
                    reduction=np.log2(leda_val.p) + np.log2(leda_val.n0),
                    msg=f"KRA2, {leda_val.p} {leda_val.n0} {leda_val.v}")
                assert c_aes is not None and q_aes is not None
                c_values.append(c_aes)
                q_values.append(q_aes)
                csv_value.append(c_aes)
                csv_value.append(q_aes)
                del n, k, t
            else:
                csv_value.append(np.inf)
                csv_value.append(np.inf)

            # KRA 3
            n = leda_val.p * leda_val.n0
            k = leda_val.p
            t = leda_val.v * leda_val.n0
            c_aes, q_aes, _ = check_dataset(
                n=n,
                k=k,
                t=t,
                c_lambda=c_lambda,
                q_lambda=q_lambda,
                reduction=np.log2(leda_val.p),
                msg=f"KRA3, {leda_val.p} {leda_val.n0} {leda_val.v}")
            assert c_aes is not None and q_aes is not None
            c_values.append(c_aes)
            q_values.append(q_aes)
            csv_value.append(c_aes)
            csv_value.append(q_aes)
            del n, k, t

            # min c, min q, min c attack, min q attack
            min_c = min(c_values)
            min_q = min(q_values)
            csv_value.append(min_c)
            csv_value.append(min_q)
            csv_values.append(csv_value)

            write_to_csv(filename_out, csv_values)


def check_dataset(n, k, t, c_lambda, q_lambda, reduction, msg):
    filename = os.path.join(OUT_DIR, "LT", "results", "json",
                            "BJMM",
                            f"{n:06}_{k:06}_{t:03}.json")
    print(filename)
    # continue exploring to find another minimum
    # filename = f"out/ledatools/json/{n:06}_{k:06}_{t:03}.json"
    less_than_threshold = False
    data = load_from_json(filename)

    c_time = data['Classic']['Plain']['value'] - reduction
    q_time = (data['Quantum']['Plain']['value']) * 2 - reduction
    if c_time < 0 or q_time < 0:
        print(f"{msg}")
        raise Exception(
            f"Value less than 0 for {filename}, with reduction {reduction}: {c_time}, {q_time}"
        )
    if c_time < .8 * c_lambda or q_time < .75 * q_lambda:
        less_than_threshold = True
    return c_time, q_time, less_than_threshold


def main():
    print("Processing merged values")
    process()


if __name__ == '__main__':
    main()
