"""Exhaustive, parallel search through all the LEDA values in dataset for the ones being
in the security level region. It seems to be less efficient than a sequential search.

"""
import itertools
import math
import os
from multiprocessing import Manager, Pool, cpu_count

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
        return c_time, q_time  #, less_than_threshold
    except FileNotFoundError:
        return None, None

def is_above_min_complexity(c_time, q_time):
    # it's useless to continue if it's below the min value of lambda.
    # We don't check for max bcz the overall complexity is the min b/w all attacks.
    if c_time < .8 * AES_LAMBDAS[0] or q_time < .8 * QAES_LAMBDAS[0]:
        return False
    return True

def check_level(c_time, q_time):
    # Find levels for both AES and QAES within the lambda range
    c_levels = {level for level, c_lambda in zip((1, 3, 5), AES_LAMBDAS) if 0.8 * c_lambda < c_time < 1.2 * c_lambda}
    q_levels = {level for level, q_lambda in zip((1, 3, 5), QAES_LAMBDAS) if 0.8 * q_lambda < q_time < 1.2 * q_lambda}

    # Use set operations to find differences and common elements
    bounds = ['Q' if c_level not in q_levels else 'C' for c_level in c_levels.symmetric_difference(q_levels)]
    levels = c_levels & q_levels  # Intersection of both sets

    return levels, bounds


def _process_combination(params):
    n0, prime, t, v = params
    n = n0 * prime
    if n >= 2.5e5:
        return

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
            return
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
                                       reduction=np.log2(prime) + np.log2(n0),
                                       msg=f"KRA2, {prime} {n0} {v}")
        if c_time is None or q_time is None:
            isd_values_to_compute.append(ISDValue(n, n - k, w))
            has_nones = True
        else:
            if not is_above_min_complexity(c_time, q_time):
                return
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
            return
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
            return
        c_times.append(c_time)
        q_times.append(q_time)

    if has_nones:
        return

    # if it reaches this point, the leda value is a good candidate for one or more levels
    # compute minimum complexity
    c_time_min = min(c_times)
    q_time_min = min(q_times)
    levels, bounds = check_level(c_time_min, q_time_min)

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


def sweep():
    # Create a manager to handle shared objects between processes
    manager = Manager()
    global leda_values_by_level
    leda_values_by_level = manager.dict()
    global isd_values_to_compute
    isd_values_to_compute = manager.list()

    for level in (1, 3, 5):
        leda_values_by_level[level] = []

    # Use a Pool to parallelize processing
    with Pool(cpu_count() - 1, maxtasksperchild=50) as pool:
        result_iterator = pool.imap_unordered(
            _process_combination,
            itertools.product(
                range(2, 6),  # n0
                range(40, 300, 1),  # t
                range(40, 200, 2),  # v
                filter(lambda x: x >= 4e3 and x <= 10e5, leda_primes)),  # prime
            chunksize=100)
        acc = 0
        for _ in result_iterator:
            print(f"{acc}", end="\r")
            pass


def main():
    global leda_primes
    leda_primes = get_proper_leda_primes()
    sweep()

    filename = os.path.join(
        "out",
        "values",
        "from_restrictions_5",
    )

    isd_values_to_compute_a = list(set(isd_values_to_compute._getvalue()))

    save_to_json(os.path.join(filename, "isd_values_to_compute.json"),
                 isd_values_to_compute_a,
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
            if leda_val.prime < ledas_by_n0[level][leda_val.n0]['p']['p_min']:
                ledas_by_n0[level][leda_val.n0]['p']['p_min'] = leda_val.p
            if leda_val.prime > ledas_by_n0[level][leda_val.n0]['p']['p_max']:
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
                 ledas_by_n0.copy(),
                 cls=LEDAValueEncoder)


if __name__ == '__main__':
    main()


# def check_level(c_time, q_time):
#     levels = set()
#     bounds = []

#     if c_time is None or q_time is None:
#         return levels, bounds

#     c_levels = []
#     q_levels = []
#     for level, c_lambda in zip((1, 3, 5), AES_LAMBDAS):
#         if .8 * c_lambda < c_time < 1.2 * c_lambda:
#             c_levels.append(level)
#     for level, q_lambda in zip((1, 3, 5), QAES_LAMBDAS):
#         if .8 * q_lambda < q_time < 1.2 * q_lambda:
#             q_levels.append(level)
#     # TODO optimize the next two iterations, may be done in terms of set
#     for c_level in c_levels:
#         if c_level not in q_levels:
#             bounds.append('Q')
#         else:
#             levels.add(c_level)

#     for q_level in q_levels:
#         if q_level not in c_levels:
#             bounds.append('C')
#         else:
#             levels.add(q_level)

#     return levels, bounds
