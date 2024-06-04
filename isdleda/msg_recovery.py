from sage.functions.all import log
from sage.symbolic.all import Expression
# from sage.functions.all import binomial  # SLOW
from typing import Callable

def isd_message(isd_function: Callable[[Expression, Expression, Expression],
                                     Expression], n0: Expression, p: Expression, t: Expression):
    # ISD(n_0*p,p,t) / sqrt(p)
    logcost = isd_function(n0*p,p,t)
    return logcost - log(p,2).n()/2
