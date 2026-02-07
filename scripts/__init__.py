# to include CryptographicEstimators in the PATH
import os
import sys

thisdir = os.path.dirname(os.path.realpath(__file__))
# sys.path.append(os.path.join(thisdir))
sys.path.append(os.path.join(thisdir, "..", "submodules", "cryptographic_estimators"))
sys.path.append(os.path.join(thisdir, "..", "submodules", "isd_scripts"))
sys.path.append(os.path.join(thisdir, ".."))
# print(f"From isdleda: {sys.path}")
