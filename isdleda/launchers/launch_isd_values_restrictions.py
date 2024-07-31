import functools
import itertools
import json
import logging
import operator
import os
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from isdleda.launchers.launcher_utils import init_logger
from isdleda.utils.common import Value
from isdleda.utils.paths import OUT_FILES_CLEDA_FMT, OUT_FILES_CLEDA_TYPE_DIR
from numpy import log2
from sortedcontainers import SortedDict

LOGGER = logging.getLogger(__name__)

# Official NIST values
AES_LAMBDAS = (143, 207, 272)
# Best values obtained for Jan+22 Ph.D. Thesis, table 6.5 (Jan+22).
QAES_LAMBDAS = (154, 219, 283)
# Values from Jaques, used by NIST in additional signature calls
# QAES_LAMBDAS = (157, 221, 285)

OUT_FILE_LEDA_VALS = 'out/values/from_restrictions/leda_values.json'
OUT_FILE_ISD_VALS = 'out/values/from_restrictions/isd_values.json'
OUT_FILE_ISD_VALS_TO_COMPUTE = 'out/values/from_restrictions/isd_values_to_compute.json'

# We want to explore the region around a given lambda; that is, [lamba + val[0], lambda + val[1]]
C_INTERVALS_FUNCTS = (functools.partial(operator.add, -30),
                      functools.partial(operator.add, 30))
# I am less conservative with quantum. If there's a classical speed-up of X,
# the quantum speed-up would roughly be sqrt(X)
Q_INTERVALS_FUNCTS = (functools.partial(operator.add, -20),
                      functools.partial(operator.add, 20))
# C_INTERVALS_FUNCTS = (functools.partial(operator.mul, .8), functools.partial(operator.mul, 1.2))
# Q_INTERVALS_FUNCTS = (functools.partial(operator.mul, .8), functools.partial(operator.mul, 1.2))

# We want to emit warning if the first value explored is too close to the
# actual value. F.e., if we have a target lambda of 100, and the first (lowest)
# t explored produces a lambda = 98, we started the exploration from a value
# which is too close to the frontier. The same applies for the upper bound, so
# f.e. at the last iteration we have a value of 102.
#
# These intervals are interpred as: If first value explored and CAES >= lambda
# + val[0] -> WARN. If last value explored and CAES <= lambda + val[1] -> WARN

C_INTERVALS_WARN_FUNCTS = (functools.partial(operator.add, -20),
                           functools.partial(operator.add, +20))
Q_INTERVALS_WARN_FUNCTS = (functools.partial(operator.add, -15),
                           functools.partial(operator.add, +15))


def check_frontier(low: bool, caes, c_lambda, qaes, q_lambda, msg: str, n, k,
                   t):
    """Either low or up frontier"""
    isd_values = []
    # exploring_range
    # low (i.e., first value explored) and (caes> c_lambda - 20 or qaes> q_lambda - 20)
    if low and (caes > C_INTERVALS_WARN_FUNCTS[0](c_lambda)
                or qaes > Q_INTERVALS_WARN_FUNCTS[0](q_lambda)):
        LOGGER.warning(f"WARNING: lower frontier! ")
        LOGGER.warning(msg)
        LOGGER.warning(f"(c_lambda, q_lambda) = ({c_lambda, q_lambda})")
        LOGGER.warning(f"(c_aes, q_aes) = ({caes, qaes})")
        LOGGER.warning(f"{n}_{k}_{t}")
        for i in range(-15, 15):
            val = Value(n, n - k, t + i)
            isd_values.append(val)
    # high (i.e., last value explored) and (caes< c_lambda + 20 or qaes< q_lambda + 20)
    if not low and (caes < C_INTERVALS_WARN_FUNCTS[1](c_lambda)
                    or qaes < Q_INTERVALS_WARN_FUNCTS[1](q_lambda)):
        LOGGER.warning("WARNING: upper frontier! ")
        LOGGER.warning(msg)
        LOGGER.warning(f"(c_lambda, q_lambda) = ({c_lambda, q_lambda})")
        LOGGER.warning(f"(c_aes, q_aes) = ({caes, qaes})")
        LOGGER.warning(f"{n}_{k}_{t}")
        for i in range(-15, 15):
            val = Value(n, n - k, t + i)
            isd_values.append(val)
    return isd_values


def get_complexity(n, k, t) -> Optional[Tuple[float, float]]:
    # WARN: we iterate on all the values close to t. The rationale is that, in
    # this module, we are trying to create a range of parameters to explore,
    # and varying the t shouldn't affect the values too much.
    #
    # To have a reference, taking the lowest n for leda, and using a (-4, +4)
    # on t, results in a (-4, +4) on the (log2) complexity. Taking the highest
    # results in (-8, +8). To compensate, we can approximately add the diff (t
    # - _t) to the result. For the quantum side, these values are halved.

    for _t in (t, t + 1, t - 1, t + 2, t - 2, t - 3, t + 3):
        filename = OUT_FILES_CLEDA_FMT.format(out_type='json',
                                              n=n,
                                              k=k,
                                              t=_t,
                                              ext='json')
        if os.path.isfile(filename):
            with open(filename, 'r') as f:
                data = json.load(f)
                cval = data['Classic']['Plain']['value']
                qval = data['Quantum']['Plain']['value']
                return cval + (t - _t), qval + (t - _t) / 2
    return None


# Define the nested defaultdict initialization
def _nested_dict():
    return defaultdict(lambda: defaultdict(dict))


def _convert_to_sorteddict(d):
    if isinstance(d, defaultdict):
        d = {k: _convert_to_sorteddict(v) for k, v in d.items()}
    if isinstance(d, dict):
        return SortedDict(d)
    return d


def get_filenames(
    filenames: List[str]
    # directory: str
) -> Dict[int, Dict[int, Dict[int, str]]]:
    filenames = sorted([Path(x).stem for x in filenames])

    filenames_idx_by_p: Dict[int, Dict[int,
                                       Dict[int,
                                            str]]] = defaultdict(_nested_dict)
    for fname in filenames:
        n, k, t = [int(x) for x in fname.split('_')]
        p = n - k
        n0 = n // p
        filenames_idx_by_p[p][n0][t] = fname
    filenames_idx_by_p_sorted = _convert_to_sorteddict(filenames_idx_by_p)
    return filenames_idx_by_p_sorted


def param(
    c_lambd: int,
    q_lambd: int,
    filenames_idx_by_p: Dict[int, Dict[int, Dict[int, str]]],
):
    # These are the leda values. Each entry is a tuple (p, n0, v, t, (C_complexity, Q_complexity))
    leda_values = []
    # These are the right ISD values to explore in the intervals around the
    # lambda values. Each entry is a Value with (n, r, t)
    isd_values = []

    # These are the ISD values for which additional exploration is needed, since probably
    # there have been values too close to the frontier
    isd_values_to_compute = []

    ps_sorted = sorted(filenames_idx_by_p)
    pmin, pmax = ps_sorted[0], ps_sorted[
        -1]  # min value of r given the filenames
    # to_generate: Set[Value]
    for p, n0 in itertools.product(range(int(pmin), int(pmax) + 1), (2, 6)):
        complexities: Dict[str, Tuple[float, float]] = {}
        n = p * n0
        r = p
        k = n - r
        try:
            filenames_idx_by_p[p][n0]
        except KeyError:
            continue
        # if n0 not in filenames_idx_by_p[p] or len(filenames_idx_by_p[p][n0]) ==0:
        #     # no value for this p and n0
        #     continue  # next (p, n0)
        # for the given value, find the minimum/maximum t
        ts_sorted = sorted(filenames_idx_by_p[p][n0])
        tmin, tmax = ts_sorted[0], ts_sorted[-1]
        trange = range(tmin, tmax + 1)
        for i, t in enumerate(trange):
            # check only the values reaching the minimum threshold
            res = get_complexity(n, k, t)
            if res is None:
                # No file with that t
                continue  # next t
            c_compl, q_compl = res
            red = log2(p) / 2
            caes = c_compl - red
            # For the quantum part, the threshold values are given by twice the
            # depth of the circuit (check Eq. 6.6 of my phd.thesis)
            qaes = 2 * (q_compl - red)
            caes_diff_low = caes - C_INTERVALS_FUNCTS[0](c_lambd)
            qaes_diff_low = qaes - Q_INTERVALS_FUNCTS[0](q_lambd)
            caes_diff_high = caes - C_INTERVALS_FUNCTS[1](c_lambd)
            qaes_diff_high = qaes - Q_INTERVALS_FUNCTS[1](q_lambd)
            if caes_diff_low <= 0 or qaes_diff_low <= 0:
                continue  # next t
            if caes_diff_high >= 0 or qaes_diff_high >= 0:
                break  # do not keep increasing the ts, it's useless, we'll have higher values
            # if at the first iteration I get a lower value which is
            #
            # - too close to the lower bound (f.e., clambda = 100, caes = 98 -> caes_diff_low = 2) OR
            #
            # - too far from the lower bound (f.e., clambda = 100, caes = +120)
            # too far away from it
            if i == 0:
                vals = check_frontier(
                    True, caes, c_lambd, qaes, q_lambd,
                    f"- MRA: p = {p}, n0 = {n0}, *t* = {t}! ", n, k, t)
                isd_values_to_compute.extend(vals)
            elif i == len(trange) - 1:
                vals = check_frontier(
                    False, caes, c_lambd, qaes, q_lambd,
                    f"- MRA: p = {p}, n0 = {n0}, *t* = {t}! ", n, k, t)
                isd_values_to_compute.extend(vals)
            complexities['MRA'] = (caes, qaes)

            # arbitrary start range, considering that t=(2*v, 2*v, n0*v)
            vmin = t // n0
            vmin = tmin // 2
            # vmin should be odd
            if vmin % 2 == 0:
                vmin += 1
            # simply because this is the highest v
            vmax = tmax * 2
            if vmax % 2 == 0:
                vmax += 1

            vrange = range(vmin, vmax, 2)
            for j, v in enumerate(vrange):
                # KRA1
                _n = n0 * p
                _k = (n0 - 1) * p
                _t = 2 * v
                # ncr(n0;2)
                red = log2(n0) + log2(n0 - 1) - 1
                res = get_complexity(_n, _k, _t)
                if res is None:
                    continue  # next v
                c_compl, q_compl = res
                caes = c_compl - red
                qaes = 2 * (q_compl - red)
                secure_ok_low = caes >= C_INTERVALS_FUNCTS[0](
                    c_lambd) and qaes >= Q_INTERVALS_FUNCTS[0](q_lambd)
                if not secure_ok_low:
                    continue  # not reaching min security, next v
                secure_ok_high = caes <= C_INTERVALS_FUNCTS[1](
                    c_lambd) and qaes <= Q_INTERVALS_FUNCTS[1](q_lambd)
                if not secure_ok_high:
                    break  # security too high, do not keep trying greater vs
                if j == 0:
                    vals = check_frontier(
                        True, caes, c_lambd, qaes, q_lambd,
                        f"- KRA1: p = {p}, n0 = {n0}, *v* = {t}! ", _n, _k, _t)
                    isd_values_to_compute.extend(vals)
                elif j == len(vrange) - 1:
                    vals = check_frontier(
                        False, caes, c_lambd, qaes, q_lambd,
                        f"- KRA1: p = {p}, n0 = {n0}, *v* = {t})! ", _n, _k,
                        _t)
                    isd_values_to_compute.extend(vals)
                complexities['KRA1'] = (caes, qaes)
                # KRA3
                _n = n0 * p
                _k = (n0 - 1) * p
                _t = n0 * v
                red = log2(p)
                res = get_complexity(_n, _k, _t)
                if res is None:
                    continue  # next t
                c_compl, q_compl = res
                caes = c_compl - red
                qaes = 2 * (q_compl - red)
                secure_ok_low = caes >= C_INTERVALS_FUNCTS[0](
                    c_lambd) and qaes >= Q_INTERVALS_FUNCTS[0](q_lambd)
                if not secure_ok_low:
                    continue  # not reaching min security, next v
                secure_ok_high = caes <= C_INTERVALS_FUNCTS[1](
                    c_lambd) and qaes <= Q_INTERVALS_FUNCTS[1](q_lambd)
                if not secure_ok_high:
                    break  # security too high, do not keep trying greater vs
                if j == 0:
                    vals = check_frontier(
                        True, caes, c_lambd, qaes, q_lambd,
                        f"- KRA3: p = {p}, n0 = {n0}, v = {t}! ", _n, _k, _t)
                    isd_values_to_compute.extend(vals)
                elif j == len(vrange) - 1:
                    vals = check_frontier(
                        False, caes, c_lambd, qaes, q_lambd,
                        f"- KRA3: p = {p}, n0 = {n0}, v = {t}! ", _n, _k, _t)
                    isd_values_to_compute.extend(vals)
                complexities['KRA3'] = (caes, qaes)

                if n0 != 2:
                    # KRA2
                    _n = n0 * p
                    _k = 2 * p
                    _t = 2 * v
                    red = log2(n0 * p)
                    res = get_complexity(_n, _k, _t)
                    if res is None:
                        continue  # next v
                    c_compl, q_compl = res
                    caes = c_compl - red
                    qaes = 2 * (q_compl - red)
                    secure_ok_low = caes >= C_INTERVALS_FUNCTS[0](
                        c_lambd) and qaes >= Q_INTERVALS_FUNCTS[0](q_lambd)
                    if not secure_ok_low:
                        continue  # not reaching min security, next v
                    secure_ok_high = caes <= C_INTERVALS_FUNCTS[1](
                        c_lambd) and qaes <= Q_INTERVALS_FUNCTS[1](q_lambd)
                    if not secure_ok_high:
                        break  # security too high, do not keep trying greater vs
                    if j == 0:
                        vals = check_frontier(
                            True, caes, c_lambd, qaes, q_lambd,
                            f"- KRA2: p = {p}, n0 = {n0}, v = {t}! ", _n, _k,
                            _t)
                        isd_values_to_compute.extend(vals)
                    elif j == len(vrange) - 1:
                        vals = check_frontier(
                            False, caes, c_lambd, qaes, q_lambd,
                            f"- KRA2: p = {p}, n0 = {n0}, v = {t}! ", _n, _k,
                            _t)
                        isd_values_to_compute.extend(vals)
                    complexities['KRA2'] = (c_compl - red, 2 * (q_compl - red))
                leda_values.append((p, n0, v, t, complexities))
                isd_values.append(Value(n, n - k, t))

            # end v loop
        # end t loop
    # end p, n0 loop

    return leda_values, set(isd_values), set(isd_values_to_compute)


def get_hardcoded_filenames():
    return [
        # "016342_008171_126.json",
        # "017338_008669_129.json",
        # "016442_008221_139.json",
        "013606_006803_130.json",
        "013606_006803_078.json",
        "013606_006803_098.json",
        "013606_006803_109.json",
        "013606_006803_114.json",
        "013606_006803_119.json",
        "013606_006803_124.json",
        "013606_006803_129.json",
        "013606_006803_082.json",
        "013606_006803_102.json",
        "013606_006803_110.json",
        "013606_006803_115.json",
        "013606_006803_120.json",
        "013606_006803_125.json",
        "013606_006803_130.json",
        "013606_006803_086.json",
        "013606_006803_106.json",
        "013606_006803_111.json",
        "013606_006803_116.json",
        "013606_006803_121.json",
        "013606_006803_126.json",
        "013606_006803_090.json",
        "013606_006803_107.json",
        "013606_006803_112.json",
        "013606_006803_117.json",
        "013606_006803_122.json",
        "013606_006803_127.json",
        "013606_006803_094.json",
        "013606_006803_108.json",
        "013606_006803_113.json",
        "013606_006803_118.json",
        "013606_006803_123.json",
        "013606_006803_128.json",
    ]


def main():
    init_logger(LOGGER, 'logs/isd_values_restrictions.log')
    # all nested keys are sorted
    filenames = os.listdir(OUT_FILES_CLEDA_TYPE_DIR.format(out_type='json'))
    # filenames = get_hardcoded_filenames()
    filenames_idx_by_p_sorted = get_filenames(filenames)
    leda_vals = {}
    isd_vals = set()
    print(f"Values available {len(filenames)}")
    for level, c_lambda, q_lambda in zip((1, 3, 5), AES_LAMBDAS, QAES_LAMBDAS):
        print(f" Level {level}: (AES, QAES) = ({c_lambda}, {q_lambda})")
        leda_values, isd_values, isd_values_to_compute = param(
            c_lambda,
            q_lambda,  # filenames,
            filenames_idx_by_p_sorted)
        print(f"LEDA values obtained: {len(leda_values)}")
        print(f"ISD values obtained {len(isd_values)}")
        print("*" * 80)
        leda_vals[level] = leda_values
        isd_vals.update(isd_values)
    with open(OUT_FILE_LEDA_VALS, 'w') as fp:
        json.dump(leda_vals, fp, indent=2)

    with open(OUT_FILE_ISD_VALS, 'w') as fp:
        json.dump([asdict(x) for x in sorted(isd_vals)], fp, indent=2)

    with open(OUT_FILE_ISD_VALS_TO_COMPUTE, 'w') as fp:
        json.dump([asdict(x) for x in sorted(isd_values_to_compute)],
                  fp,
                  indent=2)


if __name__ == '__main__':
    main()
