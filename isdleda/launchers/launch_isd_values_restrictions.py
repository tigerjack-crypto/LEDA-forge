"""It seems to be the working one"""
import os
from collections import defaultdict
from typing import Dict, List, Set

import numpy as np
from isdleda.launchers.launcher_utils import AES_LAMBDAS, QAES_LAMBDAS
from isdleda.utils.common import ISDValue, LEDAValue, dict_to_leda_value
from isdleda.utils.export.export import (ISDValueEncoder, LEDAValueEncoder,
                                         ledavalue_decoder, load_from_json,
                                         save_to_json)


# level -> p_n0; all values have t != -1, v == -1
# level -> p_n0; all values have v != -1, t == -1
def merge_values(
    leda_values_t: Dict[int, Dict[str, List[LEDAValue]]],
    leda_values_v: Dict[int, Dict[str, List[LEDAValue]]],
) -> Dict[int, List[LEDAValue]]:
    leda_values_merged: Dict[int, Set[LEDAValue]] = defaultdict(set)
    # Dict[level_idx: str, Dict[p_n0: str, List[LEDAValue]]]
    for level_idx, leda_vals_t_by_p_n0 in leda_values_t.items():
        # p_n0 is the hash of p_n0
        for p_n0, leda_vals_t in leda_vals_t_by_p_n0.items():
            # the list of leda values for which only t is defined
            for leda_val_t in leda_vals_t:
                for leda_val_v in leda_values_v[level_idx][p_n0]:
                    leda_val_tt = dict_to_leda_value(leda_val_t)
                    leda_val_vv = dict_to_leda_value(leda_val_v)
                    leda_val = LEDAValue(leda_val_tt.p, leda_val_tt.n0,
                                         leda_val_tt.t, leda_val_vv.v)
                    assert leda_val.t != -1 and leda_val.v != -1, "Something is wrong"
                    leda_values_merged[int(level_idx)].add(leda_val)

    leda_values_merged_l = {
        level_idx: list(leda_vals)
        for level_idx, leda_vals in leda_values_merged.items()
    }
    return leda_values_merged_l


def process_merged(leda_values_merged: Dict[int, List[LEDAValue]]):
    # set is useless here, the merged list doesn't have duplicates
    leda_values_ok: Dict[int, List[LEDAValue]] = defaultdict(list)
    # how many values passed the different level (MRA, KRA1, KRA2, KRA3) and the final check
    passing = [0, 0, 0, 0, 0]

    isd_values_ok: Set[ISDValue] = set()
    isd_values_to_compute: Set[ISDValue] = set()
    # level idx is (0, 1, 2)
    for level_idx, leda_values in leda_values_merged.items():
        c_lambda = AES_LAMBDAS[int(level_idx)]
        q_lambda = QAES_LAMBDAS[int(level_idx)]
        for leda_val in leda_values:
            print(f"{passing}", end="\r")
            c_complexities = [leda_val.p * leda_val.n0] * 4
            q_complexities = [leda_val.p * leda_val.n0] * 4
            isd_vals_maybe_ok = []

            # MRA
            n = leda_val.p * leda_val.n0
            k = leda_val.p * (leda_val.n0 - 1)
            t = leda_val.t
            c_aes, q_aes, less_than_threshold = check_dataset(
                n=n,
                k=k,
                t=t,
                c_lambda=c_lambda,
                q_lambda=q_lambda,
                reduction=np.log2(leda_val.p) / 2,
                msg=f"MRA, {leda_val.p} {leda_val.n0} {leda_val.v}")
            if (c_aes is None or q_aes is None):
                isd_values_to_compute.add(ISDValue(n, n - k, t))
                continue
            if less_than_threshold:
                continue

            passing[0] += 1
            c_complexities[0] = c_aes
            q_complexities[0] = q_aes
            isd_vals_maybe_ok.append(ISDValue(n, n - k, t))
            del n, k, t

            # KRA 1
            n = leda_val.p * leda_val.n0  #
            k = leda_val.p * (leda_val.n0 - 1)  #
            t = leda_val.v * 2
            c_aes, q_aes, less_than_threshold = check_dataset(
                n=n,
                k=k,
                t=t,
                c_lambda=c_lambda,
                q_lambda=q_lambda,
                reduction=np.log2(leda_val.p) + np.log2(leda_val.n0) +
                np.log2(leda_val.n0 - 1) - 1,
                msg=f"KRA1, {leda_val.p} {leda_val.n0} {leda_val.v}")
            if (c_aes is None or q_aes is None):
                isd_values_to_compute.add(ISDValue(n, n - k, t))
                continue
            if less_than_threshold:
                continue
            passing[1] += 1
            c_complexities[1] = c_aes
            q_complexities[1] = q_aes
            isd_vals_maybe_ok.append(ISDValue(n, n - k, t))
            del n, k, t

            # KRA 2
            if leda_val.n0 != 2:
                n = 2 * leda_val.p
                k = leda_val.p
                t = leda_val.v * 2
                c_aes, q_aes, less_than_threshold = check_dataset(
                    n=n,
                    k=k,
                    t=t,
                    c_lambda=c_lambda,
                    q_lambda=q_lambda,
                    reduction=np.log2(leda_val.p) + np.log2(leda_val.n0),
                    msg=f"KRA2, {leda_val.p} {leda_val.n0} {leda_val.v}")
                if (c_aes is None or q_aes is None):
                    isd_values_to_compute.add(ISDValue(n, n - k, t))
                    continue
                if less_than_threshold:
                    continue
                passing[2] += 1
                c_complexities[2] = c_aes
                q_complexities[2] = q_aes
                isd_vals_maybe_ok.append(ISDValue(n, n - k, t))
                del n, k, t

            # KRA 3
            n = leda_val.p * leda_val.n0
            k = leda_val.p
            t = leda_val.v * leda_val.n0
            c_aes, q_aes, less_than_threshold = check_dataset(
                n=n,
                k=k,
                t=t,
                c_lambda=c_lambda,
                q_lambda=q_lambda,
                reduction=np.log2(leda_val.p),
                msg=f"KRA3, {leda_val.p} {leda_val.n0} {leda_val.v}")
            if (c_aes is None or q_aes is None):
                isd_values_to_compute.add(ISDValue(n, n - k, t))
                continue
            if less_than_threshold:
                continue

            passing[3] += 1
            c_complexities[3] = c_aes
            q_complexities[3] = q_aes
            isd_vals_maybe_ok.append(ISDValue(n, n - k, t))

            # min c, min q, min c attack, min q attack
            min_c = np.inf
            min_q = np.inf
            min_c_attack = None
            min_q_attack = None
            for c_compl, q_compl, c_attack, q_attack in zip(
                    c_complexities, q_complexities,
                ("MRA", "KRA1", "KRA2", "KRA3"),
                ("MRA", "KRA1", "KRA2", "KRA3")):
                if c_compl < min_c:
                    min_c = c_compl
                    min_c_attack = c_attack
                if q_compl < min_q:
                    min_q = q_compl
                    min_q_attack = q_attack
            if is_inside(min_c, min_q, c_lambda, q_lambda):
                passing[4] += 1
                leda_val.msgs.extend([
                    f"MIN C: {min_c} attack: {min_c_attack}, MIN Q:{min_q} attack: {min_q_attack}"
                ])
    return leda_values_ok, passing, list(isd_values_ok), list(isd_values_to_compute)


def check_dataset(n, k, t, c_lambda, q_lambda, reduction, msg):
    filename = f"out/ledatools/json/{n:06}_{k:06}_{t:03}.json"
    # continue exploring to find another minimum
    less_than_threshold = False
    try:
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
    except FileNotFoundError:
        return None, None, True


def is_inside(c_time, q_time, c_lambda, q_lambda):
    if .8 * c_lambda <= c_time <= 1.2 * c_lambda:
        if .75 * q_lambda <= q_time <= 1.25 * q_lambda:
            return True
        else:
        #     # TODO Idea here is to detect quantum bounds
            return False
    return False


def main():
    skip_if_exists = False
    filename_merged = os.path.join("out", "values", "from_restrictions3",
                                   "leda_values_merged.json")
    if skip_if_exists and os.path.isfile(filename_merged):
        print("Loading already merged values")
        leda_values_merged = load_from_json(filename_merged,
                                            object_hook=ledavalue_decoder)
    else:
        print("Loading t values")
        filename = os.path.join("out", "values", "from_generation_3",
                                "leda_values_t.json")
        leda_values_t_by_level = load_from_json(filename)

        print("Loading v values")
        filename = os.path.join("out", "values", "from_generation_3",
                                "leda_values_v.json")
        leda_values_v_by_level = load_from_json(filename)

        print("Merging values")
        leda_values_merged = merge_values(
            leda_values_t_by_level,
            leda_values_v_by_level,
        )

        print("Saving merged values to json")
        save_to_json(filename_merged, leda_values_merged, cls=LEDAValueEncoder)

    print("Processing merged values")
    leda_vals_ok, passing_at_step, isd_values_ok, isd_values_to_compute = process_merged(
        leda_values_merged)
    print(f"Passings each step {passing_at_step}")

    filename = os.path.join("out", "values", "from_restrictions_3",
                            "leda_values_")
    print(f"Saving leda vals")
    for level, item in zip((1, 3, 5), leda_vals_ok.items()):
        _, leda_vals = item
        filename_level = filename + f"L{level}.json"
        print(f"Saving leda vals for {level}")
        save_to_json(filename_level, leda_vals, cls=LEDAValueEncoder)

    print(f"Saving isd vals ok {len(isd_values_ok)}")
    filename = os.path.join("out", "values", "from_restrictions_3",
                            "isd_values.json")
    isd_vals = sorted(isd_values_ok)
    save_to_json(filename, isd_vals, cls=ISDValueEncoder)

    print(f"Saving isd vals to compute {len(isd_values_to_compute)}")
    filename = os.path.join("out", "values", "from_restrictions_3",
                            "isd_values_to_compute.json")
    isd_vals = sorted(set(isd_values_to_compute))
    save_to_json(filename, isd_vals, cls=ISDValueEncoder)


if __name__ == '__main__':
    main()
