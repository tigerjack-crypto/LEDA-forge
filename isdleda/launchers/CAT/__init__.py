import os
import sys

thisdir = os.path.dirname(os.path.realpath(__file__))
bin_path = os.path.join(thisdir, "..", "..", "..", "submodules", "CryptAttackTester")
os.environ["PATH"] = bin_path + os.pathsep + os.environ.get("PATH", "")
print(f"INFO: sys path is {sys.path}")
