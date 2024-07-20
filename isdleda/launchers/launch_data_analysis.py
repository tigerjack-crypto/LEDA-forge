"""The idea is to launch the data analysis on the server, where all the data
are present, while the visualization on the client through

"""
# Needed for matplotlib to run without GUI
import matplotlib as mpl

mpl.use('Agg')

import collections
import os
from typing import Iterable

from isdleda.launchers.launch_classical_isd import MemAccess
from isdleda.utils.export.export import load_from_pickle, save_to_pickle
from isdleda.utils.paths import (OUT_FILE_FORMULA, OUT_FILES_CEB_DIR,
                                 OUT_FILES_QLB_DIR, OUT_PLOTS_DATA_DIR)

# Official NIST values
AES_LAMBDAS = (143, 207, 272)
# Values taken from my Ph.D. Thesis, table 6.5 (Jan+22). Nist uses the ones
# from Jaques though.
QAES_LAMBDAS = (154, 219, 283)

# (k/n, t, effort)
# exclude small values of time
MIN_LAMBDA_C = int(.8 * AES_LAMBDAS[0])
MAX_LAMBDA_C = int(1.2 * AES_LAMBDAS[-1])
MIN_LAMBDA_Q = int(.8 * QAES_LAMBDAS[0])
MAX_LAMBDA_Q = int(1.2 * QAES_LAMBDAS[-1])


# cisd_leebrickell_process
def cisd_eb_process(main_dir: str, filenames: Iterable[str]):
    values = []
    for filename in filenames:
        cval = load_from_pickle(os.path.join(main_dir, filename))
        time = cval['MinimumTime'][1]['estimate']['time']
        # Exclude values too far from the region of interest
        if time > MIN_LAMBDA_C and time < MAX_LAMBDA_C:
            tup = (cval['params']['n'],
                   cval['params']['n'] - cval['params']['r'],
                   cval['params']['t'], time)
            values.append(tup)
    return values


def qisd_process(main_dir: str, filenames: Iterable[str]):
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
        if 2*t_depth > MIN_LAMBDA_Q and 2*t_depth < MAX_LAMBDA_Q:
            # For the parallelization, we are interested in 2*t_depth vs QAES
            tup = (n, k, t, 2*t_depth)
            values.append(tup)
    return values


def process_data(cres):
    values_dict = collections.defaultdict(list)
    for value in cres:
        # key = k/n
        # key = f"{value[1]/value[0]}"
        # key = n0 = n / (n-k)
        key = value[0] // (value[0] - value[1])
        values_dict[key].append(value)
    return values_dict


def main():
    # Classical EB
    for mem_access in MemAccess:
        cvalues_dir = OUT_FILES_CEB_DIR.format(
            out_type='pkl',
            # memaccess=MemAccess.MEM_CONST.name)
            memaccess=mem_access.name)
        # exclude symbolic expression
        cvalues = filter(lambda x: not x.startswith(OUT_FILE_FORMULA),
                         os.listdir(cvalues_dir))
        cres = cisd_eb_process(cvalues_dir, cvalues)
        cres_grouped = process_data(cres)
        out_file = os.path.join(OUT_PLOTS_DATA_DIR,
                                f"cisd_eb_{mem_access.name}")

        save_to_pickle(out_file, cres_grouped)

    # Quantum Mine LB
    # vals_dic = []
    qvalues_dir = OUT_FILES_QLB_DIR.format(out_type='pkl')
    qvalues = filter(lambda x: not x.startswith(OUT_FILE_FORMULA),
                     os.listdir(qvalues_dir))
    qres = qisd_process(qvalues_dir, qvalues)
    qres_grouped = process_data(qres)

    save_to_pickle(os.path.join(OUT_PLOTS_DATA_DIR, "q_lb"), qres_grouped)


if __name__ == '__main__':
    main()
