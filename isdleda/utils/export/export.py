import os
import json
import pickle
from typing import Any


def save_to_pickle(filename: str, obj: Any):
    os.makedirs(filename[:filename.rfind(os.path.sep)], exist_ok=True)
    with open(filename + ".pkl", "wb") as fp:
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
    with open(filename + ".json", "w") as fp:
        json.dump(
            obj,
            fp,
            indent=4,
            ensure_ascii=False,
        )
