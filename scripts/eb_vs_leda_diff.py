import csv
import json
import os
from pathlib import Path

# DIR1 = os.path.join("sshfs_mountpoint", "vc", "isd-leda", "out", "cisd_eb",
#                     "json", "MEM_LOG")
# DIR2 = os.path.join("sshfs_mountpoint", "vc", "LEDAtools", "out", "results",
#                     "json")

# Server directories and files
# DIR1 = '/home/sperriello/vc/isd-leda/out/cisd_eb/json/MEM_LOG/'
DIR1 = '/home/sperriello/vc/isd-leda/out/cisd_eb/json/MEM_LOG/'
DIR2 = '/home/sperriello/vc/LEDAtools/out/results/json/'
OUT_FILE = 'out/eb_vs_leda_diff.csv'


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
    files_in_dir1 = set([Path(filename).stem for filename in os.listdir(DIR1)])
    print(f"Get list of files for {DIR2}")
    files_in_dir2 = set([Path(filename).stem for filename in os.listdir(DIR2)])

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
            'n',
            'k',
            't',  #
            'EB Stern time',
            'LEDA Stern time',  #
            'EB GJE',
            'LEDA GJE',  #
            'EB Stern p',
            'LEDA Stern p',  #
            'EB Stern l',
            'LEDA Stern l',
            'EB Stern M4R',
        ])
        for filename in common_files:
            eb_path = os.path.join(DIR1, filename)
            leda_path = os.path.join(DIR2, filename)

            with open(eb_path + ".json", "r") as fp:
                eb_val = json.load(fp)
            eb_val = eb_val['Stern']
            eb_val_estimate = eb_val.get("estimate")
            eb_time = eb_val_estimate.get("time")
            eb_gje = eb_val.get("additional_information").get("gauss")
            eb_p = eb_val_estimate.get("parameters").get("p")
            eb_l = eb_val_estimate.get("parameters").get("l")
            eb_m4r = eb_val_estimate.get("parameters").get("r")

            with open(leda_path + ".json", "r") as fp:
                data = json.load(fp)
            # leda_val = extract_value_from_json(leda_path, ["Classic"])
            leda_val = data["Classic"]
            leda_val_plain = leda_val.get("Plain")

            if leda_val_plain.get("alg_name") == "Stern":
                leda_time = leda_val.get("MRA")
                leda_gje = leda_val_plain.get("gje_cost")
                leda_p = leda_val_plain.get("params").get("p")
                leda_l = leda_val_plain.get("params").get("l")
            else:
                continue
            n, k, t = filename.split('_')

            writer.writerow([
                int(n),
                int(k),
                int(t),
                float(eb_time),
                float(leda_time),
                float(eb_gje),
                float(leda_gje),
                2 * int(eb_p),
                int(leda_p),
                int(eb_l),
                int(leda_l),
                int(eb_m4r),
            ])


if __name__ == '__main__':
    main()
