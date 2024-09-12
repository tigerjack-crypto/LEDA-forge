import itertools
from json import JSONDecodeError
import math
import os
from collections import defaultdict

import numpy as np
from isdleda.launchers.launcher_utils import (AES_LAMBDAS, QAES_LAMBDAS,
                                              get_proper_leda_primes)
from isdleda.utils.common import ISDValue, LEDAValue
from isdleda.utils.export.export import (ISDValueEncoder, LEDAValueEncoder,
                                         load_from_json, save_to_json)


def check_dataset(n, k, w, reduction, msg):
    filename = f"out/ledatools/json/{n:06}_{k:06}_{w:03}.json"
    # continue exploring to find another minimum
    # less_than_threshold = False
    try:
        data = load_from_json(filename)
        c_time = data['Classic']['Plain']['value'] - reduction
        q_time = (data['Quantum']['Plain']['value']) * 2 - reduction
        if c_time < 0 or q_time < 0:
            print(f"{msg}")
            raise Exception(
                f"Value less than 0 for {filename}, with reduction {reduction}: {c_time}, {q_time}"
            )
        return c_time, q_time
    except FileNotFoundError:
        return None, None
    except JSONDecodeError as e:
        print(filename)
        raise e


def is_above_min_complexity(c_time, q_time):
    # it's useless to continue if it's below the min value of lambda.
    # We don't check for max bcz the overall complexity is the min b/w all attacks.
    if c_time < .8 * AES_LAMBDAS[0] or q_time < .8 * QAES_LAMBDAS[0]:
        return False
    return True


def check_level(c_time, q_time):
    # Find levels for both AES and QAES within the lambda range
    c_levels = {
        level
        for level, c_lambda in zip((1, 3, 5), AES_LAMBDAS)
        if 0.8 * c_lambda < c_time < 1.2 * c_lambda
    }
    q_levels = {
        level
        for level, q_lambda in zip((1, 3, 5), QAES_LAMBDAS)
        if 0.8 * q_lambda < q_time < 1.2 * q_lambda
    }

    # Use set operations to find differences and common elements
    bounds = [
        'Q' if c_level not in q_levels else 'C'
        for c_level in c_levels.symmetric_difference(q_levels)
    ]
    levels = c_levels & q_levels  # Intersection of both sets

    return levels, bounds


def sweep():
    leda_primes_filtered = filter(lambda x: x >= 4e3 and x <= 10e5,
                                  leda_primes)

    leda_values_by_level = defaultdict(list)
    isd_values_to_compute = []

    n0_range = range(2, 6)
    t_range = range(40, 300, 1)
    v_range = range(40, 250, 2)

    for n0, prime, t, v in itertools.product(
            n0_range,
            # itertools.islice(leda_primes_filtered, 0, None, 10),
            leda_primes_filtered,
            t_range,
            v_range,
    ):
        n = n0 * prime
        if n >= 3e6:
            continue
        c_times = []
        q_times = []
        has_nones = False

        # KRA1 (CFP); ISD(n0*p,p,2*v) / (p*binom{n0}{2}); code rate (n0-1)/n0;
        k = (n0 - 1) * prime
        w = 2 * v
        c_time, q_time = check_dataset(n=n,
                                       k=k,
                                       w=w,
                                       reduction=np.log2(prime) + np.log2(n0) +
                                       np.log2(n0 - 1) - 1,
                                       msg=f"KRA1, {prime} {n0} {v}")
        if c_time is None or q_time is None:
            isd_values_to_compute.append(ISDValue(n, n - k, w))
            has_nones = True
        else:
            if not is_above_min_complexity(c_time, q_time):
                continue
            c_times.append(c_time)
            q_times.append(q_time)

        # KRA2 (CFP); ISD(2*p,p,2*v) / (n0*p); attacked code rate (1/2); target weight = 2v
        if n0 != 2:
            n = 2 * prime
            k = prime
            w = 2 * v
            c_time, q_time = check_dataset(n=n,
                                           k=k,
                                           w=w,
                                           reduction=np.log2(prime) +
                                           np.log2(n0),
                                           msg=f"KRA2, {prime} {n0} {v}")
            if c_time is None or q_time is None:
                isd_values_to_compute.append(ISDValue(n, n - k, w))
                has_nones = True
            else:
                if not is_above_min_complexity(c_time, q_time):
                    continue
                c_times.append(c_time)
                q_times.append(q_time)

        # KRA3 (CFP); ISD(n0*p,(n0-1)*p,n0*v) / p; attacked code rate 1/n0; target weight = n0*v
        n = prime * n0
        k = prime
        w = v * n0
        c_time, q_time = check_dataset(n=n,
                                       k=k,
                                       w=w,
                                       reduction=np.log2(prime),
                                       msg=f"KRA3, {prime} {n0} {v}")
        if c_time is None or q_time is None:
            isd_values_to_compute.append(ISDValue(n, n - k, w))
            has_nones = True
        else:
            if not is_above_min_complexity(c_time, q_time):
                continue
            c_times.append(c_time)
            q_times.append(q_time)

        # MRA
        n = prime * n0
        k = prime * (n0 - 1)
        w = t
        c_time, q_time = check_dataset(n=n,
                                       k=k,
                                       w=w,
                                       reduction=np.log2(prime) / 2,
                                       msg=f"MRA, {prime} {n0} {v}")

        if c_time is None or q_time is None:
            isd_values_to_compute.append(ISDValue(n, n - k, w))
            has_nones = True
        else:
            if not is_above_min_complexity(c_time, q_time):
                continue
            c_times.append(c_time)
            q_times.append(q_time)

        if has_nones:
            continue

        # compute minimum complexity
        c_time_min = min(c_times)
        q_time_min = min(q_times)
        levels, bounds = check_level(c_time_min, q_time_min)

        # if it reaches this point, the leda value is a good candidate for one or more levels
        leda_val = LEDAValue(prime,
                             n0,
                             t,
                             v,
                             None,
                             msgs=[
                                 f"levels {levels}",
                                 f"bounds {bounds}",
                                 f"C: {c_time_min}",
                                 f"Q: {q_time_min}",
                             ])
        for level in levels:
            leda_values_by_level[level].append(leda_val)
    return leda_values_by_level, list(set(isd_values_to_compute))


def main():
    global leda_primes
    leda_primes = get_proper_leda_primes()
    leda_values_by_level, isd_values_to_compute = sweep()

    filename = os.path.join("out", "values", "from_restrictions_4")
    save_to_json(os.path.join(filename, "isd_values_to_compute.json"),
                 isd_values_to_compute,
                 cls=ISDValueEncoder)

    for level, leda_values in leda_values_by_level.items():
        save_to_json(os.path.join(filename, f"leda_values_{level}.json"),
                     leda_values,
                     cls=LEDAValueEncoder)

    ledas_by_n0 = {}
    for level, leda_values in leda_values_by_level.items():
        # just to build the data structure
        ledas_by_n0[level] = {}
        for n0 in range(2, 6):
            ledas_by_n0[level][n0] = {
                'p': {
                    'p_min': math.inf,
                    'p_max': 0,
                    't_min': math.inf,
                    't_max': 0,
                    'v_min': math.inf,
                    'v_max': 0,
                    'n_vals': 0
                }
            }
        del n0

        for leda_val in leda_values:
            ledas_by_n0[level][leda_val.n0]['p']['n_vals'] += 1
            if leda_val.p < ledas_by_n0[level][leda_val.n0]['p']['p_min']:
                ledas_by_n0[level][leda_val.n0]['p']['p_min'] = leda_val.p
            if leda_val.p > ledas_by_n0[level][leda_val.n0]['p']['p_max']:
                ledas_by_n0[level][leda_val.n0]['p']['p_max'] = leda_val.p
            if leda_val.t < ledas_by_n0[level][leda_val.n0]['p']['t_min']:
                ledas_by_n0[level][leda_val.n0]['p']['t_min'] = leda_val.t
            if leda_val.t > ledas_by_n0[level][leda_val.n0]['p']['t_max']:
                ledas_by_n0[level][leda_val.n0]['p']['t_max'] = leda_val.t
            if leda_val.v < ledas_by_n0[level][leda_val.n0]['p']['v_min']:
                ledas_by_n0[level][leda_val.n0]['p']['v_min'] = leda_val.v
            if leda_val.v > ledas_by_n0[level][leda_val.n0]['p']['v_max']:
                ledas_by_n0[level][leda_val.n0]['p']['v_max'] = leda_val.v

    save_to_json(os.path.join(filename, "leda_values_ranges.json"),
                 ledas_by_n0,
                 cls=LEDAValueEncoder)


if __name__ == '__main__':
    main()
