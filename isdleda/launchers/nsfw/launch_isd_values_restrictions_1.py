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
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from isdleda.launchers.launcher_utils import get_proper_leda_primes, init_logger, AES_LAMBDAS, QAES_LAMBDAS
from isdleda.utils.common import ISDValue, LEDAValue
from isdleda.utils.export.export import save_to_json
from isdleda.utils.paths import OUT_FILES_CLEDA_FMT
from numpy import ceil, log2, floor
from sortedcontainers import SortedDict

LOGGER = logging.getLogger(__name__)

OUT_FILE_LEDA_VALS = 'out/values/from_restrictions/leda_values.json'
OUT_FILE_ISD_VALS = 'out/values/from_restrictions/isd_values.json'
OUT_FILE_ISD_VALS_TO_COMPUTE = 'out/values/from_restrictions/isd_values_to_compute.json'

LEDA_PRIMES = get_proper_leda_primes()


@dataclass
class Bound:
    target: float
    L: float
    L1: float
    L2: float
    H: float
    H1: float
    H2: float


def init_bounds(c_lambda, q_lambda) -> Tuple[Bound, Bound]:
    """
    ...|-----|-----|----------|---------|---|----|...
       L    L1    L2       lambda      H2  H1    H
    - {L, H}: region wort exploring (interval of lambda)
    - {L, L1}: if we have the first exploration value having complexity X, with L < X < L1, we generate additional (lower) t's 
    - {L1, L2}: if we have ...., with L1 < X < L2, we generate additional (lower) ps and n0s
    - dual for the higher values
    """
    Lc = C_INTERVALS_FUNCTS[0](c_lambda)
    Lq = Q_INTERVALS_FUNCTS[0](q_lambda)
    L1c = C_INTERVALS_FUNCTS_Lis[0](Lc)
    L2c = C_INTERVALS_FUNCTS_Lis[1](L1c)
    L1q = Q_INTERVALS_FUNCTS_Lis[0](Lq)
    L2q = Q_INTERVALS_FUNCTS_Lis[1](L1q)

    Hc = C_INTERVALS_FUNCTS[1](c_lambda)
    Hq = Q_INTERVALS_FUNCTS[1](q_lambda)
    H1c = C_INTERVALS_FUNCTS_His[0](Hc)
    H2c = C_INTERVALS_FUNCTS_His[1](H1c)
    H1q = Q_INTERVALS_FUNCTS_His[0](Hq)
    H2q = Q_INTERVALS_FUNCTS_His[1](H1q)

    return Bound(c_lambda, Lc, L1c, L2c, Hc, H1c, H2c), Bound(q_lambda, Lq, L1q, L2q, Hq, H1q, H2q)


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

C_INTERVALS_FUNCTS_Lis = (functools.partial(operator.mul, 1.1),
                          functools.partial(operator.mul, 1.05))
Q_INTERVALS_FUNCTS_Lis = (functools.partial(operator.mul, 1.1),
                          functools.partial(operator.mul, 1.05))
C_INTERVALS_FUNCTS_His = (functools.partial(operator.mul, .9),
                          functools.partial(operator.mul, .95))
Q_INTERVALS_FUNCTS_His = (functools.partial(operator.mul, .9),
                          functools.partial(operator.mul, .95))

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


def generate_new_t_values(lower, c_bounds, q_bounds, n, k, t):
    isd_values = []
    c = -log2(1 - k / n)
    if lower:
        trange = range(int(.9 * floor(c_bounds.l1/c)), int(1.1 * floor(c_bounds.target/c)), 3)
    else:
        trange = range(int(.9 * ceil(c_bounds.h1/c)), int(1.1 * ceil(c_bounds.target/c)), 3)
    for tnew in trange:
        isd_values.append(ISDValue(n, n-k, tnew))
    return isd_values

def generate_new_p_n0_values(lower, n, k, t):
    # In theory we can still use the Torres, Sendrier approximation. Since we
    # used it in the generation phase, however, here we want to explore a wider
    # range .
    p = n - k
    n0 = n/p
    isd_values = []
    if not n0.is_integer():
        return isd_values
    n0 = int(n0)
    if lower:
        if n0>2:
            n0new = n0 - 1
            isd_values.append(ISDValue(p *n0new, p * (n0new - 1), t))
        
        primes_range = filter(lambda prime: prime <= int(.9 * p), LEDA_PRIMES)
        for prime in primes_range:
            isd_values.append(ISDValue(prime * n0, prime * (n0-1), t))
    else:
        if n0<6:
            n0new = n0 + 1
            isd_values.append(ISDValue(p *n0new, p * (n0new - 1), t))
        
        primes_range = filter(lambda prime: prime <= int(1.1 * p), LEDA_PRIMES)
        for prime in primes_range:
            isd_values.append(ISDValue(prime * n0, prime * (n0-1), t))



def check_frontier(lower: bool, caes: float, qaes: float, c_bounds: Bound, q_bounds: Bound,
                   n: int, k: int, t: int):
    """Either low or up frontier"""
    # exploring_range
    # low (i.e., first value explored) and (caes> c_lambda - 20 or qaes> q_lambda - 20)
    if lower:
        if caes > c_bounds.L and qaes > q_bounds.L:
            if caes < c_bounds.L1 and qaes < q_bounds.L2:
                # |---X---|
                # L       L1
                return generate_new_t_values(True, c_bounds, q_bounds, n, k, t)
            elif caes < c_bounds.L2 and qaes < q_bounds.L2:
                # |---X---|
                # L1      L2
                return generate_new_p_n0_values(True, n, k, t)
    if not lower:
        if caes < c_bounds.H and qaes < q_bounds.H:
            if caes > c_bounds.H1 and qaes > q_bounds.H2:
                return generate_new_t_values(False, c_bounds, q_bounds, n, k, t)
            elif caes > c_bounds.H2 and qaes > q_bounds.H2:
                return generate_new_p_n0_values(False, n, k, t)

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
                return cval + 2 * (t - _t), qval + (t - _t)
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


def loop_complexity(n, k, t, red, iteration: int, c_bounds: Bound, q_bounds: Bound):
    # iteration_first is 0 if it's the first iteration, 1 if it's the last, 2
    # if none of the two

    # continue, break, results
    ret_val = [False, False, None]
    res = get_complexity(n, k, t)
    if res is None:
        ret_val[0] = True  # next t
        return ret_val
    c_compl, q_compl = res
    caes = c_compl - red
    # For the quantum part, the threshold values are given by twice the
    # depth of the circuit (check Eq. 6.6 of my phd.thesis)
    qaes = 2 * (q_compl - red)
    caes_diff_low = caes - c_bounds.L  # caes < L
    qaes_diff_low = qaes - q_bounds.L
    caes_diff_high = caes - c_bounds.H  # caes > H
    qaes_diff_high = qaes - q_bounds.H
    if caes_diff_low <= 0 or qaes_diff_low <= 0:
        ret_val[0] = True
    if caes_diff_high >= 0 or qaes_diff_high >= 0:
        ret_val[1] = True
    if iteration == 0:
        vals = check_frontier(True, caes, qaes, c_bounds, q_bounds, n,
                              k, t)
    elif iteration == 1:
        vals = check_frontier(False, caes, qaes, c_bounds, q_bounds, n,
                              k, t)
    else:
        vals = []
    ret_val[2] = (caes, qaes, vals)
    return ret_val


def check_mra(p, n0, trange, c_bounds, q_bounds):
    isd_values_to_compute = []
    complexities_by_t = {}
    for i, t in enumerate(trange):
        _n = p * n0
        _r = p
        _k = _n - _r
        _w = t
        # DOOM
        red = log2(p) / 2
        if i == 0:
            it = 0
        elif i == len(trange) - 1:
            it = 1
        else:
            it = 2
        ret_val = loop_complexity(_n, _k, _w, red, it, c_bounds, q_bounds)
        if ret_val[0]:
            continue  # next t
        if ret_val[1]:
            break
        caes, qaes, vals_to_compute = ret_val[2]
        isd_values_to_compute.extend(vals_to_compute)
        complexities_by_t[t] = (caes, qaes)
    return complexities_by_t, isd_values_to_compute


def check_kra(p, n0, t, vmin, vmax, c_bounds: Bound, q_bounds: Bound, complexities,
              min_complexity_c, min_complexity_q):
    isd_values_to_compute = []
    leda_values = []

    vrange = range(vmin, vmax + 1, 2)

    for j, v in enumerate(vrange):
        # KRA1
        _n = n0 * p
        _k = (n0 - 1) * p
        _w = 2 * v
        # explicit ncr(n0;2)
        red = log2(n0) + log2(n0 - 1) - 1
        if j == 0:
            it = 0
        elif j == vmax:
            it = 1
        else:
            it = 2
        ret_val = loop_complexity(_n, _k, _w, red, it, c_bounds, q_bounds)
        if ret_val[0]:
            continue  # next t
        if ret_val[1]:
            break
        caes, qaes, vals_to_compute = ret_val[2]
        isd_values_to_compute.extend(vals_to_compute)
        complexities['KRA1'] = (caes, qaes)
        min_complexity_c = caes if caes < min_complexity_c else min_complexity_c
        min_complexity_q = qaes if qaes < min_complexity_q else min_complexity_q

        # KRA3
        _n = n0 * p
        _k = p
        _w = n0 * v
        red = log2(p)
        if j == 0:
            it = 0
        elif j == vmax:
            it = 1
        else:
            it = 2
        ret_val = loop_complexity(_n, _k, _w, red, it, c_bounds, q_bounds)
        if ret_val[0]:
            continue  # next t
        if ret_val[1]:
            break
        caes, qaes, vals_to_compute = ret_val[2]
        isd_values_to_compute.extend(vals_to_compute)
        complexities['KRA3'] = (caes, qaes)
        min_complexity_c = caes if caes < min_complexity_c else min_complexity_c
        min_complexity_q = qaes if qaes < min_complexity_q else min_complexity_q

        if n0 != 2:
            # KRA2
            _n = 2 * p
            _k = p
            _w = 2 * v
            red = log2(n0 * p)

            if j == 0:
                it = 0
            elif j == vmax:
                it = 1
            else:
                it = 2
            ret_val = loop_complexity(_n, _k, _w, red, it, c_bounds, q_bounds)
            if ret_val[0]:
                continue  # next t
            if ret_val[1]:
                break
            caes, qaes, vals_to_compute = ret_val[2]
            isd_values_to_compute.extend(vals_to_compute)
            complexities['KRA3'] = (caes, qaes)
            min_complexity_c = caes if caes < min_complexity_c else min_complexity_c
            min_complexity_q = qaes if qaes < min_complexity_q else min_complexity_q

        complexities['Minimum'] = (min_complexity_c, min_complexity_q)

        # v_totally_explored += 1
        leda_values.append(
            LEDAValue(p=p,
                      n0=n0,
                      t=t,
                      v=v,
                      msgs=[f"Complexities: {complexities}"]))
    return leda_values, isd_values_to_compute


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

    c_bounds, q_bounds = init_bounds(c_lambda, q_lambda)

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
            complexities_by_t, _isd_values_to_compute = check_mra(
                p, n0, trange, c_bounds, q_bounds)
            isd_values_to_compute.extend(_isd_values_to_compute)
            # n_ts_explored = len(complexities_by_t)#

            for t, (caes, qaes) in complexities_by_t.items():
                complexities['MRA'] = (caes, qaes)
                min_complexity_c, min_complexity_q = caes, qaes

                # Due to minimum distance constraints, it has to hold that n0 *
                # v > 2*t. Hence, v > 2*t/n0. Seems wrong.
                #
                # vmin = int(2 * t / n0).
                # Counterexample, first row of [Annechini et. al, Table 1]: n0
                # = 2, t = 130, v = 71

                # The minimum distance of the code is 2v (LEDA specs., pg. 41).
                # So, we can correct up to t errors. Hence t <= 2v -> v >= t/2
                vmin = int(t / 2)
                if vmin % 2 == 0:
                    vmin -= 1
                # arbitrary end range, should end way before
                vmax = tmax * 3
                if vmax % 2 == 0:
                    vmax += 1

                leda_values, _isd_values_to_compute = check_kra(
                    p, n0, t, vmin, vmax, c_bounds, q_bounds, complexities,
                    min_complexity_c, min_complexity_q)
                isd_values_to_compute.extend(_isd_values_to_compute)
                isd_values.append(ISDValue(p * n0, p * (n0 - 1), t))
            # end t loop
        # end n0
    # end p loop

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


def get_hardcoded_filenames_2():
    return [
        '526508_394881_342.json', '555188_416391_732.json',
        '250804_188103_524.json', '320204_240153_144.json',
        '193484_145113_222.json', '331532_248649_540.json',
        '280268_210201_524.json', '582644_436983_378.json',
        '138668_104001_412.json', '111764_083823_075.json',
        '458284_343713_732.json', '217748_163311_452.json',
        '243284_182463_132.json', '328204_246153_612.json',
        '553396_415047_684.json', '132716_099537_182.json',
        '202508_151881_468.json', '370828_278121_278.json',
        '260108_195081_262.json', '112724_084543_364.json',
        '599212_449409_764.json', '130015_104012_365.json',
        '675295_540236_895.json', '092305_073844_058.json',
        '534745_427796_274.json', '671095_536876_354.json',
        '111415_089132_142.json', '255665_204532_535.json',
        '073265_058612_051.json', '093185_074548_064.json',
        '579295_463436_294.json', '101095_080876_081.json',
        '247615_198092_096.json', '743615_594892_885.json',
        '475105_380084_254.json', '078305_062644_105.json',
        '318865_255092_585.json', '473905_379124_675.json',
        '709265_567412_905.json', '587135_469708_755.json',
        '534295_427436_286.json', '063095_050476_245.json',
        '182319_121546_471.json', '044529_029686_201.json',
        '193359_128906_318.json', '091983_061322_214.json',
        '363057_242038_197.json', '149007_099338_429.json',
        '211503_141002_294.json', '207777_138518_152.json',
        '146721_097814_246.json', '084633_056422_092.json',
        '324183_216122_549.json', '057711_038474_087.json',
        '281433_187622_362.json', '044151_029434_219.json',
        '183999_122666_270.json', '080583_053722_099.json',
        '337521_225014_354.json', '260583_173722_189.json',
        '129849_086566_262.json', '038769_025846_135.json',
        '096927_064618_218.json'
    ]


def main():
    init_logger(LOGGER, 'logs/isd_values_restrictions.log')
    # all nested keys are sorted
    # filenames = os.listdir(OUT_FILES_CLEDA_TYPE_DIR.format(out_type='json'))
    filenames = get_hardcoded_filenames_2()
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
