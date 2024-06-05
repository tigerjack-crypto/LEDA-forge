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
        for row in reader:
            proper_primes = list(map(int, row))
    assert proper_primes is not None
    n0_values = range(2, 6)

    lambda_values = (128, 192, 256)
    values: Set[Value] = set()

    for n0, lam in itertools.product(n0_values, lambda_values):
        # print(n0, lam)
        # ISD(n_0*p,p,t) / sqrt(p) attacked code rate (n_0-1)/n_0
        t = np.ceil(-lam / np.log2(1 - (n0 - 1) / n0))
        # ISD(n_0*p,p,2*v) / (p* binom{n_0}{2}), attacked code rate (n_0-1)/n_0
        v1 = np.ceil(-lam / np.log2(1 - (n0 - 1) / n0)) // 2
        # ISD(2*p,p,2*v) / (n_0*p), attacked code rate (1/2)
        v2 = np.ceil(-lam / np.log2(1 - 1 / 2)) // 2
        # ISD(n_0*p,(n_0-1)*p,n_0*v) / p    attacked code rate 1/n_0
        v3 = np.ceil(-lam / np.log2(1 - 1 / n0)) // n0

        # KEY recovery
        v_min = min(v1, v2, v3)
        v_max = max(v1, v2, v3)

        # v should be odd
        v_range_low = int(.8 * v_min)
        v_range_high = int(1.3 * v_max)

        if not v_range_low % 2:
            v_range_low -= 1
        if not v_range_high % 2:
            v_range_high += 1

        for v in range(v_range_low, v_range_high, 2):
            # p*n0 = (v*n0)^2 -> p = v^2*n0
            prime_guess = v**2 * n0
            prime_range = filter(
                lambda p: p >= int(.8 * prime_guess) and p <= int(
                    1.2 * prime_guess), proper_primes)
            for prime in prime_range:
                # key recovery 1 (n0*p, p, 2*v)
                value = Value(n=prime * n0,
                              r=prime,
                              t=2 * v,
                              prime=prime,
                              n0=n0,
                              v=v)
                values.add(value)

                # key recovery 2 (2p, p, 2v)
                value = Value(n=prime * 2,
                              r=prime,
                              t=2 * v,
                              prime=prime,
                              n0=n0,
                              v=v)
                values.add(value)

                # key recovery 3 (n0*p, (n0-1)*p, n0*v
                value = Value(n=prime * n0,
                              r=prime,
                              t=2 * v,
                              prime=prime,
                              n0=n0,
                              v=v)
                values.add(value)
                # classical = min(kr1, kr2, kr3)
                # for p in range(1, 4):
                #     # quantum key recovery 1, 2, 3 as before
        # MSG recovery
        for t in range(int(v1 * .8), int(v1 * 1.2)):
            # t = 2v
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
                              v=None)
                values.add(value)
                # for p in range(1, 4):
                #     # quantum msg recovery p*n0, p, t
    print(len(values))
    print(f"Pickling to {ISD_VALUES_FILE_PKL}")
    save_to_pickle(ISD_VALUES_FILE_PKL, values)
    print(f"JSONing to {ISD_VALUES_FILE_JSON}")
    save_to_json(ISD_VALUES_FILE_JSON, [asdict(x) for x in sorted(values)])


if __name__ == '__main__':
    main()
