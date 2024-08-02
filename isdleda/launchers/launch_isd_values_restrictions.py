"""Given all the already computed (classical, quantum) values (possibly
produced by the launch_isd_values_generation tool), this tool tries to produce:
- a list of plausible (p, n0, v) LEDA values to explore - the corresponding (n,
k, t) ISD values useful for a generic ISD exploration - the missing (n, k, t)
ISD values that have to be computed; if the dataset misses some values that
this tool deems worth exploring, it produces all those values

"""
import functools
import json
import logging
import operator
import os
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from isdleda.launchers.launcher_utils import init_logger, AES_LAMBDAS, QAES_LAMBDAS
from isdleda.utils.common import ISDValue, LEDAValue
from isdleda.utils.export.export import save_to_json
from isdleda.utils.paths import OUT_FILES_CLEDA_FMT, OUT_FILES_CLEDA_TYPE_DIR
from numpy import log2
from sortedcontainers import SortedDict

LOGGER = logging.getLogger(__name__)

OUT_FILE_LEDA_VALS = 'out/values/from_restrictions/leda_values.json'
OUT_FILE_ISD_VALS = 'out/values/from_restrictions/isd_values.json'
OUT_FILE_ISD_VALS_TO_COMPUTE = 'out/values/from_restrictions/isd_values_to_compute.json'

# We want to explore the region around a given lambda; that is, [lamba + val[0], lambda + val[1]]
# C_INTERVALS_FUNCTS = (functools.partial(operator.add, -30),
#                       functools.partial(operator.add, 30))
# I am less conservative with quantum. If there's a classical speed-up of X,
# the quantum speed-up would roughly be sqrt(X)
# Q_INTERVALS_FUNCTS = (functools.partial(operator.add, -20),
#                       functools.partial(operator.add, 20))
C_INTERVALS_FUNCTS = (functools.partial(operator.mul, .8),
                      functools.partial(operator.mul, 1.2))
# Bigger confidence interval for quantum since there may be other breakthroughs
Q_INTERVALS_FUNCTS = (functools.partial(operator.mul, .7),
                      functools.partial(operator.mul, 1.3))

# We want to emit warning if the first value explored is too close to the
# actual value. F.e., if we have a target lambda of 100, and the first (lowest)
# t explored produces a lambda = 98, we started the exploration from a value
# which is too close to the frontier. The same applies for the upper bound, so
# f.e. at the last iteration we have a value of 102.
#
# These intervals are interpred as: If first value explored and CAES >= lambda
# * val[0] -> WARN. If last value explored and CAES <= lambda + val[1] -> WARN

C_INTERVALS_WARN_FUNCTS = (functools.partial(operator.add, -25),
                           functools.partial(operator.add, +25))
Q_INTERVALS_WARN_FUNCTS = (functools.partial(operator.add, -20),
                           functools.partial(operator.add, +20))
# C_INTERVALS_WARN_FUNCTS = C_INTERVALS_FUNCTS
# Q_INTERVALS_WARN_FUNCTS = Q_INTERVALS_FUNCTS


def generate_new_t_values(n, k, t, caes_diff, qaes_diff, lower):
    isd_values = []
    if lower:
        parameter = -90
        step = -1
    else:
        parameter = 90
        step = 1

    for i in range(int(parameter * 1 / max(caes_diff, qaes_diff, 1)), step, 3):
        if i < 0 and lower: break
        val = ISDValue(n, n - k, t + i)
        isd_values.append(val)
    return isd_values


def check_frontier(low: bool, caes: float, c_lambda: int, qaes: float,
                   q_lambda: int, msg: str, n: int, k: int, t: int):
    """Either low or up frontier"""
    # exploring_range
    # low (i.e., first value explored) and (caes> c_lambda - 20 or qaes> q_lambda - 20)
    caes_diff = caes - C_INTERVALS_WARN_FUNCTS[0](c_lambda)
    qaes_diff = qaes - Q_INTERVALS_WARN_FUNCTS[0](q_lambda)
    if low and (caes_diff > 0 or qaes_diff > 0):
        LOGGER.warning(f"WARNING: lower frontier! ")
        LOGGER.warning(msg)
        LOGGER.warning(f"(c_lambda, q_lambda) = ({c_lambda, q_lambda})")
        LOGGER.warning(f"(c_aes, q_aes) = ({caes, qaes})")
        LOGGER.warning(f"{n:06}_{k:06}_{t:03}")
        return generate_new_t_values(n, k, t, caes_diff, qaes_diff, True)
        # decrease the t of a value inversely proportional to the max difference
    # high (i.e., last value explored) and (caes< c_lambda + 20 or qaes< q_lambda + 20)

    caes_diff = caes - C_INTERVALS_WARN_FUNCTS[1](c_lambda)
    qaes_diff = qaes - Q_INTERVALS_WARN_FUNCTS[1](q_lambda)
    if not low and (caes_diff < 0 or qaes_diff < 0):
        LOGGER.warning("WARNING: upper frontier! ")
        LOGGER.warning(msg)
        LOGGER.warning(f"(c_lambda, q_lambda) = ({c_lambda, q_lambda})")
        LOGGER.warning(f"(c_aes, q_aes) = ({caes, qaes})")
        LOGGER.warning(f"{n:06}_{k:06}_{t:03}")
        return generate_new_t_values(n, k, t, caes_diff, qaes_diff, False)

    return []


def get_complexity(n, k, t) -> Optional[Tuple[float, float]]:
    # WARN: we iterate on all the values close to t. The rationale is that, in
    # this module, we are trying to create a range of parameters to explore,
    # and varying the t shouldn't affect the values too much.
    #
    # To have a reference, taking the lowest n for leda, and using a (-4, +4)
    # on t, results in a (-4, +4) on the (log2) classical complexity. On the
    # other hand, taking the highest n, it results in (-8, +8).
    #
    # To have a quick reasonable compensation, I approximately add the diff
    # 2*(t - _t) to the result. For the quantum side, these values are halved.

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
                return cval + 2*(t - _t), qval + (t - _t)
    return None


# Define the nested defaultdict initialization
def _nested_dict():
    return defaultdict(_nested_dict)


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
    # filenames = [Path(x).stem for x in filenames]

    filenames_idx_by_p: Dict[int, Dict[int,
                                       Dict[int,
                                            str]]] = defaultdict(_nested_dict)
    for fname in filenames:
        n, k, t = [int(x) for x in Path(fname).stem.split('_')]
        p = n - k
        n0 = n // p

        # pdic = filenames_idx_by_p.get(p, {})
        # n0dic = pdic.get(n0, {})
        # tdic = n0dic.get(t, {})
        filenames_idx_by_p[p][n0][t] = fname
    # return filenames_idx_by_p
    filenames_idx_by_p_sorted = _convert_to_sorteddict(filenames_idx_by_p)
    return filenames_idx_by_p_sorted


def param(
    c_lambda: int,
    q_lambda: int,
    filenames_idx_by_p: Dict[int, Dict[int, Dict[int, str]]],
) -> Tuple[Set[LEDAValue], Set[ISDValue], Set[ISDValue]]:
    # While the filenames_idx_by_p are dictionaries, the function expects
    # SortedDict instances. The package does not have any type information
    # available.

    # LEDA values having complexities in the interval around the given
    # c_lambdaa/q_lambdaa. Each entry is a tuple (p, n0, v, t), with an
    # additional message of (C_complexity, Q_complexity)
    leda_values: List[LEDAValue] = []

    # ISD values in the intervals around the lambda values. Each entry is an
    # ISDValue with (n, r, t)
    isd_values: List[ISDValue] = []

    # ISD values missing from the dataset. These values are generated because
    # the explorations of the v's and t's parameters was not exhaustive, since
    # some values were missing.
    isd_values_to_compute: List[ISDValue] = []

    # These keys are sorted
    ps = [*filenames_idx_by_p]
    # pmin, pmax = ps[0], ps[-1]  # min value of r given the filenames
    # to_generate: Set[Value]
    nrange = range(2, 6)
    for p in ps:
        for n0 in nrange:
            complexities: Dict[str, Tuple[float, float]] = {}
            complexities["Target"] = (c_lambda, q_lambda)
            min_complexity_c: int
            min_complexity_q: int
            try:
                ts = [*filenames_idx_by_p[p][n0]]
            except KeyError:
                continue  # next n0
            tmin, tmax = ts[0], ts[-1]
            # Sweep all the t values in the range, even if not present in the
            # dataset. Note that even if the t is not present, the complexity
            # values are still approximated (if possible) using the closest t
            # value.
            trange = range(tmin, tmax + 1)
            n_ts_explored = 0
            for i, t in enumerate(trange):
                _n = p * n0
                _r = p
                _k = _n - _r
                _w = t
                # MRA
                res = get_complexity(_n, _k, _w)
                if res is None:
                    continue  # next t
                n_ts_explored += 1
                c_compl, q_compl = res
                # DOOM
                red = log2(p) / 2
                caes = c_compl - red
                # For the quantum part, the threshold values are given by twice the
                # depth of the circuit (check Eq. 6.6 of my phd.thesis)
                qaes = 2 * (q_compl - red)
                caes_diff_low = caes - C_INTERVALS_FUNCTS[0](c_lambda)
                qaes_diff_low = qaes - Q_INTERVALS_FUNCTS[0](q_lambda)
                caes_diff_high = caes - C_INTERVALS_FUNCTS[1](c_lambda)
                qaes_diff_high = qaes - Q_INTERVALS_FUNCTS[1](q_lambda)
                if caes_diff_low <= 0 or qaes_diff_low <= 0:
                    continue  # next t
                if caes_diff_high >= 0 or qaes_diff_high >= 0:
                    if i != 0 and n_ts_explored == 0:
                        # TODO double check
                        generate_new_t_values(_n, _k, _w, caes_diff_low,
                                              qaes_diff_low, True)
                    break  # do not keep increasing the ts, it's useless, we'll have higher values

                if i == 0:
                    vals = check_frontier(
                        True, caes, c_lambda, qaes, q_lambda,
                        f"- MRA: p = {p}, n0 = {n0}, *t* = {t}! ", _n, _k, _w)
                    isd_values_to_compute.extend(vals)
                elif i == len(trange) - 1:
                    vals = check_frontier(
                        False, caes, c_lambda, qaes, q_lambda,
                        f"- MRA: p = {p}, n0 = {n0}, *t* = {t}! ", _n, _k, _w)
                    isd_values_to_compute.extend(vals)
                complexities['MRA'] = (caes, qaes)
                min_complexity_c, min_complexity_q = caes, qaes

                # Due to minimum distance constraints, it has to hold that n0 v
                # > 2 t. Hence, v > 2t/n0
                vmin = int(2 * t / n0)
                # vmin should be odd
                if vmin % 2 == 0:
                    vmin += 1
                # arbitrary end range
                vmax = tmax * n0
                if vmax % 2 == 0:
                    vmax += 1

                vrange = range(vmin, vmax + 1, 2)
                for j, v in enumerate(vrange):
                    # KRA1
                    _n = n0 * p
                    _k = (n0 - 1) * p
                    _w = 2 * v
                    # explicit ncr(n0;2)
                    red = log2(n0) + log2(n0 - 1) - 1
                    res = get_complexity(_n, _k, _w)
                    if res is None:
                        continue  # next v
                    c_compl, q_compl = res
                    caes = c_compl - red
                    qaes = 2 * (q_compl - red)
                    secure_ok_low = caes >= C_INTERVALS_FUNCTS[0](
                        c_lambda) and qaes >= Q_INTERVALS_FUNCTS[0](q_lambda)
                    if not secure_ok_low:
                        continue  # not reaching min security, next v
                    secure_ok_high = caes <= C_INTERVALS_FUNCTS[1](
                        c_lambda) and qaes <= Q_INTERVALS_FUNCTS[1](q_lambda)
                    if not secure_ok_high:
                        if i != 0 and n_ts_explored == 0:
                            # TODO double check
                            generate_new_t_values(_n, _k, _w, caes_diff_low,
                                                  qaes_diff_low, True)
                        break  # security too high, do not keep trying greater vs
                    if j == 0:
                        vals = check_frontier(
                            True, caes, c_lambda, qaes, q_lambda,
                            f"- KRA1: p = {p}, n0 = {n0}, *v* = {t}!", _n, _k,
                            _w)
                        isd_values_to_compute.extend(vals)
                    elif j == len(vrange) - 1:
                        vals = check_frontier(
                            False, caes, c_lambda, qaes, q_lambda,
                            f"- KRA1: p = {p}, n0 = {n0}, *v* = {t})!", _n, _k,
                            _w)
                        isd_values_to_compute.extend(vals)
                    complexities['KRA1'] = (caes, qaes)
                    min_complexity_c = caes if caes < min_complexity_c else min_complexity_c
                    min_complexity_q = qaes if qaes < min_complexity_q else min_complexity_q
                    # KRA3
                    _n = n0 * p
                    # NOTE: the original formulation has _k = p, and hence _k < _r,
                    # since we're considering the dual code.
                    _k = p
                    _w = n0 * v
                    red = log2(p)
                    res = get_complexity(_n, _k, _w)
                    if res is None:
                        continue  # next t
                    c_compl, q_compl = res
                    caes = c_compl - red
                    qaes = 2 * (q_compl - red)
                    secure_ok_low = caes >= C_INTERVALS_FUNCTS[0](
                        c_lambda) and qaes >= Q_INTERVALS_FUNCTS[0](q_lambda)
                    if not secure_ok_low:
                        continue  # not reaching min security, next v
                    secure_ok_high = caes <= C_INTERVALS_FUNCTS[1](
                        c_lambda) and qaes <= Q_INTERVALS_FUNCTS[1](q_lambda)
                    if not secure_ok_high:
                        if i != 0 and n_ts_explored == 0:
                            # TODO double check
                            generate_new_t_values(_n, _k, _w, caes_diff_low,
                                                  qaes_diff_low, True)
                    if j == 0:
                        vals = check_frontier(
                            True, caes, c_lambda, qaes, q_lambda,
                            f"- KRA3: p = {p}, n0 = {n0}, v = {t}! ", _n, _k,
                            _w)
                        isd_values_to_compute.extend(vals)
                    elif j == len(vrange) - 1:
                        vals = check_frontier(
                            False, caes, c_lambda, qaes, q_lambda,
                            f"- KRA3: p = {p}, n0 = {n0}, v = {t}! ", _n, _k,
                            _w)
                        isd_values_to_compute.extend(vals)
                    complexities['KRA3'] = (caes, qaes)
                    min_complexity_c = caes if caes < min_complexity_c else min_complexity_c
                    min_complexity_q = qaes if qaes < min_complexity_q else min_complexity_q

                    if n0 != 2:
                        # KRA2
                        _n = 2 * p
                        _k = p
                        _w = 2 * v
                        red = log2(n0 * p)
                        res = get_complexity(_n, _k, _w)
                        if res is None:
                            continue  # next v
                        c_compl, q_compl = res
                        caes = c_compl - red
                        qaes = 2 * (q_compl - red)
                        secure_ok_low = caes >= C_INTERVALS_FUNCTS[0](
                            c_lambda) and qaes >= Q_INTERVALS_FUNCTS[0](
                                q_lambda)
                        if not secure_ok_low:
                            continue  # not reaching min security, next v
                        secure_ok_high = caes <= C_INTERVALS_FUNCTS[1](
                            c_lambda) and qaes <= Q_INTERVALS_FUNCTS[1](
                                q_lambda)
                        if not secure_ok_high:
                            if i != 0 and n_ts_explored == 0:
                                # TODO double check
                                generate_new_t_values(_n, _k, _w,
                                                      caes_diff_low,
                                                      qaes_diff_low, True)
                        if j == 0:
                            vals = check_frontier(
                                True, caes, c_lambda, qaes, q_lambda,
                                f"- KRA2: p = {p}, n0 = {n0}, v = {t}! ", _n,
                                _k, _w)
                            isd_values_to_compute.extend(vals)
                        elif j == len(vrange) - 1:
                            vals = check_frontier(
                                False, caes, c_lambda, qaes, q_lambda,
                                f"- KRA2: p = {p}, n0 = {n0}, v = {t}! ", _n,
                                _k, _w)
                            isd_values_to_compute.extend(vals)
                        complexities['KRA2'] = (c_compl - red,
                                                2 * (q_compl - red))
                        min_complexity_c = caes if caes < min_complexity_c else min_complexity_c
                        min_complexity_q = qaes if qaes < min_complexity_q else min_complexity_q
                    complexities['Minimum'] = (min_complexity_c,
                                               min_complexity_q)
                    leda_values.append(
                        LEDAValue(p=p,
                                  n0=n0,
                                  t=t,
                                  v=v,
                                  msgs=[f"Complexities: {complexities}"]))
                    isd_values.append(ISDValue(p * n0, p * (n0 - 1), t))

                # end v loop
            # end t loop
        # end p
    # end n0 loop

    return set(leda_values), set(isd_values), set(isd_values_to_compute)


def get_hardcoded_filenames():
    """just for quick testing"""
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
    # These are values worth exploring, and should be categorized per security level
    leda_vals = {}
    # These are values that we deem worthful exploring for ISD attack
    isd_vals: Set[ISDValue] = set()
    # These are values that we deem worthful exploring for ISD attack, but for
    # which no computation still exists
    isd_vals_to_compute: Set[ISDValue] = set()

    print(f"Values available {len(filenames)}")
    print("*" * 80)
    acc_leda = 0
    for level, c_lambda, q_lambda in zip((1, 3, 5), AES_LAMBDAS, QAES_LAMBDAS):
        print(f"Level {level}: (AES, QAES) = ({c_lambda}, {q_lambda})")
        leda_values, isd_values, isd_values_to_compute = param(
            c_lambda,
            q_lambda,  # filenames,
            filenames_idx_by_p_sorted)
        acc_leda += len(leda_values)
        print(f"LEDA values obtained: {len(leda_values)}")
        print(f"ISD values obtained {len(isd_values)}")
        print(f"ISD values to compute obtained {len(isd_values_to_compute)}")
        print("*" * 80)
        leda_vals[level] = [asdict(x) for x in sorted(leda_values)]
        isd_vals.update(isd_values)
        isd_vals_to_compute.update(isd_values_to_compute)

    print(f"LEDA values TOTAL {acc_leda}")
    print(f"ISD values TOTAL {len(isd_vals)}")
    print(f"ISD values to compute TOTAL {len(isd_vals_to_compute)}")

    save_to_json(OUT_FILE_LEDA_VALS, leda_vals)
    save_to_json(OUT_FILE_ISD_VALS, [asdict(x) for x in sorted(isd_vals)])
    save_to_json(OUT_FILE_ISD_VALS_TO_COMPUTE,
                 [asdict(x) for x in sorted(isd_vals_to_compute)])


if __name__ == '__main__':
    main()
