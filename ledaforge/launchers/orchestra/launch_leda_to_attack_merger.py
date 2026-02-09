"""Add c_time and q_time to LEDA parameters (p, n0, v, t).
"""
import argparse
import functools
import os
from typing import Dict, List, Tuple

import numpy as np
from ledaforge.launchers.launcher_utils import (AES_LAMBDAS, QAES_LAMBDAS,
                                                get_kra1_from_leda,
                                                get_kra2_from_leda,
                                                get_kra3_from_leda,
                                                get_mra_from_leda,
                                                get_pass_counter,
                                                get_qc_reduction_kra1,
                                                get_qc_reduction_kra2,
                                                get_qc_reduction_kra3,
                                                get_qc_reduction_mra,
                                                set_pass_counter)
from ledaforge.utils.common import Attack, ISDValue, LEDAValueAttackCost
from ledaforge.utils.export.export import (from_csv_to_ledavalue,
                                           load_from_json,
                                           save_ledavalues_attack_cost_to_csv)
from ledaforge.utils.paths import OUT_DIR


def check_dataset_LT(attack_dir: str, isd_val: ISDValue, reduction,
                     msg) -> Tuple[float, float]:
    filename = os.path.join(
        attack_dir, f"{isd_val.n:06}_{isd_val.k:06}_{isd_val.w:03}.json")

    data = load_from_json(filename)

    c_time = data['Classic']['value'] - reduction
    # compare eq. 6.6 of my phd thesis
    q_time = (data['Quantum']['value']) * 2 - reduction
    return c_time, q_time


def check_dataset_CE(mem_cost: str, attack_dir: str, isd_val: ISDValue,
                     reduction, msg) -> Tuple[float, float]:
    filename = os.path.join(
        attack_dir, f"MEM_{mem_cost}",
        f"{isd_val.n:06}_{isd_val.k:06}_{isd_val.w:03}.json")
    data = load_from_json(filename)
    c_time = data["MinimumTime"][1]["estimate"]["time"] - reduction
    q_time = np.inf
    return c_time, q_time


def check_dataset_CAT(attack_dir: str, isd_val: ISDValue, reduction,
                      msg) -> Tuple[float, float]:
    filename = os.path.join(
        attack_dir, f"{isd_val.n:06}_{isd_val.k:06}_{isd_val.w:03}.txt")
    with open(filename, 'r') as infile:
        line = infile.readline()
        value = float(line) - reduction
        return value, np.inf


def main():
    parser = argparse.ArgumentParser(
        description="Merga LEDA values with their corresponding attack values.")

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
    parser.add_argument(
        "--attack-dir",
        "-a",
        type=str,
        required=True,
        help="Directory containing the JSON files containing ISD attacks.")
    parser.add_argument("--tool",
                        "-t",
                        type=str,
                        choices=["LT", "CAT", "CE_CONST", "CE_LOG", "CE_SQRT", "CE_CBRT"],
                        required=True,
                        help="Tool used: LT, CE, or CAT.")
    parser.add_argument("--check-threshold",
                        "-c",
                        action="store_true",
                        help="Boolean. Check for lambda threshold.")
    parser.add_argument("--update-counter",
                        "-u",
                        action="store_true",
                        help="Boolean. Update the counter.txt file.")

    args = parser.parse_args()

    print(
        f"stage {args.stage}, check_threshold {args.check_threshold}, update counter {args.update_counter}"
    )

    match args.tool:
        case 'LT':
            check_dataset = check_dataset_LT
        case 'CAT':
            check_dataset = check_dataset_CAT
        case 'CE_CONST':
            check_dataset = functools.partial(check_dataset_CE, 'CONST')
        case 'CE_LOG':
            check_dataset = functools.partial(check_dataset_CE, 'LOG')
        case 'CE_SQRT':
            check_dataset = functools.partial(check_dataset_CE, 'SQRT')
        case 'CE_CBRT':
            check_dataset = functools.partial(check_dataset_CE, 'CBRT')
        case _:
            raise Exception("Wrong tool, possibles are")

    output_dir = os.path.join(f"{OUT_DIR}", "orchestra",
                              f"S{args.stage}")
    counter = get_pass_counter(output_dir)
    _tmp = os.path.join(output_dir, f"{counter:03}_leda2attack")
    # _was_existing = False
    if not os.path.exists(_tmp):
        os.mkdir(_tmp)
    print(f"output dir will be {_tmp}")

    missing_counter = 0

    for level_idx, level in enumerate((1, 3, 5)):
        filename_in = os.path.join(args.input_dir, f"cat_{level}_region")
        # filename_in = f"{OUT_DIR}/post_dfr_in/{ITERATION_IN}/cat_{level}_region"
        leda_values = from_csv_to_ledavalue(f"{filename_in}.csv")
        print(f"found {len(leda_values)} in {filename_in}")
        c_lambda = AES_LAMBDAS[int(level_idx)]
        q_lambda = QAES_LAMBDAS[int(level_idx)]
        # filename_out = f"{OUT_DIR}/post_dfr_in/{ITERATION_IN}/cat_{level}_attacks"
        filename_out = os.path.join(_tmp, f"cat_{level}_attacks_{args.tool}")
        leda_values_to_attacks: List[LEDAValueAttackCost] = []

        for leda_val in leda_values:
            # csv_value = []
            c_costs: Dict[Attack, float] = {}
            q_costs: Dict[Attack, float] = {}

            # MRA
            isd_val = get_mra_from_leda(leda_val)
            try:
                c_aes, q_aes = check_dataset(
                    args.attack_dir,
                    isd_val,
                    reduction=get_qc_reduction_mra(leda_val),
                    msg=f"MRA, {leda_val.p} {leda_val.n0} {leda_val.v}")
            except FileNotFoundError as e:
                missing_counter += 1
                print(f"File not found for {leda_val} and {isd_val}\n{e}")
                continue
            if c_aes is None:
                # at least c_aes present, q_aes is only from LT
                print(f"Value not found for {leda_val} and {isd_val}")
                missing_counter += 1
                c_aes, q_aes = np.inf, np.inf
            assert c_aes is not None and q_aes is not None
            c_costs[Attack.MsgR] = c_aes
            q_costs[Attack.MsgR] = q_aes
            del isd_val
            # print("MRA over")

            # KRA 1
            isd_val = get_kra1_from_leda(leda_val)
            try:
                c_aes, q_aes = check_dataset(
                    args.attack_dir,
                    isd_val,
                    reduction=get_qc_reduction_kra1(leda_val),
                    msg=f"KRA1, {leda_val.p} {leda_val.n0} {leda_val.v}")
            except FileNotFoundError:
                missing_counter += 1
                print(f"File not found for {leda_val} and {isd_val}\n{e}")
                c_aes, q_aes = np.inf, np.inf
            assert c_aes is not None and q_aes is not None
            c_costs[Attack.KeyR1] = c_aes
            q_costs[Attack.KeyR1] = q_aes
            del isd_val, c_aes, q_aes
            # print("KRA1 over")

            # KRA 2
            if leda_val.n0 != 2:
                isd_val = get_kra2_from_leda(leda_val)
                try:
                    c_aes, q_aes = check_dataset(
                        args.attack_dir,
                        isd_val,
                        reduction=get_qc_reduction_kra2(leda_val),
                        msg=f"KRA2, {leda_val.p} {leda_val.n0} {leda_val.v}")
                except FileNotFoundError:
                    missing_counter += 1
                    print(f"File not found for {leda_val} and {isd_val}\n{e}")
                    c_aes, q_aes = np.inf, np.inf
                assert c_aes is not None and q_aes is not None
            else:
                c_aes = np.inf
                q_aes = np.inf
            c_costs[Attack.KeyR2] = c_aes
            q_costs[Attack.KeyR2] = q_aes
            # print("KRA2 over")

            # KRA 3
            isd_val = get_kra3_from_leda(leda_val)
            try:
                c_aes, q_aes = check_dataset(
                    args.attack_dir,
                    isd_val,
                    reduction=get_qc_reduction_kra3(leda_val),
                    msg=f"KRA3, {leda_val.p} {leda_val.n0} {leda_val.v}")
            except FileNotFoundError:
                missing_counter += 1
                print(f"File not found for {leda_val} and {isd_val}\n{e}")
                c_aes, q_aes = np.inf, np.inf
            assert c_aes is not None and q_aes is not None
            c_costs[Attack.KeyR3] = c_aes
            q_costs[Attack.KeyR3] = q_aes
            # print("KRA3 over")

            # min c, min q, min c attack, min q attack
            min_c = min(c_costs.items(), key=lambda x: x[1])
            min_q = min(q_costs.items(), key=lambda x: x[1])
            if (args.check_threshold and (min_c[1] > .75 * c_lambda
                                         and min_q[1] > .75 * q_lambda)) or not args.check_threshold:
                lvac = LEDAValueAttackCost(leda_val, c_costs, q_costs, min_c,
                                           min_q)
                leda_values_to_attacks.append(lvac)

        save_ledavalues_attack_cost_to_csv(leda_values_to_attacks,
                                           filename_out)
        # write_to_csv(filename_out, csv_values)
    if args.update_counter:
        set_pass_counter(output_dir, counter + 1)
    print(f"{missing_counter} files missing")


if __name__ == '__main__':
    main()
