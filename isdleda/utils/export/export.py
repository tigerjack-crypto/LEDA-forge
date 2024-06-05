import os
import json
import pickle
from typing import Any
from pathlib import Path


def save_to_pickle(filename: str, obj: Any):
    os.makedirs(filename[:filename.rfind(os.path.sep)], exist_ok=True)
    fn = filename + ".pkl" if not Path(filename).suffix == ".pkl" else filename
    with open(fn, "wb") as fp:
        pickle.dump(obj, fp)


def load_from_pickle(filename: str) -> Any:
    with open(filename, "rb") as fp:
        return pickle.load(fp)


def save_to_txt(filename: str, obj: Any):
    os.makedirs(filename[:filename.rfind(os.path.sep)], exist_ok=True)
    with open(filename + ".txt", "w") as fp:
        print(obj, file=fp)


def save_to_json(filename: str, obj: Any):
    os.makedirs(filename[:filename.rfind(os.path.sep)], exist_ok=True)
    fn = filename + ".json" if not Path(
        filename).suffix == ".json" else filename
    with open(fn, "w") as fp:
        json.dump(
            obj,
            fp,
            indent=4,
            ensure_ascii=False,
        )
