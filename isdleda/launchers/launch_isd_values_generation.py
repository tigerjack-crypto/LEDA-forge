"""Generate a range of useful values for LEDA, based on the approximation of
Torres, Sendrier - PQCrypto 2016

"""
import csv
import itertools
import os
from dataclasses import asdict
from typing import Dict

import numpy as np
from isdleda.utils.common import ISDValue
from isdleda.utils.export.export import save_to_json

# from isdleda.utils.paths import ISD_VALUES_FILE_JSON, ISD_VALUES_FILE_PKL


# def add_to_dict(values: Dict[str, Value], n, r, t, prime, n0, v, lambd, msg):
def add_to_dict(values: Dict[str, ISDValue], n, r, t, msg):
    _key = f"{n}_{r}_{t}"
    if _key not in values:
        value = ISDValue(
            n=n,
            r=r,
            # This is the t used to assess the ISD attack
            t=t,
            # prime=prime,
            # n0=n0,
            # v=v,
            # lambd=lambd,
            msgs=[msg],
        )
        values[_key] = value
    else:
        _val = values[_key]
        _val.msgs.append(msg)


def main():
    proper_primes = None
    with open('./isdleda/assets/proper_primes.csv', 'r',
              newline='') as csvfile:
        reader = csv.reader(csvfile)
        # actually there's just one row
        for row in reader:
            proper_primes = list(map(int, row))
    assert proper_primes is not None
    n0_values = range(2, 6)

    lambda_values = (128, 192, 256)
    values: Dict[str, ISDValue] = dict()

    for n0, lam in itertools.product(n0_values, lambda_values):
        # Approximate ISD hardness (Sendrier method). Given the weight $w$ of
        # the codeword/error to be found and the code rate k/n=R, an ISD costs
        # approx 2^cw, where the constant c depends on the rate
        #
        # c = log_2(1/(1-R)) = -log_2(1-R) ;
        #
        # so, from 2^cw = 2^lambda, given lambda and n0, we first compute c,
        # and then
        #
        # w = -lam/c

        # MRA (SDP) ;
        # ISD(n, k, t); code rate (n0-1)/n0
        c = -np.log2(1 - (n0 - 1) / n0)
        t1 = np.ceil(lam / c)
        # NOTE: the ISD parameters in LEDA are (n, r, t) and not (n, k, t) as usual
        # KRA1 (CFP); ISD(n0*p,p,2*v) / (p*binom{n0}{2}); code rate (n0-1)/n0;
        # target weight = 2*v
        c = -np.log2(1 - (n0-1) / n0)
        v1 = np.ceil(lam / (2 * c))
        # KRA2 (CFP); ISD(2*p,p,2*v) / (n0*p); attacked code rate (1/2); target weight = 2v
        c = -np.log2(1 - 1 / 2)
        v2 = np.ceil(lam / (2 * c))
        # KRA3 (CFP); ISD(n0*p,(n0-1)*p,n0*v) / p; attacked code rate 1/n0; target weight = n0*v
        c = -np.log2(1 - 1 / n0)
        v3 = np.ceil(lam / (n0 * c))

        # KEY recovery
        v_min = min(v1, v2, v3)
        v_max = max(v1, v2, v3)

        v_range_low = int(.7 * v_min)
        v_range_high = int(1.3 * v_max)

        # v should be odd
        if not v_range_low % 2:
            v_range_low -= 1
        if not v_range_high % 2:
            v_range_high += 1

        for v in range(v_range_low, v_range_high, 2):
            # since v != sqrt(n) = sqrt(p*n0) -> v**2 = p * n0 -> p = v**2 * n0
            prime_guess = v**2 * n0

            # Take only the acceptable primes with a +- 20% margin on the prime
            # guess
            prime_range = filter(
                lambda p: p >= int(.8 * prime_guess) and p <= int(
                    1.2 * prime_guess), proper_primes)
            # NOTE the t values here are NOT the t to be used in the parameter
            # set, but only the equivalent t used to compute the complexity of
            # the Codeword Finding Problem (CFP)
            for prime in prime_range:
                # key recovery 1: ISD(n0*p, p, 2*v)
                msg = "KR1"
                _n = prime * n0
                _r = prime
                _t = 2 * v
                add_to_dict(values, _n, _r, _t, msg)

                # key recovery 3 ISD(n0*p, (n0-1)*p, n0*v
                msg = "KR3"
                _n = prime * n0
                _r = (n0 - 1) * prime
                _t = n0 * v
                # Note that, for this attack we are considering the dual code,
                # and hence k<r. However, we can just store the value of the
                # original code, and hence _n - _r.
                add_to_dict(values, _n, _n - _r, _t, msg)

                # key recovery 2 ISD(2p, p, 2v)
                # Each n0 !=2 can be reduced to n0=2
                if n0 != 2:
                    msg = "KR2"
                    _n = prime * 2
                    _r = prime
                    _t = 2 * v
                    add_to_dict(values, _n, _r, _t, msg)


        # Message recovery, i.e., Syndrome Decoding Problem (SDP)
        # the +3 skip is just to sweep the range faster
        for t in range(int(t1 * .8), int(t1 * 1.2), 3):
            # same as before
            prime_guess = t**2 * n0
            prime_range = filter(
                lambda p: p >= int(.8 * prime_guess) and p <= int(
                    1.2 * prime_guess), proper_primes)
            for prime in prime_range:
                # msg recovery p*n0, p, t
                _n = prime * n0
                _r = prime
                _t = t
                add_to_dict(values, _n, _r, _t, msg)

    print(len(values))
    values_set = set(values.values())
    # print(f"Pickling to {ISD_VALUES_FILE_PKL}")
    # save_to_pickle(ISD_VALUES_FILE_PKL, values_set)
    filename = os.path.join("out", "values", "from_generation",
                            "isd_values.json")
    print(f"JSONing to {filename}")
    save_to_json(filename, [asdict(x) for x in sorted(values_set)])


if __name__ == '__main__':
    main()
