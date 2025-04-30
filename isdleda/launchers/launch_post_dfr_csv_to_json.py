from isdleda.launchers.launcher_utils import OUT_DIR
from isdleda.utils.export.export import ISDValueEncoder, from_csv_to_ledavalue, save_to_json
from isdleda.utils.common import ISDValue
from typing import List
import os

# the 0-th time this is launched
ITERATION=0

isd_values: List[ISDValue] = []
for level in (1, 3, 5):
    filename = f"/mnt/data/simone/vc/crypto/leda_design/stime_ISD/post_dfr_in/{ITERATION}/cat_{level}_region"
    ledavalues = from_csv_to_ledavalue(f"{filename}.csv")

    for leda_val in ledavalues:
        # MRA
        n = leda_val.p * leda_val.n0
        k = leda_val.p * (leda_val.n0 - 1)
        t = leda_val.t
        isd_values.append(ISDValue(n, n - k, t, msgs=[f"MRA"]))

        # KRA 1
        n = leda_val.p * leda_val.n0  #
        k = leda_val.p * (leda_val.n0 - 1)  #
        t = leda_val.v * 2
        isd_values.append(ISDValue(n, n - k, t, msgs=[f"KRA 1"]))

        # KRA 2
        if leda_val.n0 != 2:
            n = 2 * leda_val.p
            k = leda_val.p
            t = leda_val.v * 2
            isd_values.append(ISDValue(n, n - k, t, msgs=[f"KRA 2"]))

        # KRA 3
        n = leda_val.p * leda_val.n0
        k = leda_val.p
        t = leda_val.v * leda_val.n0

        isd_values.append(ISDValue(n, n - k, t, msgs=[f"KRA 3"]))

print(len(isd_values))
filename = os.path.join(OUT_DIR, "isd-leda", "values",
                        f"post_dfr_out", f"{ITERATION}", "isd_values.json")
save_to_json(filename, isd_values, cls=ISDValueEncoder)
