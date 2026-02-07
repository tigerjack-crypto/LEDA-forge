# to include submodules in the PATH
import os
import sys
from unittest.mock import MagicMock

# Create a MagicMock for the prettytable module
print("WARN: Mocking unused pretty-table")
mock_prettytable = MagicMock()
mock_table_instance = MagicMock()
# Mock the PrettyTable class to return a mock instance
mock_prettytable.PrettyTable.return_value = mock_table_instance
# Inject the mocked module into sys.modules
sys.modules['prettytable'] = mock_prettytable

# Add CE submodule to path
thisdir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(
    os.path.join(thisdir, "..", "..", "..", "submodules",
                 "cryptographic_estimators"))
# sys.path.append(os.path.join(thisdir, "..", "..", "submodules", "isd_scripts"))
# print(f"INFO: sys path is {sys.path}")
