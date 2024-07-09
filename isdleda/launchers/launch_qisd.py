"""Compute the computational cost for the quantum ISD
"""
import argparse
import os
from dataclasses import replace
from enum import IntEnum
from typing import Dict, Optional, Sequence

from isdleda.utils.common import Value
from isdleda.utils.export.export import (load_from_pickle, save_to_json, save_to_pickle,
                                         save_to_txt)
from isdleda.utils.paths import (ISD_VALUES_FILE_PKL, OUT_FILES_QLB_FMT,
                                 OUT_FILES_QLB_SYMBOLIC)
# ISD_scripts
from measures.common import CodeExtended
from measures.leebrickell_quantum import LeeBrickellQuantum, ValueDicts
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
    JSON = 2


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
    else:  # 
        save_to_json(OUT_FILES_QLB_SYMBOLIC.format(out_type="pkl"), res)


def parse_arguments():
    parser = argparse.ArgumentParser("Launch Lee-Brickell")
    parser.add_argument("--skip-existing",
                        action="store_true",
                        help="Skip quantum complexity files if existing")
    parser.add_argument("--out-format", choices=["txt", "pkl", "json"], default="pkl")
    parser.add_argument(
        "--formula-only",
        action="store_true",
        help="Just store the formula without computing the actual values",
    )
    return parser


def main(raw_args: Optional[list[str]] = None):
    print("#" * 80)
    parser = parse_arguments()
    if raw_args and len(raw_args) != 0:
        namespace = parser.parse_args(raw_args)
    else:
        namespace = parser.parse_args()
    print(namespace)
    pickle_file = OUT_FILES_QLB_SYMBOLIC.format(out_type="pkl")
    if not os.path.isfile(pickle_file):
        res = _get_formula()
        _store_formula(OutType.PKL, res)
    else:
        res = load_from_pickle(pickle_file)
        assert res is not None and len(res) > 0, f"No valid formula found"

    if namespace.formula_only:
        print(res)
        return

    isd_values: Sequence[Value] = load_from_pickle(ISD_VALUES_FILE_PKL)
    p_range = range(1, 5)
    tot = len(isd_values) * len(p_range)

    for i, value in enumerate(isd_values):
        n_o, k_o, t_o, r_o, p_o = var("n_o, k_o, t_o, r_o, p_o",
                                      domain="integer")
        assume(n_o > 0, k_o > 0, t_o > 0, r_o > 0, p_o > 0)
        var_subs = {
            n_o: REAL_FIELD(value.n),
            k_o: REAL_FIELD(value.n - value.r),
            r_o: REAL_FIELD(value.r),
            t_o: REAL_FIELD(value.t),
        }
        dic: Dict[str, ValueDicts] = {}
        for p in p_range:
            out_file = OUT_FILES_QLB_FMT.format(
                out_type=namespace.out_format,
                n=value.n,
                r=value.r,
                t=value.t,
                ext=namespace.out_format,
            )
            if namespace.skip_existing and os.path.isfile(out_file):
                continue
            var_subs[p_o] = REAL_FIELD(p)
            # var_subs_short = 
            # All the following value dicts are present, so if conditions are
            # not really necessary, but still they are in theory possibly None, and
            # lsp complains
            if not (res.normal2 and res.normal_expanded2 and res.tmeas2):
                raise Exception("Wrong state")
            normal2 = replace_exp_valuedict(res.normal2,
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
                in_params={
                    n_o: value.n,
                    k_o: value.n - value.r,
                    r_o: value.r,
                    t_o: value.t,
                    p_o: p
                }
,
                normal2=normal2,
                normal_expanded2=normal_expanded2,
                tmeas2=tmeas2,
                normal=None,
                normal_expanded=None,
                tmeas=None,
            )
            dic[f"p_{p}"] = res2

        min_time = min(dic.items(), key=lambda algo: algo[1].tmeas2.t_depth)
        dic['MinimumDepth'] = min_time[1]
        if namespace.out_format == 'pkl':
            save_to_pickle(out_file, dic)
        elif namespace.out_format == 'txt':
            save_to_txt(out_file, dic)
        elif namespace.out_format == 'json':
            save_to_json(out_file, dic)

        print(
            f"done {(i+1) * len(p_range)}/{tot} -> {(i+1)*len(p_range)/tot:%}",
            end='\r')


if __name__ == '__main__':
    main()

# for
