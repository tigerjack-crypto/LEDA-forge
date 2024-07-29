import csv
import json
import os
from typing import List


# DIR1 = os.path.join("sshfs_mountpoint", "vc", "isd-leda", "out", "cisd_eb",
#                     "json", "MEM_LOG")
# DIR2 = os.path.join("sshfs_mountpoint", "vc", "LEDAtools", "out", "results",
#                     "json")

# Server directories and files
DIR1 = '/home/sperriello/vc/isd-leda/out/cisd_eb/json/MEM_LOG/'
DIR2 = '/home/sperriello/vc/LEDAtools/out/results/json/'
OUT_FILE = 'out/eb_vs_leda_diff.csv'


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

    with open(OUT_FILE, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile,
                            delimiter=',',
                            quotechar='|',
                            quoting=csv.QUOTE_MINIMAL)
        # EB - LEDA
        writer.writerow([
            'n', 'k', 't', 'EB Stern', 'EB GJE', 'EB Stern p', 'EB Stern l',
            'EB Stern M4R', 'LEDA Stern', 'LEDA GJE', 'LEDA Stern p',
            'LEDA Stern l'
        ])
        for filename in common_files:
            eb_path = os.path.join(DIR1, filename)
            leda_path = os.path.join(DIR2, filename)

            eb_val = extract_value_from_json(eb_path, [
                "Stern",
            ])
            eb_val_estimate = eb_val.get("estimate")
            eb_time = eb_val_estimate.get("time")
            eb_gje = eb_val.get("additional_information").get("gauss")
            eb_p = eb_val_estimate.get("parameters").get("p")
            eb_l = eb_val_estimate.get("parameters").get("l")
            eb_m4r = eb_val_estimate.get("parameters").get("r")

            leda_val = extract_value_from_json(leda_path, ["Classic"])
            leda_val_plain = leda_val.get("Plain")

            if leda_val_plain.get("alg_name") == "Stern":
                leda_time = leda_val.get("MRA")
                leda_gje = leda_val_plain.get("gje_cost")
                leda_p = leda_val_plain.get("params").get("p")
                leda_l = leda_val_plain.get("params").get("l")
            else:
                continue
            n, k, t = filename[:-5].split('_')

            writer.writerow([
                int(n),
                int(k),
                int(t),
                float(eb_time),
                float(eb_gje),
                2 * int(eb_p),
                int(eb_l),
                int(eb_m4r),
                float(leda_time),
                float(leda_gje),
                int(leda_p),
                int(leda_l)
            ])


if __name__ == '__main__':
    main()
