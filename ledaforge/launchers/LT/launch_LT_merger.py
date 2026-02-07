"""
launch_LT script generates
"""

import json
import pathlib
from collections import defaultdict
# import argparse
from sys import argv
import os

from ledaforge.utils.export.export import save_to_json

def main():
    root = argv[1] # the source dir
    # computing_paradigm = argv[2]  # either Classic or Quantum

    all_values = defaultdict(lambda: defaultdict(lambda: defaultdict()))
    for computing_paradigm in ("Classic", "Quantum"):
        values = defaultdict(list)
        curdir = os.path.join(root, computing_paradigm)
        for attack_dir in pathlib.Path(curdir).iterdir():
            if not attack_dir.is_dir():
                continue

            for json_file in attack_dir.glob("*.json"):
                key = json_file.stem  # n_k_w
                with open(json_file) as f:
                    data = json.load(f)
                    try:
                        values[key].append((data[computing_paradigm]["value"], attack_dir.name))
                    except Exception as e:
                        print(attack_dir)
                        print(data)
                        input()
                        raise e

        # Print minimum per n_k_w
        for key, entries in sorted(values.items()):
            min_value, attack = min(entries, key=lambda x: x[0])
            all_values[key][computing_paradigm]["value"] = min_value
            all_values[key][computing_paradigm]["attack"] = attack
            # print(f"{key}: min value = {min_value} ({attack})")
    for k, v in all_values.items():
        save_to_json(os.path.join(root, "ALL", f"{k}.json"), v)


if __name__ == '__main__':
    main()


