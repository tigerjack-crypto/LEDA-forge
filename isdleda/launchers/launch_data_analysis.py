"""The idea is to launch the data analysis on the server, where all the data
are present, while the visualization on the client through

"""
# Needed for matplotlib to run without GUI
import matplotlib as mpl

mpl.use('Agg')

import collections
import os
from typing import Iterable, List

from isdleda.launchers.launch_classical_isd import MemAccess
from isdleda.utils.export.export import load_from_pickle, save_to_pickle
from isdleda.utils.paths import OUT_FILE_FORMULA, OUT_FILES_CEB_DIR, OUT_PLOTS_DATA_DIR

# (k/n, t, effort)
# exclude small values of time
MIN_LAMBDA = 100
MAX_LAMBDA = 300


# cisd_leebrickell_process
def cisd_eb_process(main_dir: str, filenames: Iterable[str]):
    values = []
    for filename in filenames:
        cval = load_from_pickle(os.path.join(main_dir, filename))
        time = cval['MinimumTime'][1]['estimate']['time']
        # Exclude values too far from the region of interest
        if time > MIN_LAMBDA and time < MAX_LAMBDA:
            tup = (cval['params']['n'],
                   cval['params']['n'] - cval['params']['r'],
                   cval['params']['t'], time)
            values.append(tup)
    return values


def qisd_process(filenames: List[str]):
    values = []
    for filename in filenames:
        qval = load_from_pickle(filename)
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
        tup = (n, k, t, qval['MinimumDepth'].tmeas2.t_depth)
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
    cvals_dic = []
    for mem_access in (
            MemAccess.MEM_CONST,
            MemAccess.MEM_LOG,
            MemAccess.MEM_SQRT,
            MemAccess.MEM_CBRT,
    ):

        cvalues_dir = OUT_FILES_CEB_DIR.format(
            out_type='pkl',
            # memaccess=MemAccess.MEM_CONST.name)
            memaccess=mem_access.name)
        # exclude symbolic expression
        cvalues = filter(lambda x: not x.startswith(OUT_FILE_FORMULA),
                         os.listdir(cvalues_dir))
        cres = cisd_eb_process(cvalues_dir, cvalues)
        cres_grouped = process_data(cres)
        cvals_dic.append((mem_access.name, cres_grouped))
    save_to_pickle(os.path.join(OUT_PLOTS_DATA_DIR, "all"), cvals_dic)


if __name__ == '__main__':
    main()
