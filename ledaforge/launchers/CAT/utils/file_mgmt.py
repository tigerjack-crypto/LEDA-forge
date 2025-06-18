import os

OUT_FILES_PART_FMT = ("{n:06}_{k:06}_{w:03}.{ext}")
OUT_DIR = os.path.join('..', 'leda_design', 'stime_ISD', 'CAT', 'out', ("{hostname}"))
OUT_FILE = os.path.join(OUT_DIR, OUT_FILES_PART_FMT)
OUT_DIR_MIN = os.path.join('..', 'leda_design', 'stime_ISD', 'CAT',
                            ("txt-{isd}"))
OUT_FILE_MIN = os.path.join(OUT_DIR_MIN, OUT_FILES_PART_FMT)
