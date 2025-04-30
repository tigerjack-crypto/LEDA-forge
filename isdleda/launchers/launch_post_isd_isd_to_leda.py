"""It's just the restriction routine, but tailored for the new data format.
It should be merged with the restriction one.
"""
import os
from collections import defaultdict
from typing import Dict, List, Set

import numpy as np
from isdleda.launchers.launcher_utils import AES_LAMBDAS, OUT_DIR, QAES_LAMBDAS
from isdleda.utils.common import ISDValue, LEDAValue
from isdleda.utils.export.export import (ISDValueEncoder, LEDAValueEncoder,
                                         from_csv_to_ledavalue, load_from_json,
                                         save_to_json)

# the 0-th time this is launched
ITERATION = "1_BJMM"

DATA_SET = os.path.join(OUT_DIR, "LT", "results", "json")
isd_values_to_compute: Set[ISDValue] = set()
# isd_values: List[ISDValue] = []



def process():
    # set is useless here, the merged list doesn't have duplicates
    leda_values_ok: Dict[int, List[LEDAValue]] = defaultdict(list)
    # how many values passed the different level (MRA, KRA1, KRA2, KRA3) and the final check
    passing = [0, 0, 0, 0, 0]

    isd_values_ok: Set[ISDValue] = set()
    isd_values_to_compute: Set[ISDValue] = set()
    for level_idx, level in enumerate((1, 3, 5)):
        filename = f"/mnt/data/simone/vc/crypto/leda_design/stime_ISD/post_dfr_in/{ITERATION}/cat_{level}_region"
        leda_values = from_csv_to_ledavalue(f"{filename}.csv")

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
    filename = os.path.join(OUT_DIR, "LT", "results", "json", f"{n:06}_{k:06}_{t:03}.json")
    # continue exploring to find another minimum
    # filename = f"out/ledatools/json/{n:06}_{k:06}_{t:03}.json"
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
    print("Processing merged values")
    leda_vals_ok, passing_at_step, isd_values_ok, isd_values_to_compute = process()
    print(f"Passings each step {passing_at_step}")

    filename = os.path.join(OUT_DIR, "isd-leda", "values", "from_restrictions",
                            f"{ITERATION}"
                            "leda_values_")
    print(f"Saving leda vals ok")
    for level, item in zip((1, 3, 5), leda_vals_ok.items()):
        _, leda_vals = item
        filename_level = filename + f"L{level}.json"
        print(f"Saving leda vals for {level}")
        save_to_json(filename_level, leda_vals, cls=LEDAValueEncoder)

    print(f"Saving isd vals ok {len(isd_values_ok)}")
    filename = os.path.join(OUT_DIR, "isd-leda", "values", "from_restrictions",
                            f"{ITERATION}"
                            "isd_values.json")
    isd_vals = sorted(isd_values_ok)
    save_to_json(filename, isd_vals, cls=ISDValueEncoder)

    print(f"Saving isd vals to compute {len(isd_values_to_compute)}")
    filename = os.path.join(OUT_DIR, "isd-leda", "values", "from_restrictions",
                            f"{ITERATION}"
                            "isd_values_to_compute.json")
    isd_vals = sorted(set(isd_values_to_compute))
    save_to_json(filename, isd_vals, cls=ISDValueEncoder)


if __name__ == '__main__':
    main()
