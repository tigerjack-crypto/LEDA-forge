"""Generate the range of useful values for LEDA
"""
import csv
import itertools
from dataclasses import asdict
from typing import Set

import numpy as np
from isdleda.utils.common import Value
from isdleda.utils.export.export import save_to_json, save_to_pickle
from isdleda.utils.paths import ISD_VALUES_FILE_JSON, ISD_VALUES_FILE_PKL


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
    values: Set[Value] = set()

    for n0, lam in itertools.product(n0_values, lambda_values):
        # Approximate ISD hardness (Sendrier method). Given the weight $w$ of
        # the codeword/error to be found and the code rate k/n=R, an ISD costs
        # approx 2^cw, where the constant c depends on the rate
        #
        # c = log_2(1/(1-R)) c = -log_2(1-R) = -log2(1-(n_0-1)/n_0)
        #
        # c_X is the constant for a given number of blocks n_0, and a parity
        # check matrix H which is one block high and n_0 wide, hence
        #
        # R=(n_0-1)/n_0
        # 
        # c_2 = 1
        #
        # c_3 = 1.58
        # 
        # c_4 = 2
        #
        # so, from 2^cw = lam, given c and lam (with lam already expressed in
        # log2) we have
        #
        # w = lam/c

        # code rate (n_0-1)/n_0
        t1 = np.ceil(-lam / np.log2(1 - (n0 - 1) / n0))
        # ISD(n_0*p,p,2*v) / (p* binom{n_0}{2}), attacked code rate (n_0-1)/n_0
        v1 = np.ceil(-lam / np.log2(1 - (n0 - 1) / n0)) // 2
        # ISD(2*p,p,2*v) / (n_0*p), attacked code rate (1/2)
        v2 = np.ceil(-lam / np.log2(1 - 1 / 2)) // 2
        # ISD(n_0*p,(n_0-1)*p,n_0*v) / p    attacked code rate 1/n_0
        v3 = np.ceil(-lam / np.log2(1 - 1 / n0)) // n0

        # KEY recovery
        v_min = min(v1, v2, v3)
        v_max = max(v1, v2, v3)

        v_range_low = int(.8 * v_min)
        v_range_high = int(1.3 * v_max)

        # v should be odd
        if not v_range_low % 2:
            v_range_low -= 1
        if not v_range_high % 2:
            v_range_high += 1

        for v in range(v_range_low, v_range_high, 2):
            # p*n0 = (v*n0)^2 -> p = v^2*n0
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
                value = Value(n=prime * n0,
                              r=prime,
                              # This is the t used to assess the ISD attack
                              t=2 * v,
                              prime=prime,
                              n0=n0,
                              v=v,
                              lambd=lam)
                values.add(value)

                # key recovery 2 ISD(2p, p, 2v)
                if n0 == 2:
                    value = Value(n=prime * 2,
                                  r=prime,
                                  # This is the t used to assess the ISD attack
                                  t=2 * v,
                                  prime=prime,
                                  n0=n0,
                                  v=v,
                                  lambd=lam)
                    values.add(value)

                # key recovery 3 ISD(n0*p, (n0-1)*p, n0*v
                value = Value(n=prime * n0,
                              r=prime * (n0 - 1),
                              # This is the t used to assess the ISD attack
                              t=n0 * v,
                              prime=prime,
                              n0=n0,
                              v=v,
                              lambd=lam)
                values.add(value)

        # Message recovery, i.e., Syndrome Decoding Problem (SDP)
        for t in range(int(t1 * .8), int(t1 * 1.2)):
            prime_guess = (t / 2)**2 * n0
            prime_range = filter(
                lambda p: p >= int(.8 * prime_guess) and p <= int(
                    1.2 * prime_guess), proper_primes)
            for prime in prime_range:
                # msg recovery p*n0, p, t
                value = Value(n=prime * n0,
                              r=prime,
                              t=t,
                              prime=prime,
                              n0=n0,
                              # None bcz we are not interested in v in this attack
                              v=None,
                              lambd=lam)
                values.add(value)
    print(len(values))
    print(f"Pickling to {ISD_VALUES_FILE_PKL}")
    save_to_pickle(ISD_VALUES_FILE_PKL, values)
    print(f"JSONing to {ISD_VALUES_FILE_JSON}")
    save_to_json(ISD_VALUES_FILE_JSON, [asdict(x) for x in sorted(values)])


if __name__ == '__main__':
    main()
