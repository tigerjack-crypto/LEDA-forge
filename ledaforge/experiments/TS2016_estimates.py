"""Experiments using the results from

Torres, R. C., & Sendrier, N. (2016). Analysis of information set decoding for
a sub-linear error weight. In T. Takagi (Ed.), Post-quantum cryptography—7th
international workshop, PQCrypto 2016, fukuoka, japan, february 24-26, 2016,
proceedings (Vol. 9606, pp. 144–161). Springer.
https://doi.org/10.1007/978-3-319-29360-8_10

Given the weight $w$ of the codeword/error to be found and the code rate R=k/n,
the authors show that an ISD costs approx $2^cw$, where

$c = log_2(1/(1-R)) = -log_2(1-R) = -log_2(1-(n_0-1)/n_0)$

We want to use this idea to retrieve $w$ given $\\lambda$ (i.e., the target
computational complexity, expressed as log2) and $c$; that is

$w = -\\lambda/c$

"""
from sage.all import var
from sage.functions.all import ceil, log

n0, lambd = var('n0, lambd')

# c_X is the constant for a given number of blocks n_0, and a parity check matrix H
# which is one block high and n_0 wide, hence R=(n_0-1)/n_0
# c_2 = 1
# c_3 = 1.58
# c_4 = 2

# MRA (SDP) ;
# ISD(n, k, t); code rate (n0-1)/n0
c = -log(1 - (n0 - 1) / n0, 2)
t = ceil(lambd / c)
# NOTE: the ISD parameters in LEDA are (n, r, t) and not (n, k, t) as usual
# KRA1 (CFP); ISD(n0*p,p,2*v) / (p*binom{n0}{2}); code rate (n0-1)/n0;
# target weight = 2*v
c = -log(1 - (n0 - 1) / n0, 2)
v1 = ceil(lambd / (2 * c))
# KRA2 (CFP); ISD(2*p,p,2*v) / (n0*p); attacked code rate (1/2); target weight = 2v
c = -log(1 - 1 / 2, 2)
v2 = ceil(lambd / (2 * c))
# KRA3 (CFP); ISD(n0*p,(n0-1)*p,n0*v) / p; attacked code rate 1/n0; target weight = n0*v
c = -log(1 - 1 / n0, 2)
v3 = ceil(lambd / (n0 * c))


def get_values():

    print(f"t: {t}, v1: {v1} v2: {v2}, v3:{v3}")

    ls = ['lambda', 'n0', 'v1', 'v2', 'v3',  't']
    for item in ls:
        print(f"{item:<6}|", end="")
    print("")

    # for lambd_r in [128, 192, 256]:
    for lambd_r in [143, 207, 272]:
        for n0_r in range(2, 6):
            # t_r, v1_r, v2_r, v3_r = get_value(n0_r, lambd_r)
            ress = get_value(n0_r, lambd_r)
            # print(f"({n0_r},{lambd_r})->"
            #       f"t: {int(t_r)}, v1: {int(v1_r)} v2: {int(v2_r)}, v3:{int(v3_r)}")

            print(f"{lambd_r:<6}|{n0_r:<6}|", end="")
            for item in ress:
                print(f"{int(item):<6}|", end="")
            print("")

        print("")


def get_value(n0_r: int, lambd_r: int):
    """Given lambda (security level) and n0 (parameter of LEDA) compute the
    estimate for the t (message recovery attack) and the v_i values (key
    recovery attack)"""

    # ISD(n0*p,p,t) / sqrt(p) attacked code rate (n0-1)/n0
    t_r = t.subs({n0: n0_r, lambd: lambd_r}).unhold().n()
    v1_r = v1.subs({n0: n0_r, lambd: lambd_r}).unhold().n()
    v2_r = v2.subs({n0: n0_r, lambd: lambd_r}).unhold().n()
    v3_r = v3.subs({n0: n0_r, lambd: lambd_r}).unhold().n()

    return v1_r, v2_r, v3_r, t_r


if __name__ == '__main__':
    get_values()
