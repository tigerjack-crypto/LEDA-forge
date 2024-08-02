"""It assembles the complexity data obtained from the different ISD computation
tools. Since the complexity data are generated on a gui-less server, matplotlib
will need to run in a gui-less mode. The data is then exported in a specific
directory, and can then be used from data visualization tool to produce graphs.
"""
# Needed for matplotlib to run without GUI
import matplotlib as mpl
from isdleda.launchers.launcher_utils import AES_LAMBDAS, QAES_LAMBDAS

mpl.use('Agg')

import collections
import os
from pathlib import Path
from typing import Iterable

from isdleda.launchers.launch_classical_isd import MemAccess
from isdleda.utils.export.export import (load_from_json, load_from_pickle,
                                         save_to_pickle)
from isdleda.utils.paths import (OUT_FILE_FORMULA, OUT_FILES_CEB_DIR,
                                 OUT_FILES_CLEDA_TYPE_DIR, OUT_FILES_QLB_DIR,
                                 OUT_PLOTS_DATA_DIR)

# (k/n, t, effort)
# exclude small values of time
MIN_LAMBDA_C = int(.8 * AES_LAMBDAS[0])
MAX_LAMBDA_C = int(1.2 * AES_LAMBDAS[-1])
MIN_LAMBDA_Q = int(.8 * QAES_LAMBDAS[0])
MAX_LAMBDA_Q = int(1.2 * QAES_LAMBDAS[-1])


# cisd_leebrickell_process
def process_eb_support(main_dir: str, filenames: Iterable[str]):
    values = []
    for filename in filenames:
        cval = load_from_json(os.path.join(main_dir, filename))
        time = cval['MinimumTime'][1]['estimate']['time']
        # Exclude values too far from the region of interest
        if time > MIN_LAMBDA_C and time < MAX_LAMBDA_C:
            tup = (cval['params']['n'],
                   cval['params']['n'] - cval['params']['r'],
                   cval['params']['t'], time)
            values.append(tup)
    return values


def process_pbp23_support(main_dir: str, filenames: Iterable[str]):
    values = []
    for filename in filenames:
        qval = load_from_pickle(os.path.join(main_dir, filename))
        n, k, t = None, None, None
        for key, value in qval['MinimumDepth'].in_params.items():
            match str(key):
                case 'n_o':
                    n = value
                case 'k_o':
                    k = value
                case 't_o':
                    t = value
        assert n is not None, "n is None"
        assert k is not None, "k is None"
        assert t is not None, "t is None"
        t_depth = qval['MinimumDepth'].tmeas2.t_depth
        if 2 * t_depth > MIN_LAMBDA_Q and 2 * t_depth < MAX_LAMBDA_Q:
            # For the parallelization, we are interested in 2*t_depth vs QAES
            tup = (n, k, t, 2 * t_depth)
            values.append(tup)
    return values


def process_ledatools_support(main_dir: str, filenames: Iterable[str]):
    c_values = []
    q_values = []
    for filename in filenames:
        val = load_from_json(os.path.join(main_dir, filename))
        n, k, t = [int(x) for x in Path(filename).stem.split("_")]
        c_time = val["Classic"]["Plain"]["value"]
        t_depth = val["Quantum"]["Plain"]["value"]
        if MIN_LAMBDA_Q < 2 * t_depth < MAX_LAMBDA_Q and MIN_LAMBDA_C < c_time < MAX_LAMBDA_C:
            # For the parallelization, we are interested in 2*t_depth vs QAES
            c_tup = (n, k, t, c_time)
            q_tup = (n, k, t, 2 * t_depth)
            c_values.append(c_tup)
            q_values.append(q_tup)
    return c_values, q_values


def process_data(cres):
    values_dict = collections.defaultdict(list)
    for value in cres:
        # key = k/n
        key = f"{value[1]/value[0]}"
        # key = n0 = n / (n-k)
        # key = value[0] // (value[0] - value[1])
        values_dict[key].append(value)
    return values_dict


def process_eb():
    # Classical EB
    for mem_access in MemAccess:
        cvalues_dir = OUT_FILES_CEB_DIR.format(
            out_type='json',
            # memaccess=MemAccess.MEM_CONST.name)
            memaccess=mem_access.name)
        # exclude symbolic expression
        cvalues = filter(lambda x: not x.startswith(OUT_FILE_FORMULA),
                         os.listdir(cvalues_dir))
        cres = process_eb_support(cvalues_dir, cvalues)
        cres_grouped = process_data(cres)
        out_file = os.path.join(OUT_PLOTS_DATA_DIR, f"eb_{mem_access.name}")

        save_to_pickle(out_file, cres_grouped)


def process_pbp23():
    # Quantum Mine LB
    # vals_dic = []
    qvalues_dir = OUT_FILES_QLB_DIR.format(out_type='pkl')
    qvalues = filter(lambda x: not x.startswith(OUT_FILE_FORMULA),
                     os.listdir(qvalues_dir))
    qres = process_pbp23_support(qvalues_dir, qvalues)
    qres_grouped = process_data(qres)
    save_to_pickle(os.path.join(OUT_PLOTS_DATA_DIR, "pbp23"), qres_grouped)


def process_ledatools():
    values_dir = OUT_FILES_CLEDA_TYPE_DIR.format(out_type='json')
    values = filter(lambda x: not x.startswith(OUT_FILE_FORMULA),
                    os.listdir(values_dir))
    # (classica, quantum) value
    c_res, q_res = process_ledatools_support(values_dir, values)

    # classic
    res_grouped = process_data(c_res)
    out_file = os.path.join(OUT_PLOTS_DATA_DIR, f"ledatools_classic")
    save_to_pickle(out_file, res_grouped)

    # quantum
    res_grouped = process_data(q_res)
    out_file = os.path.join(OUT_PLOTS_DATA_DIR, f"ledatools_quantum")
    save_to_pickle(out_file, res_grouped)




def main():
    # process_eb()
    # process_pbp23()
    process_ledatools()


if __name__ == '__main__':
    main()
