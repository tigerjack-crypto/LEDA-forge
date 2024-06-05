import os
from dataclasses import replace
from enum import IntEnum
from typing import Sequence

from isdleda.utils.common import Value
from isdleda.utils.export.export import (load_from_pickle, save_to_pickle,
                                         save_to_txt)
from isdleda.utils.paths import (ISD_VALUES_FILE_PKL, OUT_FILES_QLB_FMT,
                                 OUT_FILES_QLB_SYMBOLIC)
# ISD_scripts
from measures.common import CodeExtended
from measures.leebrickell_quantum import LeeBrickellQuantum
from sage.all import assume, var
# SAGE
from sage.rings.all import RealField
from utils.datamanipulation import replace_exp_valuedict

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
    pickle_file = OUT_FILES_QLB_SYMBOLIC.format(out_type="pkl")
    if not os.path.isfile(pickle_file):
        res = _get_formula()
        _store_formula(OutType.PKL, res)
    else:
        res = load_from_pickle(pickle_file)

    isd_values: Sequence[Value] = load_from_pickle(ISD_VALUES_FILE_PKL)
    for value in isd_values:
        n_o, k_o, t_o, r_o, p_o = var("n_o, k_o, t_o, r_o, p_o",
                                      domain="integer")
        assume(n_o > 0, k_o > 0, t_o > 0, r_o > 0, p_o > 0)
        var_subs = {
            n_o: REAL_FIELD(value.n),
            k_o: REAL_FIELD(value.n - value.r),
            r_o: REAL_FIELD(value.r),
            t_o: REAL_FIELD(value.t),
        }
        for p in range(1, 4):
            var_subs[p_o] = REAL_FIELD(p)

            print(var_subs)

            normal2 = replace_exp_valuedict(
                res.normal2,  # lsp: ignore
                var_subs,
                numerical=True)
            normal_expanded2 = replace_exp_valuedict(res.normal_expanded2,
                                                     var_subs,
                                                     numerical=True)
            tmeas2 = replace_exp_valuedict(res.tmeas2,
                                           var_subs,
                                           numerical=True)
            res2 = replace(
                res,
                normal2=normal2,
                normal_expanded2=normal_expanded2,
                tmeas2=tmeas2,
                normal=None,
                normal_expanded=None,
                tmeas=None,
            )
            out_file = OUT_FILES_QLB_FMT.format(
                out_type='bin',
                n=value.n,
                r=value.r,
                t=value.t,
                p=p,
                ext='.pkl',
            )
            save_to_pickle(out_file, res2)


if __name__ == '__main__':
    main()

# for
