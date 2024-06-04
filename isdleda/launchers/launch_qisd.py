import itertools
import os
from enum import IntEnum

from isdleda.utils.export.export import (load_from_pickle, save_to_pickle,
                                         save_to_txt)
from isdleda.utils.paths import OUT_FILES_QLB_SYMBOLIC
from isdleda.utils.static import get_primes
# ISD_scripts
from measures.common import CodeExtended
from measures.leebrickell_quantum import LeeBrickellQuantum
from sage.all import var
# SAGE
from sage.rings.all import RealField
from utils.datamanipulation import replace_exp_valuedict
from dataclasses import replace

REAL_PREC = 1000
REAL_FIELD = RealField(prec=REAL_PREC)

from statics.codes import SecurityLevels


class OutType(IntEnum):
    TXT = 0
    PKL = 1


def _get_formula():
    meas = LeeBrickellQuantum(CodeExtended(
        "LEDA",
        SecurityLevels.UND,
        -1,
        -1,
        -1,
        is_cyclic=False,
        init_real_values=False,
    ),
                              p=-1)
    res = meas.go()
    return res


def _store_formula(out: OutType, res):
    if out == OutType.TXT:
        save_to_txt(OUT_FILES_QLB_SYMBOLIC.format(out_type="txt"), res)
    elif out == OutType.PKL:
        save_to_pickle(OUT_FILES_QLB_SYMBOLIC.format(out_type="pkl"), res)
    else:
        raise AttributeError("Unknown out type %s" % out)


def main():
    # _store_formula(OutType.TXT)
    pickle_file = OUT_FILES_QLB_SYMBOLIC.format(out_type="pkl")
    if not os.path.isfile(pickle_file):
        res = _get_formula()
        _store_formula(OutType.PKL, res)
    else:
        res = load_from_pickle(pickle_file)

    ts = {128: range(40, 140), 192: range(70, 200), 256: range(100, 280)}
    n0s = range(2, 6)
    primes = get_primes()
    ps = range(1, 3)

    # launch: Type[CodeExtendedSage]
    # print(OUT_FILES_QLB_FMT)

    for (n0, prime, p, t) in itertools.product(n0s, primes, ps, ts[128]):
        print(n0, p, t)
        if (prime * n0) < (t * 5):
            print("continue")
            continue

        n_o, k_o, t_o, r_o, p_o = var("n_o, k_o, t_o, r_o, p_o",
                                      domain="integer")
        var_subs = {
            n_o: REAL_FIELD(prime * n0),
            k_o: REAL_FIELD(prime * n0 - prime),
            t_o: REAL_FIELD(t),
            r_o: REAL_FIELD(prime),
            p_o: REAL_FIELD(p),
        }
        # Dict associting to each string a corresponding name
        # var_by_names = {str(v): v for v in (n_o, k_o, t_o, r_o, p_o)}
        # res.in_params = LeeBrickellQuantum.get_dict_input_params_cls(True, var_by_names,
        #                                       var_by_names, var_subs)

        # LeeBrickellQuantum.replace_with_real_values(res, var_subs)

        normal2 = replace_exp_valuedict(
            res.normal2,  # lsp: ignore
            var_subs,
            numerical=True)
        normal_expanded2 = replace_exp_valuedict(res.normal_expanded2,
                                                 var_subs,
                                                 numerical=True)
        tmeas2 = replace_exp_valuedict(res.tmeas2, var_subs, numerical=True)
        res2 = replace(
            res,
            normal2=normal2,
            normal_expanded2=normal_expanded2,
            tmeas2=tmeas2,
            normal=None,
            normal_expanded=None,
            tmeas=None,
        )
        print(res2)

        # launch = LeeBrickellQuantum

        # meas = launch(CodeExtended("LEDA",
        #                            SecurityLevels.UND,
        #                            prime * n0,
        #                            prime * n0 - prime,
        #                            t,
        #                            is_cyclic=False,
        #                            init_real_values=True),
        #               p=p)
        # kwords = {}
        # kwords["subs"] = True
        # res = meas.go(**kwords)
        # print(res)
        # break


if __name__ == '__main__':
    main()

# for
