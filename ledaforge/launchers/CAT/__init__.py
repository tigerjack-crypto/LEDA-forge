import os

thisdir = os.path.dirname(os.path.realpath(__file__))
bin_path = os.path.join(thisdir, "..", "..", "..", "submodules", "cryptattacktester-20231020")
os.environ["PATH"] = bin_path + os.pathsep + os.environ.get("PATH", "")
print(os.environ['PATH'])
