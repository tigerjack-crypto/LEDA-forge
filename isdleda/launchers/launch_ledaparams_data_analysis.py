import matplotlib as mpl
from isdleda.launchers.launcher_utils import AES_LAMBDAS, QAES_LAMBDAS

mpl.use('Agg')

import collections
import json
import os

from isdleda.utils.export.export import load_from_json, save_to_pickle
from isdleda.utils.paths import OUT_FILES_LEDA_PARAMS, OUT_PLOTS_DATA_DIR


def process_ledatools_ledaparams():
    # This one is for LEDA params, the other was for LEDA results
    c_values = collections.defaultdict(list)
    q_values = collections.defaultdict(list)
    all_values = collections.defaultdict(list)
    values_by_level = load_from_json(OUT_FILES_LEDA_PARAMS)
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
        step = 3
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

            if .9 * QAES_LAMBDAS[level_idx] < qaes_min < 1.1 * QAES_LAMBDAS[
                    level_idx] and .9 * AES_LAMBDAS[
                        level_idx] < caes_min < 1.1 * AES_LAMBDAS[level_idx]:
                c_values[rate].append((p, n0, t, v, caes_min))
                q_values[rate].append((p, n0, t, v, qaes_min))
                all_values[rate].append((p, n0, t, v))
                acc += 1
        print(f"For level {level}: {acc} params obtained")
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
