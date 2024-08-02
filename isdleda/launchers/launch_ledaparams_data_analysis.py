import matplotlib as mpl
from isdleda.launchers.launcher_utils import AES_LAMBDAS, QAES_LAMBDAS

mpl.use('Agg')

import collections
import json
import os

from isdleda.utils.export.export import load_from_json, save_to_pickle
from isdleda.utils.paths import OUT_FILES_LEDA_PARAMS, OUT_PLOTS_DATA_DIR

import functools
import operator

# We want to explore the region around a given lambda; that is, [lamba + val[0], lambda + val[1]]
C_INTERVALS_FUNCTS = (functools.partial(operator.add, -30),
                      functools.partial(operator.add, 30))
# I am less conservative with quantum. If there's a classical speed-up of X,
# the quantum speed-up would roughly be sqrt(X)
Q_INTERVALS_FUNCTS = (functools.partial(operator.add, -20),
                      functools.partial(operator.add, 20))
# C_INTERVALS_FUNCTS = (functools.partial(operator.mul, .8),
#                       functools.partial(operator.mul, 1.2))
# # Bigger confidence interval for quantum since there may be other breakthroughs
# Q_INTERVALS_FUNCTS = (functools.partial(operator.mul, .7),
#                       functools.partial(operator.mul, 1.3))


def process_ledatools_ledaparams():
    # This one is for LEDA params, the other was for LEDA results
    c_values = collections.defaultdict(list)
    q_values = collections.defaultdict(list)
    all_values = collections.defaultdict(list)
    values_by_level = load_from_json(OUT_FILES_LEDA_PARAMS)
    gacc = 0
    bound_counts = [0, 0]
    for level, values in values_by_level.items():
        print(f"Level {level}: {len(values)} starting params")
        acc = 0
        match level:
            case "1":
                level_idx = 0
            case "3":
                level_idx = 1
            case "5":
                level_idx = 2
            case _:
                raise Exception(f"Unknown level {level}")
        step = 5
        for i in range(0, len(values), step):
            value = values[i]
            p = value["p"]
            n0 = value["n0"]
            rate = (n0 - 1) / n0
            t = value["t"]
            v = value["v"]
            # TODO delete this check
            if t < 0:
                print(value)
                exit(-1)
            if v < 0:
                print(value)
                exit(-1)
            # END TODO

            complexities_jsonized = value["msgs"][0].replace("'", '"').replace(
                "(", "[").replace(")", "]").split(':', 1)[1]
            caes_min, qaes_min = json.loads(complexities_jsonized)['Minimum']

            q_bound = False
            c_bound = False
            if not(C_INTERVALS_FUNCTS[0](
                    AES_LAMBDAS[level_idx]) < caes_min < C_INTERVALS_FUNCTS[1](
                        AES_LAMBDAS[level_idx])):
                c_bound = True
                bound_counts[0] += 1
            if not (Q_INTERVALS_FUNCTS[0](QAES_LAMBDAS[level_idx]
                                     ) < qaes_min < Q_INTERVALS_FUNCTS[1](
                                         QAES_LAMBDAS[level_idx])):
                q_bound = True
                bound_counts[1] += 1
            
            if not q_bound and not c_bound:
                c_values[rate].append((p, n0, t, v, caes_min))
                q_values[rate].append((p, n0, t, v, qaes_min))
                all_values[rate].append((p, n0, t, v))
                acc += 1
        print(f"For level {level}: {acc} params obtained")
        gacc += acc

    print(f"Total {gacc} values. (cbound, qbounds): {bound_counts}")

    out_file = os.path.join(OUT_PLOTS_DATA_DIR,
                            f"ledatools_ledaparams_exploration_all")
    print(f"Saving to {out_file}")
    save_to_pickle(out_file, all_values)
    out_file = os.path.join(OUT_PLOTS_DATA_DIR,
                            f"ledatools_ledaparams_exploration_classic")
    print(f"Saving to {out_file}")
    save_to_pickle(out_file, c_values)
    out_file = os.path.join(OUT_PLOTS_DATA_DIR,
                            f"ledatools_ledaparams_exploration_quantum")
    print(f"Saving to {out_file}")
    save_to_pickle(out_file, q_values)


def main():
    process_ledatools_ledaparams()


if __name__ == '__main__':
    main()
