# Needed for matplotlib to run without GUI
import matplotlib as mpl
mpl.use('Agg')

import os
import collections
import numpy as np
from typing import Iterable, List

import matplotlib.pyplot as plt
from isdleda.launchers.launch_classical_isd import MemAccess
from isdleda.utils.export.export import load_from_pickle
from isdleda.utils.paths import OUT_FILES_CEB_DIR

# (k/n, t, effort)


# cisd_leebrickell_process
def cisd_eb_process(main_dir: str, filenames: Iterable[str]):
    values = []
    for filename in filenames:
        cval = load_from_pickle(os.path.join(main_dir, filename))
        tup = (cval['params']['n'], cval['params']['n'] - cval['params']['r'],
               cval['params']['t'], cval['MinimumTime'][1]['estimate']['time'])
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
        key = f"{value[1]/value[0]}"
        values_dict[key].append(value)
    return values_dict


def plot_data(cvals: list[dict]):
    # fig = plt.figure()
    # axs = fig.subplots(ncols=2, nrows=len(cvals) // 2 + len(cvals) % 2, subplot_kw={'projection': '3d'})
    # axs = axs.flatten()

    # for (ax, cvals_tup) in zip(axs, cvals):
    for cvals_tup in cvals:
        fig = plt.figure()
        mem, cvals_dic = cvals_tup
        ax = fig.add_subplot(projection='3d')
        ax.set_title(mem)

        min_first = np.inf
        max_first = 0
        min_second = np.inf
        max_second = 0
        for ratio, values in cvals_dic.items():
            first_values, _, second_values, third_values = zip(*values)
            ax.scatter(first_values, second_values, third_values, label=ratio)
            _val = min(first_values)
            if _val < min_first:
                min_first = _val
            _val = max(first_values)
            if _val > max_first:
                max_first = _val
            _val = min(second_values)
            if _val < min_second:
                min_second = _val
            _val = max(second_values)
            if _val > max_second:
                max_second = _val

        # Set labels
        ax.set_xlabel('n')
        ax.set_ylabel('weight')
        ax.set_zlabel('time')


        # Create a meshgrid for the plane
        x = np.linspace(min_first, max_first, 10)
        y = np.linspace(min_second, max_second, 10)
        x, y = np.meshgrid(x, y)
        z1 = np.full_like(x, 143)
        z2 = np.full_like(x, 207)
        z3 = np.full_like(x, 272)

        ax.plot_surface(x, y, z1, color='r', alpha=.5)
        ax.plot_surface(x, y, z2, color='r', alpha=.5)
        ax.plot_surface(x, y, z3, color='r', alpha=.5)
        ax.legend()
        fig.savefig(f"out/figs/{mem}.png")

    # plt.show()


def main():
    cvals_dic = []
    for mem_access in (
            MemAccess.MEM_CONST,
            MemAccess.MEM_LOG,
            MemAccess.MEM_SQRT,
            MemAccess.MEM_CBRT,
    ):

        cvalues_dir = OUT_FILES_CEB_DIR.format(out_type='pkl',
                                            # memaccess=MemAccess.MEM_CONST.name)
                                            memaccess=mem_access.name)
        cvalues = filter(lambda x: not x.startswith('0_symbolic'),
                        os.listdir(cvalues_dir))
        cres = cisd_eb_process(cvalues_dir, cvalues)
        cres_grouped = process_data(cres)
        cvals_dic.append((mem_access.name, cres_grouped))
    plot_data(cvals_dic)


if __name__ == '__main__':
    main()
