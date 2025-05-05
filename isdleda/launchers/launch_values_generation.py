"""Exhaustive search over all parameters.
The Torres, Sendrier approximation did not work so good.
"""
import json
import os
from collections import defaultdict
from dataclasses import asdict
from typing import Dict, List, Set
from itertools import product

import numpy as np
from isdleda.launchers.launcher_utils import LEVELS, get_proper_leda_primes, OUT_DIR
from isdleda.utils.common import ISDValue, LEDAValue
from isdleda.utils.export.export import ISDValueEncoder, save_ledavalues_to_csv, save_to_json


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
                merged_val = LEDAValue(
                    p=t_val.p if t_val.p is not None else v_val.p,
                    n0=t_val.n0 if t_val.n0 is not None else v_val.n0,
                    t=t_val.t,
                    v=v_val.v,
                    tau=t_val.tau if t_val.tau is not None else v_val.tau,
                    msgs=(t_val.msgs or []) + (v_val.msgs or []))
                merged[level_idx].append(merged_val)

    return merged


def main():
    leda_primes = get_proper_leda_primes()

    isd_values: List[ISDValue] = []
    # level -> p_n0; all values have t != -1, v == -1
    leda_values_t_by_level: Dict[int, Dict[str, Set[LEDAValue]]] = defaultdict(
        lambda: defaultdict(set))
    # level -> p_n0; all values have v != -1, t == -1
    leda_values_v_by_level: Dict[int, Dict[str, Set[LEDAValue]]] = defaultdict(
        lambda: defaultdict(set))

    for level_idx, c_lambda in enumerate(LEVELS):
        # for c_lambda in LEVELS:
        for prime in filter(lambda p: 5e3 < p < 9e4, leda_primes):
            for n0 in range(2, 6):
                # MRA, KRA1, 2, 3

                n = prime * n0
                if n > 2e5:
                    continue
                # MRA, KRA1, KRA2, KRA3
                r = prime
                k = n - r
                c = -np.log2(1 - k / n)
                c_lambda_expected = c_lambda - 3 * np.log2(r)
                tmin = int(np.floor(.6 * c_lambda_expected / c))
                tmax = int(np.ceil(1.2 * c_lambda_expected / c))

                for t in range(tmin, tmax, 1):
                    isd_values.append(ISDValue(n, r, t, msgs=[f"MRA"]))
                    leda_values_t_by_level[level_idx][f"{prime}_{n0}"].add(
                        LEDAValue(prime, n0, t, -1, msgs=[f"MRA"]))
                del n, k, r, c, c_lambda_expected, t

                # KRA1
                n = prime * n0
                r = prime
                k = n - r
                c = -np.log2(1 - k / n)
                c_lambda_expected = c_lambda - 3 * np.log2(r)

                vmin = int(np.floor(.8 * c_lambda_expected / (2 * c)))
                vmax = int(np.ceil(1.2 * c_lambda_expected / (2 * c)))
                if vmin % 2 == 0:
                    vmin -= 1
                if vmax % 2 == 0:
                    vmax += 1
                for v in range(vmin, vmax, 2):
                    isd_values.append(ISDValue(n, r, 2 * v, msgs=[f"KRA 1"]))
                    leda_values_v_by_level[level_idx][f"{prime}_{n0}"].add(
                        LEDAValue(prime, n0, -1, v, msgs=[f"KRA 1"]))
                del n, k, r, c, c_lambda_expected, v

                # KRA2
                if n0 != 2:
                    n = 2 * prime
                    r = prime
                    k = n - r
                    c = -np.log2(1 - k / n)
                    c_lambda_expected = c_lambda - 3 * np.log2(r)

                    vmin = int(np.floor(.8 * c_lambda_expected / (2 * c)))
                    vmax = int(np.ceil(1.2 * c_lambda_expected / (2 * c)))
                    if vmin % 2 == 0:
                        vmin -= 1
                    if vmax % 2 == 0:
                        vmax += 1
                    for v in range(vmin, vmax, 2):
                        isd_values.append(
                            ISDValue(n, r, 2 * v, msgs=[f"KRA 2"]))
                        leda_values_v_by_level[level_idx][f"{prime}_{n0}"].add(
                            LEDAValue(prime, n0, -1, v, msgs=[f"KRA 2"]))
                    del n, k, r, c, c_lambda_expected, v

                # KRA3
                n = prime * n0
                r = prime * (n0 - 1)
                k = n - r
                c = -np.log2(1 - k / n)
                c_lambda_expected = c_lambda - 3 * np.log2(r)
                vmin = int(np.floor(.8 * c_lambda_expected / (n0 * c)))
                vmax = int(np.ceil(1.2 * c_lambda_expected / (n0 * c)))
                if vmin % 2 == 0:
                    vmin -= 1
                if vmax % 2 == 0:
                    vmax += 1
                for v in range(vmin, vmax, 2):
                    isd_values.append(ISDValue(n, r, n0 * v, msgs=[f"KRA 3"]))
                    leda_values_v_by_level[level_idx][f"{prime}_{n0}"].add(
                        LEDAValue(prime, n0, -1, v, msgs=[f"KRA 3"]))
                del n, k, r, c, c_lambda_expected, v

    print("Saving isd vals")
    filename = os.path.join(OUT_DIR, "isd-leda", "values",
                            "exhaustive_generation", "isd_values")
    isd_vals = sorted(set(isd_values))
    save_to_json(filename, isd_vals, cls=ISDValueEncoder)

    print("Saving leda vals")
    dirpath = os.path.join(
        OUT_DIR,
        "isd-leda",
        "values",
        "exhaustive_generation",
    )
    levels = [1, 3, 5]
    merged_leda_values = merge_leda_values(leda_values_t_by_level, leda_values_v_by_level)
    for level_idx, _ in enumerate(LEVELS):
        filename = os.path.join(dirpath, f"cat_{levels[level_idx]}_region.csv")
        save_ledavalues_to_csv(merged_leda_values[level_idx], filename)

    # print("Saving leda vals t")
    # filename = os.path.join(OUT_DIR, "isd-leda", "values", "exhaustive_generation",
    #                         "leda_values_t")
    # save_to_json(filename, leda_values_t_by_level, cls=CustomEncoder)

    # print("Saving leda vals v")
    # filename = os.path.join(OUT_DIR, "isd-leda", "values", "exhaustive_generation",
    #                         "leda_values_v")
    # save_to_json(filename, leda_values_v_by_level, cls=CustomEncoder)


if __name__ == '__main__':
    main()
