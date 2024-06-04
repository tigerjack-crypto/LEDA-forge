# key recovery attack
from sage.functions.all import log
from sage.symbolic.all import Expression
# from sage.functions.all import binomial  # SLOW
from typing import Callable
from math import comb


def isd_kra_1(isd_function: Callable[[Expression, Expression, Expression],
                                     Expression], n0: Expression, p: Expression, v: Expression):
    # ISD(n_0*p,p,2*v) / (p* binom{n_0}{2}), attacked code rate (1/n_0)
    r = p
    n = p * n0
    t = 2 * v
    logcost = isd_function(n, n - r, t)
    return logcost - log(p * comb(n0, 2), 2).n()


def isd_kra_2(isd_function: Callable[[Expression, Expression, Expression],
                                     Expression], n0: Expression, p: Expression, v: Expression):
    # ISD(2*p,p,2*v) / (n_0*p), attacked code rate (1/2)
    n = p * 2
    r = p
    t = 2 * v
    logcost = isd_function(n, n - r, t)
    return logcost - log(p * n0, 2).n()


def isd_kra_3(isd_function: Callable[[Expression, Expression, Expression],
                                     Expression], n0: Expression, p: Expression, v: Expression):
    # ISD(n_0*p,(n_0-1)*p,n_0*v) / p
    n = p * n0
    r = (n0 - 1) * p
    t = n0 * v
    logcost = isd_function(n, n - r, t)
    return logcost - log(p, 2).n()
