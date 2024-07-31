import json
import os
from isdleda.utils.export.export import save_to_json
# from isdleda.utils.paths import ISD_VALUES_FILE_JSON
from dataclasses import asdict

# Official NIST values
AES_LAMBDAS = (143, 207, 272)
# Values taken from my Ph.D. Thesis, table 6.5 (Jan+22). Nist uses the ones
# from Jaques though.
QAES_LAMBDAS = (154, 219, 283)


def main():
    with open('out/isd_values.json', 'rb') as f:
        isdval = json.load(f)

    to_discard_set = set()
    # the most expensive costs shoud be with MEM_SQRT
    DIR = 'out/cisd_eb/pkl/MEM_SQRT/'
    for filename in os.listdir(DIR):
        with open(DIR + filename, 'rb') as f:
            eb_val = json.load(f)

        min_val = eb_val['MinimumTime'][1]['estimate']['time']
        if min_val < AES_LAMBDAS[0] - 30 or min_val > AES_LAMBDAS[2] + 30:
            to_discard_set.add(filename)
    # just for quick access
    new_isd_vals = []
    useless = []
    for val in isdval:
        search_val = f"{val.n:06}_{val.n - val.r:06}_{val.t:03}.pkl"
        if search_val not in to_discard_set:
            new_isd_vals.append(val)
        else:
            useless.append(val)
            # print(val)
    print("no. of isd values")
    print(f"OLD: {len(isdval)}")
    print(f"NEW: {len(new_isd_vals)}")
    print(f"USELESS: {len(useless)}")

    # print(f"Pickling to {ISD_VALUES_FILE_PKL}")
    # save_to_pickle(ISD_VALUES_FILE_PKL, new_isd_vals)
    filename = os.path.join("out", "values", "from_useless", "isd_values.json")
    print(
        f"JSONing to {filename}")
    save_to_json(filename,
                 [asdict(x) for x in sorted(new_isd_vals)])

    filename = os.path.join("out", "values", "from_useless", "isd_values_useless.json")
    print(f"JSONing useless to {filename}")
    save_to_json(filename, [asdict(x) for x in sorted(useless)])


if __name__ == '__main__':
    main()
