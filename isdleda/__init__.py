# to include CryptographicEstimators in the PATH
import os
import sys

thisdir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(thisdir, "..", "submodules"))
