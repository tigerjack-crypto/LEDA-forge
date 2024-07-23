import os
import json
from typing import List
import csv
import os

# Directories

# DIR1 = os.path.join("sshfs_mountpoint", "vc", "isd-leda", "out", "cisd_eb",
#                     "json", "MEM_LOG")
# DIR2 = os.path.join("sshfs_mountpoint", "vc", "LEDAtools", "out", "results",
#                     "json")
DIR1 = '/home/sperriello/vc/isd-leda/out/cisd_eb/json/MEM_LOG/'
DIR2 = '/home/sperriello/vc/LEDAtools/out/results/json/'


def extract_value_from_json(file_path, key_tree: List[str]):
    with open(file_path, 'r') as file:
        data = json.load(file)
        intermediate_val = data
        for key in key_tree:
            intermediate_val = intermediate_val.get(key, None)
        return intermediate_val


def main():
    # Ensure directories exist
    if not os.path.isdir(DIR1):
        print(f"DIR1 must exist, got {DIR1}.")
        exit(1)
    if not os.path.isdir(DIR2):
        print(f"DIR2 must exist, got {DIR2}.")
        exit(1)

    # Get list of files in both directories
    print(f"Get list of files for {DIR1}")
    files_in_dir1 = set(os.listdir(DIR1))
    print(f"Get list of files for {DIR2}")
    files_in_dir2 = set(os.listdir(DIR2))

    # Find common files
    print(f"Get common files")
    common_files = files_in_dir1.intersection(files_in_dir2)

    with open('out/eb_vs_leda_diff.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile,
                            delimiter=',',
                            quotechar='|',
                            quoting=csv.QUOTE_MINIMAL)
        # EB - LEDA
        writer.writerow([
            'n', 'r', 't', 'EB Stern', 'EB Stern p', 'EB Stern l',
            'EB Stern M4R', 'LEDA Stern', 'LEDA Stern p', 'LEDA Stern l'
        ])
        for filename in common_files:
            eb_path = os.path.join(DIR1, filename)
            leda_path = os.path.join(DIR2, filename)

            eb_val = extract_value_from_json(eb_path, ["Stern", "estimate"])
            eb_time = eb_val.get("time")
            eb_p = eb_val.get("parameters").get("p")
            eb_l = eb_val.get("parameters").get("l")
            eb_m4r = eb_val.get("parameters").get("r")

            leda_val = extract_value_from_json(leda_path, ["MRA", "C"])
            if leda_val.get("alg_name") == "Stern":
                leda_time = leda_val.get("value")
                leda_p = leda_val.get("params").get("p")
                leda_l = leda_val.get("params").get("l")
            else:
                continue
            n, r, t = filename[:-5].split('_')

            writer.writerow([
                int(n),
                int(r),
                int(t),
                float(eb_time), 2 * int(eb_p),
                int(eb_l),
                int(eb_m4r),
                float(leda_time),
                int(leda_p),
                int(leda_l)
            ])


if __name__ == '__main__':
    main()
