from sage.all import var
from sage.functions.all import ceil, log

n0, lambd = var('n0, lambd')

# approximate ISD hardness given the weight $w$ of the codeword/error to be found
# and the code rate k/n=R
# an ISD costs approx 2^cw, where the constant c depends on the rate c = log_2(1/(1-R))
# c = -log_2(1-R) = -log2(1-(n_0-1)/n_0)
# c_X is the constant for a given number of blocks n_0, and a parity check matrix H
# which is one block high and n_0 wide, hence R=(n_0-1)/n_0
# c_2 = 1
# c_3 = 1.58
# c_4 = 2

t = ceil(-lambd / log(1 - (n0 - 1) / n0, 2))
# ISD(n0*p,p,2*v) / (p* binom{n0}{2}), attacked code rate (n0-1)/n0
v1 = ceil(-lambd / (2 * log(1 - (n0 - 1) / n0, 2)))
# ISD(2*p,p,2*v) / (n0*p), attacked code rate (1/2)
v2 = ceil(-lambd / (2 * log(1 - 1 / 2, 2)))
# ISD(n0*p,(n0-1)*p,n0*v) / p    attacked code rate 1/n0
v3 = ceil(-lambd / (n0 * log(1 - 1 / n0, 2)))


def get_values():

    print(f"t: {t}, v1: {v1} v2: {v2}, v3:{v3}")


    ls = ['lambda', 'n0', 't', 'v1', 'v2', 'v3']
    for item in ls:
        print(f"{item:<6}|", end="")
    print("")

    for lambd_r in [128, 192, 256]:
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

    return t_r, v1_r, v2_r, v3_r


if __name__ == '__main__':
    get_values()
