"""Add c_time and q_time to LEDA parameters (p, n0, v, t).
"""
import csv
import os
from sys import argv
from typing import Dict, List, Tuple

import numpy as np
from isdleda.launchers.launcher_utils import (
    AES_LAMBDAS, QAES_LAMBDAS, get_kra1_from_leda, get_kra2_from_leda,
    get_kra3_from_leda, get_mra_from_leda, get_pass_counter,
    get_qc_reduction_kra1, get_qc_reduction_kra2, get_qc_reduction_kra3,
    get_qc_reduction_mra, set_pass_counter)
from isdleda.utils.common import Attack, ISDValue, LEDAValueAttackCost
from isdleda.utils.export.export import (from_csv_to_ledavalue, load_from_json,
                                         save_ledavalues_attack_cost_to_csv)
from isdleda.utils.paths import OUT_DIR

# from typing import Set


def write_to_csv(filename, values):
    with open(f"{filename}.csv", 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(values)


def check_dataset(attack_dir: str, isd_val: ISDValue, reduction,
                  msg) -> Tuple[float, float]:
    filename = os.path.join(
        attack_dir, f"{isd_val.n:06}_{isd_val.k:06}_{isd_val.w:03}.json")
    # print(filename)
    # continue exploring to find another minimum
    # filename = f"out/ledatools/json/{n:06}_{k:06}_{t:03}.json"
    try:
        data = load_from_json(filename)
    except:
        print(f"{filename} not found")
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
    print(f"stage {stage}, check_threshold {check_threshold}")

    output_dir = os.path.join(f"{OUT_DIR}", "isd-leda", "values", f"S{stage}")
    counter = get_pass_counter(output_dir)
    _tmp = os.path.join(output_dir, f"{counter}_leda2attack")
    # _was_existing = False
    if not os.path.exists(_tmp):
        os.mkdir(_tmp)
    print(f"output dir will be {_tmp}")

    missing_counter = 0

    for level_idx, level in enumerate((1, 3, 5)):
        filename_in = f"{input_dir}/cat_{level}_region"
        # filename_in = f"{OUT_DIR}/post_dfr_in/{ITERATION_IN}/cat_{level}_region"
        leda_values = from_csv_to_ledavalue(f"{filename_in}.csv")
        print(f"found {len(leda_values)} in {filename_in}")
        c_lambda = AES_LAMBDAS[int(level_idx)]
        q_lambda = QAES_LAMBDAS[int(level_idx)]
        # filename_out = f"{OUT_DIR}/post_dfr_in/{ITERATION_IN}/cat_{level}_attacks"
        filename_out = os.path.join(_tmp, f"cat_{level}_attacks")
        leda_values_to_attacks: List[LEDAValueAttackCost] = []

        for leda_val in leda_values:
            # csv_value = []
            c_costs: Dict[Attack, float] = {}
            q_costs: Dict[Attack, float] = {}

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
                c_aes, q_aes = np.inf, np.inf
            assert c_aes is not None and q_aes is not None
            c_costs[Attack.MsgR] = c_aes
            q_costs[Attack.MsgR] = q_aes
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
                c_aes, q_aes = np.inf, np.inf
            assert c_aes is not None and q_aes is not None
            c_costs[Attack.KeyR1] = c_aes
            q_costs[Attack.KeyR1] = q_aes
            del isd_val, c_aes, q_aes

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
                    c_aes, q_aes = np.inf, np.inf
                assert c_aes is not None and q_aes is not None
            else:
                c_aes = np.inf
                q_aes = np.inf
            c_costs[Attack.KeyR2] = c_aes
            q_costs[Attack.KeyR2] = q_aes

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
                c_aes, q_aes = np.inf, np.inf
            assert c_aes is not None and q_aes is not None
            c_costs[Attack.KeyR3] = c_aes
            q_costs[Attack.KeyR3] = q_aes

            # min c, min q, min c attack, min q attack
            min_c = min(c_costs.items(), key=lambda x: x[1])
            min_q = min(q_costs.items(), key=lambda x: x[1])
            if check_threshold and (min_c[1] > .75 * c_lambda
                                    or min_q[1] > .75 * q_lambda):
                lvac = LEDAValueAttackCost(leda_val, c_costs, q_costs, min_c,
                                           min_q)
                leda_values_to_attacks.append(lvac)

        save_ledavalues_attack_cost_to_csv(leda_values_to_attacks,
                                           filename_out)
        # write_to_csv(filename_out, csv_values)
    set_pass_counter(output_dir, counter + 1)
    print(f"{missing_counter} files missing")


if __name__ == '__main__':
    main()
