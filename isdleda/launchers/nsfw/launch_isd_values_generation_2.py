"""Generate a range of useful values for LEDA, based on the approximation of
Torres, Sendrier - PQCrypto 2016

"""
import functools
import itertools
import logging
import operator
import os
from dataclasses import asdict
from typing import Dict

import numpy as np
from isdleda.launchers.launcher_utils import (AES_LAMBDAS,
                                              get_proper_leda_primes,
                                              init_logger)
from isdleda.utils.common import Attacks, ISDValue
from isdleda.utils.export.export import load_from_json, save_to_json

# from isdleda.utils.paths import ISD_VALUES_FILE_JSON, ISD_VALUES_FILE_PKL
LOGGER = logging.getLogger(__name__)


def check_generated_in_dataset(n, k, t, attack, reduction, c_lambda):
    filename = f"out/cisd_leda/json/{n:06}_{k:06}_{t:03}.json"
    try:
        data = load_from_json(filename)
    except FileNotFoundError:
        LOGGER.debug(
            f"Value not present for ({filename}) (Attack: {attack}) -> Lambda: {c_lambda}"
        )
        return None

    c_time = data['Classic']['Plain']['value'] - reduction
    if .75 * c_lambda <= c_time <= 1.25 * c_lambda:
        return True
    LOGGER.warning(
        f"Wrong guess for {attack} to ({n}, {k}, {t}) -> Lambda: {c_lambda}, CTime w/out red {c_time + reduction:03f}; CTime w/ reduction: {c_time:03f}"
    )
    return False


# def add_to_dict(values: Dict[str, Value], n, r, t, prime, n0, v, lambd, msg):
def add_to_dict(values: Dict[str, ISDValue], n, r, t, msg):
    _key = f"{n}_{r}_{t}"
    if _key not in values:
        value = ISDValue(
            n=n,
            r=r,
            # This is the t used to assess the ISD attack
            t=t,
            msgs=[msg],
        )
        values[_key] = value
    else:
        _val = values[_key]
        _val.msgs.append(msg)


def main():
    init_logger(LOGGER, 'logs/launch_isd_values_generation.log')
    proper_primes = get_proper_leda_primes()
    assert proper_primes is not None
    n0_values = range(2, 6)

    # lambda_values = (128, 192, 256)
    lambda_values = AES_LAMBDAS
    values: Dict[str, ISDValue] = dict()

    acc = 0

    # Approximate ISD hardness (Sendrier method). Given the weight $w$ of
    # the codeword/error to be found and the code rate k/n=R, an ISD costs
    # approx 2^cw, where the constant c depends on the rate
    #
    # c = log_2(1/(1-R)) = -log_2(1-R) ;
    #
    # From 2^cw = 2^lambda, given lambda and n0, we first compute c,
    # and then
    #
    # w = lam/c
    #
    # If there's a reduction (f.e., bcz of quasi-cyclic), that is,
    # 2^{cw}/red, it becomes
    #
    # cw - log2(red) = lambda -> w = (lambda + log2(red)) / c
    #

    # MRA (SDP) ;
    # ISD(n, k, t); code rate (n0-1)/n0
    # c0 = -np.log2(1 - (n0 - 1) / n0)
    # t0 = np.ceil(lam / c0)
    # red0 = functools.partial(operator.add, 0)
    # NOTE: the ISD parameters in LEDA are (n, r, t) and not (n, k, t) as usual

    # functions return (c, w/v, n_fun, r_fun, v_fun, red)

    # KRA1 (CFP); ISD(n0*p,p,2*v) / (p*binom{n0}{2}); code rate (n0-1)/n0;
    # target weight = 2*v
    fun_kr1 = lambda n0: (
        -np.log2(1 - (n0 - 1) / n0),
        2,
        functools.partial(operator.mul, n0),  # miss p
        functools.partial(operator.mul, 1),  # miss p
        # functools.partial(operator.mul, 1/w_to_v1),  # miss v
        functools.partial(operator.add,
                          np.log2(n0)+ np.log2(n0 - 1))  # miss p
    )

    # KRA2 (CFP); ISD(2*p,p,2*v) / (n0*p); attacked code rate (1/2); target weight = 2v
    fun_kr2 = lambda n0: (
        -np.log2(1 - 1 / 2),
        2,
        functools.partial(operator.mul, 2),  # miss p
        functools.partial(operator.mul, 1),  # miss p
        # functools.partial(operator.mul, 1/w_to_v2),  # miss v
        functools.partial(
            operator.add,
            np.log2(n0),
        ))
    # KRA3 (CFP); ISD(n0*p,(n0-1)*p,n0*v) / p; attacked code rate 1/n0; target weight = n0*v
    fun_kr3 = lambda n0: (
        -np.log2(1 - 1 / n0),
        n0,
        functools.partial(operator.mul, n0),  # miss p
        functools.partial(operator.mul, n0 - 1),  # miss p
        # functools.partial(operator.mul, 1/w_to_v3),  # miss v
        functools.partial(operator.add, 0),
    )
    for n0, lam in itertools.product(n0_values, lambda_values):

        c1, w_to_v1, n1_fun, r1_fun, red1 = fun_kr1(n0)
        w1 = np.ceil(lam / (w_to_v1 * c1))

        c2, w_to_v2, n2_fun, r2_fun, red2 = fun_kr2(n0)
        w2 = np.ceil(lam / (w_to_v2 * c2))

        c3, w_to_v3, n3_fun, r3_fun, red3 = fun_kr3(n0)
        w3 = np.ceil(lam / (w_to_v3 * c3))

        for w, w_to_v, attack, n_fun, r_fun, red_fun, in zip(
            (w1, w2, w3),
                (w_to_v1, w_to_v2, w_to_v3),
            (Attacks.KeyR1, Attacks.KeyR2, Attacks.KeyR3),
            (n1_fun, n2_fun, n3_fun),
            (r1_fun, r2_fun, r3_fun),
            (red1, red2, red3),
        ):
            if n0 == 2 and attack == Attacks.KeyR2:
                continue
            v_min = int(np.floor(.9 * w))
            if v_min % 2 == 0: v_min -= 1
            v_max = int(np.floor(1.2 * w))
            if v_min % 2 == 0: v_min += 1
            step = 2

            for v in range(v_min, v_max, step):
                # For LDPC, n0*v = log(n) = log(p*n0) = log(p) + log(n0) -> log(p) = n0*v - log(n0) -> p = 2^(n0*v - log(n0))
                #
                # For MDPC, n0*v = sqrt(n*log(n)) = sqrt(p*n0*log(p*n0)) -> (n0 * v)^2 = p * n0 * (log(p)+log(n0)) 
                # 
                # Removing the log factors, we have p = (n0 * v)^2 / n0
                prime_guess_max = 1.1 * (2**(n0*v - np.log2(n0)))
                prime_guess_min = .8 * ((n0*v)**2)/n0
                prime_range = filter(
                    lambda p: prime_guess_min <= p <= 1.2 * prime_guess_max,
                    proper_primes)
                for prime in prime_range:
                    n = n_fun(prime)
                    r = r_fun(prime)
                    k = n - r
                    weight = v * w_to_v
                    red = red_fun(np.log2(prime))
                    is_admissible = check_generated_in_dataset(
                        n, k, weight, attack, red, lam)
                    if is_admissible is None or is_admissible == True:
                        add_to_dict(values, n, r, weight, attack)
                    else:
                        acc += 1
                    if attack == Attacks.KeyR1:
                        # The minimum distance of the code is 2v/w_to_v? (LEDA specs., pg. 41).
                        # So, we can correct up to t = v/w_to_v errors. Hence t <= v/(w_to_v)
                        t_max = v
                        for t in range(int(np.floor(.8 * t_max)),
                                       int(np.floor(1.2 * t_max)), 1):
                            is_admissible = check_generated_in_dataset(
                                n, k, t, attack, red, lam)
                            if is_admissible is None or is_admissible == True:
                                add_to_dict(values, n, r, t, Attacks.MsgR)
                            else:
                                acc += 1

    print(f"Wrong values {acc}")
    print(f"Admissible values {len(values)}")
    values_set = set(values.values())
    # print(f"Pickling to {ISD_VALUES_FILE_PKL}")
    # save_to_pickle(ISD_VALUES_FILE_PKL, values_set)
    filename = os.path.join("out", "values", "from_generation",
                            "isd_values.json")
    print(f"JSONing to {filename}")
    save_to_json(filename, [asdict(x) for x in sorted(values_set)])


if __name__ == '__main__':
    main()
