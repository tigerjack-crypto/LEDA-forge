"""Exhaustive search over all parameters.
The Torres, Sendrier approximation did not work so good, and hence this tool will generate
all the candidate LEDA values exhaustively.
"""
import json
import os
from collections import defaultdict
from dataclasses import asdict
from itertools import product
# from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Pool
# from sys import argv
from typing import Dict, List, Set

import numpy as np
from ledaforge.launchers.launcher_utils import (LEVELS,
                                              get_proper_leda_primes)
from ledaforge.utils.paths import OUT_DIR
from ledaforge.utils.common import LEDAValue
from ledaforge.utils.export.export import save_ledavalues_to_csv


class CustomEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, LEDAValue):
            return asdict(obj)
        if isinstance(obj, set):
            return list(obj)
        return super().default(obj)


def merge_leda_values(
    leda_values_t_by_level: Dict[int, Dict[str, Set[LEDAValue]]],
    leda_values_v_by_level: Dict[int, Dict[str, Set[LEDAValue]]]
) -> Dict[int, List[LEDAValue]]:
    # levels = [1, 3, 5]
    merged = defaultdict(list)

    for level_idx, _ in enumerate(LEVELS):
        # level = levels[level_idx]
        keys = set(leda_values_t_by_level.get(level_idx, {})) | set(
            leda_values_v_by_level.get(level_idx, {}))
        for key in keys:
            t_vals = leda_values_t_by_level.get(level_idx, {}).get(key, set())
            v_vals = leda_values_v_by_level.get(level_idx, {}).get(key, set())

            # Cartesian product of all t's and v's
            for t_val, v_val in product(t_vals, v_vals):
                if v_val.p % 2 == 0:
                    print(f"v is even in merging {t_val} {v_val}")
                merged_val = LEDAValue(
                    p=t_val.p if t_val.p is not None else v_val.p,
                    n0=t_val.n0 if t_val.n0 is not None else v_val.n0,
                    t=t_val.t,
                    v=v_val.v,
                    tau=t_val.tau if t_val.tau is not None else v_val.tau,
                    msgs=(t_val.msgs or []) + (v_val.msgs or []))
                merged[level_idx].append(merged_val)

    return merged

def check_vs(level_idx, vmin, vmax):
    if level_idx == 0:
        if vmin < 31:
            vmin = 31
    elif level_idx == 1:
        if vmin < 51:
            vmin = 51
    elif level_idx == 2:
        if vmin < 75:
            vmin = 75

    if vmin % 2 == 0:
        vmin -= 1
    if vmax % 2 == 0:
        vmax += 1
    return vmin, vmax


def worker(leda_primes, level_idx, c_lambda):
    # level -> p_n0; all values have t != -1, v == -1
    leda_values_v: Dict[str, Set[LEDAValue]] = defaultdict(set)
    leda_values_t: Dict[str, Set[LEDAValue]] = defaultdict(set)

    for prime in filter(lambda p: 5e3 < p < 9e4, leda_primes):
        for n0 in range(2, 6):
            n = prime * n0
            if n > 2e5:
                continue
            # MRA
            r = prime
            k = n - r
            c = -np.log2(1 - k / n)
            c_lambda_expected = c_lambda - 3 * np.log2(r)
            tmin = int(np.floor(0.8 * c_lambda_expected / c))
            tmax = int(np.ceil(1.7 * c_lambda_expected / c))

            for t in range(tmin, tmax, 1):
                leda_val = LEDAValue(prime, n0, t, -1, msgs=[f"MRA"])
                leda_values_t[f"{prime}_{n0}"].add(leda_val)
                # isd_values.append(get_mra_from_leda(leda_val))
            del n, k, r, c, c_lambda_expected, t, leda_val

            # KRA1
            n = prime * n0
            r = prime
            k = n - r
            c = -np.log2(1 - k / n)
            c_lambda_expected = c_lambda - 3 * np.log2(r)

            vmin = int(np.floor(0.8 * c_lambda_expected / (2 * c)))
            vmax = int(np.ceil(1.7 * c_lambda_expected / (2 * c)))
            vmin, vmax = check_vs(level_idx, vmin, vmax)
            for v in range(vmin, vmax, 2):
                if v % 2 == 0:
                    print(f"KRA1, v is {v}")
                leda_val = LEDAValue(prime, n0, -1, v, msgs=[f"KRA 1"])
                leda_values_v[f"{prime}_{n0}"].add(leda_val)
                # isd_values.append(get_kra1_from_leda(leda_val))
            del n, k, r, c, c_lambda_expected, v

            # KRA2
            if n0 != 2:
                n = 2 * prime
                r = prime
                k = n - r
                c = -np.log2(1 - k / n)
                c_lambda_expected = c_lambda - 3 * np.log2(r)

                vmin = int(np.floor(0.8 * c_lambda_expected / (2 * c)))
                vmax = int(np.ceil(1.7 * c_lambda_expected / (2 * c)))
                vmin, vmax = check_vs(level_idx, vmin, vmax)
                for v in range(vmin, vmax, 2):
                    if v % 2 == 0:
                        print(f"KRA2, v is {v}")
                    leda_val = LEDAValue(prime, n0, -1, v, msgs=[f"KRA 2"])
                    leda_values_v[f"{prime}_{n0}"].add(leda_val)
                    # isd_values.append(
                    #     get_kra2_from_leda(leda_val))
                del n, k, r, c, c_lambda_expected, v, leda_val

            # KRA3
            n = prime * n0
            r = prime * (n0 - 1)
            k = n - r
            c = -np.log2(1 - k / n)
            c_lambda_expected = c_lambda - 3 * np.log2(r)
            vmin = int(np.floor(0.8 * c_lambda_expected / (n0 * c)))
            vmax = int(np.ceil(1.7 * c_lambda_expected / (n0 * c)))
            vmin, vmax = check_vs(level_idx, vmin, vmax)
            for v in range(vmin, vmax, 2):
                if v % 2 == 0:
                    print(f"KRA3, v is {v}")
                leda_val = LEDAValue(prime, n0, -1, v, msgs=[f"KRA 3"])
                leda_values_v[f"{prime}_{n0}"].add(leda_val)
                # isd_values.append(get_kra3_from_leda(leda_val))
    return leda_values_t, leda_values_v


def main():
    # stage = argv[1]  # the stage in which we are in
    leda_primes = get_proper_leda_primes()
    leda_values_t_by_level: Dict[int, Dict[str, Set[LEDAValue]]] = defaultdict(
        lambda: defaultdict(set))
    # level -> p_n0; all values have v != -1, t == -1
    leda_values_v_by_level: Dict[int, Dict[str, Set[LEDAValue]]] = defaultdict(
        lambda: defaultdict(set))

    args = [(leda_primes, level_idx, c_lambda)
            for level_idx, c_lambda in enumerate(LEVELS)]

    dirpath = os.path.join(
        OUT_DIR,
        "orchestra",
        # f"S{stage}",
        "S0",
        "exhaustive_generation",
    )
    if not os.path.exists(dirpath):
        os.mkdir(dirpath)
    print(f"Results will be in {dirpath}")

    with Pool() as pool:
        results = pool.starmap(worker, args)

    for idx, (leda_t, leda_v) in enumerate(results):
        leda_values_t_by_level[idx] = leda_t
        leda_values_v_by_level[idx] = leda_v

    print("Exhaustive generation over")
    levels = [1, 3, 5]
    merged_leda_values = merge_leda_values(leda_values_t_by_level,
                                           leda_values_v_by_level)
    print("Merging over")
    for level_idx, _ in enumerate(LEVELS):
        filename = os.path.join(dirpath, f"cat_{levels[level_idx]}_region.csv")
        print(f"Saving leda vals to {filename}")
        save_ledavalues_to_csv(merged_leda_values[level_idx], filename)

    # filename = os.path.join(dirpath, "isd_values")
    # isd_vals = sorted(set(isd_values))
    # print(f"Saving isd vals to {filename}")
    # save_to_json(filename, isd_vals, cls=ISDValueEncoder)


if __name__ == '__main__':
    main()
