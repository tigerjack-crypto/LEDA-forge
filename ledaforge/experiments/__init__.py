# to include CryptographicEstimators in the PATH
import os
import sys

thisdir = os.path.dirname(os.path.realpath(__file__))
print(thisdir)
sys.path.append(os.path.join(thisdir, "..", "..", "submodules", "cryptographic_estimators"))
