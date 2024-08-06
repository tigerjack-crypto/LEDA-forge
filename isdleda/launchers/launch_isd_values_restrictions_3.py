import os
from collections import defaultdict
from typing import Dict, List

import numpy as np
from isdleda.launchers.launcher_utils import AES_LAMBDAS, QAES_LAMBDAS
from isdleda.utils.common import ISDValue, LEDAValue, dict_to_leda_value
from isdleda.utils.export.export import (ISDValueEncoder, LEDAValueEncoder,
                                         load_from_json, save_to_json)


# level -> p_n0; all values have t != -1, v == -1
# level -> p_n0; all values have v != -1, t == -1
def post_process_values(leda_values_t: Dict[int, Dict[str, List[LEDAValue]]],
                        leda_values_v: Dict[int, Dict[str, List[LEDAValue]]]):
    # Assuming all the values are already present in the database
    leda_values_new: Dict[int, List[LEDAValue]] = defaultdict(list)
    isd_values_to_compute: List[ISDValue] = []
    isd_values_ok: List[ISDValue] = []
    # level idx is (0, 1, 2)
    for level_idx, leda_vals_t_by_p_n0 in leda_values_t.items():
        c_lambda = AES_LAMBDAS[int(level_idx)]
        q_lambda = QAES_LAMBDAS[int(level_idx)]
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
                    c_complexities = [leda_val.p * leda_val.n0] * 4
                    q_complexities = [leda_val.p * leda_val.n0] * 4
                    isd_vals_ok = []

                    # MRA
                    n = leda_val.p * leda_val.n0
                    k = leda_val.p * (leda_val.n0 - 1)
                    t = leda_val.t
                    # try:
                    c_aes, q_aes, cont = check_dataset(
                        n,
                        k,
                        t,
                        c_lambda,
                        q_lambda,
                        reduction=np.log2(leda_val.p) / 2,
                        msg=f"MRA, {leda_val.p} {leda_val.n0} {leda_val.v}")
                    if (c_aes is None or q_aes is None):
                        isd_values_to_compute.append(ISDValue(n, n - k, t))
                        continue
                    if cont:
                        continue
                    isd_vals_ok.append(ISDValue(n, k, t))
                    c_complexities[0] = c_aes
                    q_complexities[0] = q_aes
                    del n, k, t

                    # KRA 1
                    n = leda_val.p * leda_val.n0  #
                    k = leda_val.p * (leda_val.n0 - 1)  #
                    t = leda_val.v * 2
                    c_aes, q_aes, cont = check_dataset(
                        n,
                        k,
                        t,
                        c_lambda,
                        q_lambda,
                        reduction=np.log2(leda_val.p) + np.log2(leda_val.n0) +
                        np.log2(leda_val.n0 - 1) - 1,
                        msg=f"KRA1, {leda_val.p} {leda_val.n0} {leda_val.v}")
                    if (c_aes is None or q_aes is None):
                        isd_values_to_compute.append(ISDValue(n, n - k, t))
                        continue
                    if cont:
                        continue
                    c_complexities[1] = c_aes
                    q_complexities[1] = q_aes
                    isd_vals_ok.append(ISDValue(n, k, t))
                    del n, k, t

                    # KRA 2
                    if leda_val.n0 != 2:
                        n = 2 * leda_val.p
                        k = leda_val.p
                        t = leda_val.v * 2
                        c_aes, q_aes, cont = check_dataset(
                            n,
                            k,
                            t,
                            c_lambda,
                            q_lambda,
                            reduction=np.log2(leda_val.p),
                            msg=f"KRA2, {leda_val.p} {leda_val.n0} {leda_val.v}"
                        )
                        if (c_aes is None or q_aes is None):
                            isd_values_to_compute.append(ISDValue(n, n - k, t))
                            continue
                        if cont:
                            continue
                        c_complexities[2] = c_aes
                        q_complexities[2] = q_aes
                        isd_vals_ok.append(ISDValue(n, k, t))
                        del n, k, t

                    # KRA 3
                    n = leda_val.p * leda_val.n0
                    k = leda_val.p
                    t = leda_val.v * leda_val.n0
                    c_aes, q_aes, cont = check_dataset(
                        n,
                        k,
                        t,
                        c_lambda,
                        q_lambda,
                        reduction=np.log2(leda_val.p),
                        msg=f"KRA3, {leda_val.p} {leda_val.n0} {leda_val.v}")
                    if (c_aes is None or q_aes is None):
                        isd_values_to_compute.append(ISDValue(n, n - k, t))
                        continue
                    if cont:
                        continue

                    c_complexities[3] = c_aes
                    q_complexities[3] = q_aes
                    isd_vals_ok.append(ISDValue(n, k, t))

                    # min c, min q, min c attack, min q attack
                    min_c = n
                    min_q = n
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
                        leda_val.msgs.extend([
                            f"MIN C: {min_c} attack: {min_c_attack}, MIN Q:{min_q} attack: {min_q_attack}"
                        ])
                        leda_values_new[int(level_idx)].append(leda_val)
                        isd_values_ok.extend(isd_vals_ok)
    return leda_values_new, isd_values_ok, isd_values_to_compute,


def check_dataset(n, k, t, c_lambda, q_lambda, reduction, msg):
    filename = f"out/cisd_leda/json/{n:06}_{k:06}_{t:03}.json"
    # continue exploring to find another minimum
    cont = True
    try:
        data = load_from_json(filename)
        c_time = data['Classic']['Plain']['value'] - reduction
        q_time = (data['Quantum']['Plain']['value']) * 2 - reduction
        if c_time < .8 * c_lambda or q_time < .8 * q_lambda:
            cont = False
        return c_time, q_time, cont

    except FileNotFoundError:
        return None, None, False


def is_inside(c_time, q_time, c_lambda, q_lambda):
    # - 1: below lower bound; 0: inside bounds; 1 above bounds

    if .8 * c_lambda <= c_time <= 1.2 * c_lambda:
        if .75 * q_lambda <= q_time <= 1.25 * q_lambda:
            return True, c_time, q_time
        else:
            # TODO Idea here is to detect quantum bounds
            return False, c_time, q_time
    return False


def main():
    filename = os.path.join("out", "values", "from_generation_3",
                            "leda_values_t.json")
    leda_values_t_by_level = load_from_json(filename)

    filename = os.path.join("out", "values", "from_generation_3",
                            "leda_values_v.json")
    leda_values_v_by_level = load_from_json(filename)

    leda_vals_new, isd_values_ok, isd_values_to_compute = post_process_values(
        leda_values_t_by_level, leda_values_v_by_level)

    print("Saving isd vals ok")
    filename = os.path.join("out", "values", "from_restrictions_3",
                            "isd_values.json")
    isd_vals = sorted(set(isd_values_ok))
    save_to_json(filename, isd_vals, cls=ISDValueEncoder)

    print(f"Saving isd vals fo compute")
    filename = os.path.join("out", "values", "from_restrictions_3",
                            "isd_values_to_compute.json")
    isd_vals = sorted(set(isd_values_to_compute))
    save_to_json(filename, isd_vals, cls=ISDValueEncoder)

    filename = os.path.join("out", "values", "from_restrictions_3",
                            "leda_values_")
    for level, item in zip((1, 3, 5), leda_vals_new.items()):
        _, leda_vals = item
        filename_level = filename + f"L{level}.json"
        print(f"Saving leda vals for {level}")
        save_to_json(filename_level, leda_vals, cls=LEDAValueEncoder)


if __name__ == '__main__':
    main()
