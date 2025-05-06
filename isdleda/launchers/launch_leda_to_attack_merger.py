"""
"""
import csv
import os
from sys import argv
# from typing import Set

import numpy as np
from isdleda.launchers.launcher_utils import AES_LAMBDAS, OUT_DIR, QAES_LAMBDAS, get_kra1_from_leda, get_kra2_from_leda, get_kra3_from_leda, get_mra_from_leda, get_pass_counter, get_qc_reduction_mra, get_qc_reduction_kra1, get_qc_reduction_kra2, get_qc_reduction_kra3, set_pass_counter
# from isdleda.utils.common import ISDValue
from isdleda.utils.export.export import (
    from_csv_to_ledavalue,
    load_from_json,
)


def write_to_csv(filename, values):
    header = [
        'n0', 'p', 't', 'v', 'c_mra', 'q_mra', 'c_kra1', 'q_kra1', 'c_kra2',
        'q_kra2', 'c_kra3', 'q_kra3', 'c_best', 'q_best'
    ]
    with open(f"{filename}.csv", 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(values)


def check_dataset(attack_dir, isd_val, reduction, msg):
    filename = os.path.join(
        attack_dir,
        f"{isd_val.n:06}_{isd_val.n - isd_val.r:06}_{isd_val.t:03}.json")
    # print(filename)
    # continue exploring to find another minimum
    # filename = f"out/ledatools/json/{n:06}_{k:06}_{t:03}.json"
    try:
        data = load_from_json(filename)
    except:
        print(filename)
        return 0, 0

    c_time = data['Classic']['Plain']['value'] - reduction
    q_time = (data['Quantum']['Plain']['value']) * 2 - reduction
    if c_time < 0 or q_time < 0:
        print(f"{msg}")
        raise Exception(
            f"Value less than 0 for {filename}, with reduction {reduction}: {c_time}, {q_time}"
        )
    return c_time, q_time


def main():
    # the stage in which we are in
    stage = int(argv[1])
    # The directory containing the CSV files of LEDA values
    input_dir = argv[2]
    # The directory containing the json files containing ISD attacksk_dir = argv[
    attack_dir = argv[3]
    # if to check for the threshold, boolean
    check_threshold = bool(argv[4])

    output_dir = os.path.join(f"{OUT_DIR}", "isd-leda", "values", f"S{stage}")
    counter = get_pass_counter(output_dir)
    _tmp = os.path.join(output_dir, f"{counter}_leda2attack")
    # _was_existing = False
    if not os.path.exists(_tmp):
        os.mkdir(_tmp)

    missing_counter = 0

    for level_idx, level in enumerate((1, 3, 5)):
        filename_in = f"{input_dir}/cat_{level}_region"
        # filename_in = f"{OUT_DIR}/post_dfr_in/{ITERATION_IN}/cat_{level}_region"
        leda_values = from_csv_to_ledavalue(f"{filename_in}.csv")
        c_lambda = AES_LAMBDAS[int(level_idx)]
        q_lambda = QAES_LAMBDAS[int(level_idx)]
        # filename_out = f"{OUT_DIR}/post_dfr_in/{ITERATION_IN}/cat_{level}_attacks"
        filename_out = os.path.join(_tmp, f"cat_{level}_attacks")
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
            isd_val = get_mra_from_leda(leda_val)
            try:
                c_aes, q_aes = check_dataset(
                    attack_dir,
                    isd_val,
                    reduction=get_qc_reduction_mra(leda_val),
                    msg=f"MRA, {leda_val.p} {leda_val.n0} {leda_val.v}")
            except FileNotFoundError:
                missing_counter += 1
                print(f"File not found for {leda_val} and {isd_val}")
            assert c_aes is not None and q_aes is not None
            c_values.append(c_aes)
            q_values.append(q_aes)
            csv_value.append(c_aes)
            csv_value.append(q_aes)
            del isd_val

            # KRA 1
            isd_val = get_kra1_from_leda(leda_val)
            try:
                c_aes, q_aes = check_dataset(
                    attack_dir,
                    isd_val,
                    reduction=get_qc_reduction_kra1(leda_val),
                    msg=f"KRA1, {leda_val.p} {leda_val.n0} {leda_val.v}")
            except FileNotFoundError:
                missing_counter += 1
                print(f"File not found for {leda_val} and {isd_val}")
            assert c_aes is not None and q_aes is not None
            c_values.append(c_aes)
            q_values.append(q_aes)
            csv_value.append(c_aes)
            csv_value.append(q_aes)
            del isd_val

            # KRA 2
            if leda_val.n0 != 2:
                isd_val = get_kra2_from_leda(leda_val)
                try:
                    c_aes, q_aes = check_dataset(
                        attack_dir,
                        isd_val,
                        reduction=get_qc_reduction_kra2(leda_val),
                        msg=f"KRA2, {leda_val.p} {leda_val.n0} {leda_val.v}")
                except FileNotFoundError:
                    missing_counter += 1
                    print(f"File not found for {leda_val} and {isd_val}")
                assert c_aes is not None and q_aes is not None
                c_values.append(c_aes)
                q_values.append(q_aes)
                csv_value.append(c_aes)
                csv_value.append(q_aes)
            else:
                csv_value.append(np.inf)
                csv_value.append(np.inf)

            # KRA 3
            isd_val = get_kra3_from_leda(leda_val)
            try:
                c_aes, q_aes = check_dataset(
                    attack_dir,
                    isd_val,
                    reduction=get_qc_reduction_kra3(leda_val),
                    msg=f"KRA3, {leda_val.p} {leda_val.n0} {leda_val.v}")
            except FileNotFoundError:
                missing_counter += 1
                print(f"File not found for {leda_val} and {isd_val}")
            assert c_aes is not None and q_aes is not None
            c_values.append(c_aes)
            q_values.append(q_aes)
            csv_value.append(c_aes)
            csv_value.append(q_aes)

            # min c, min q, min c attack, min q attack
            min_c = min(c_values)
            min_q = min(q_values)
            if check_threshold and (min_c > .75 * c_lambda or min_q > .75 * q_lambda):
                csv_value.append(min_c)
                csv_value.append(min_q)
                csv_values.append(csv_value)

        write_to_csv(filename_out, csv_values)
    set_pass_counter(output_dir, counter + 1)
    print(f"{missing_counter} files missing")


if __name__ == '__main__':
    main()
