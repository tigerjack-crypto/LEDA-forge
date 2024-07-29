import json
import os
import pickle
from pathlib import Path
from typing import Any


def save_to_pickle(filename: str, obj: Any):
    fn = filename + ".pkl" if not Path(filename).suffix == ".pkl" else filename
    try:
        with open(fn, "wb") as fp:
            pickle.dump(obj, fp)
    except FileNotFoundError:
        os.makedirs(filename[:filename.rfind(os.path.sep)], exist_ok=True)
        save_to_pickle(filename, obj)


def load_from_pickle(filename: str) -> Any:
    try:
        with open(filename, "rb") as fp:
            return pickle.load(fp)
    except FileNotFoundError as e:
        fn = filename + ".pkl" if not Path(filename).suffix == ".pkl" else filename
        if fn == filename:
            raise e
        with open(fn, "rb") as fp:
            return pickle.load(fp)

def load_from_json(filename: str) -> Any:
    try:
        with open(filename, "r") as fp:
            return json.load(fp)
    except FileNotFoundError as e:
        fn = filename + ".json" if not Path(filename).suffix == ".json" else filename
        if fn == filename:
            raise e
        with open(fn, "r") as fp:
            return json.load(fp)



def save_to_txt(filename: str, obj: Any):
    fn = filename + ".txt" if not Path(filename).suffix == ".txt" else filename
    try:
        with open(fn, "w") as fp:
            print(obj, file=fp)
    except FileNotFoundError:
        os.makedirs(filename[:filename.rfind(os.path.sep)], exist_ok=True)
        print(obj, file=fp)


def save_to_json(filename: str, obj: Any):
    fn = filename + ".json" if not Path(
        filename).suffix == ".json" else filename
    try:
        with open(fn, "w") as fp:
            json.dump(
                obj,
                fp,
                indent=4,
                ensure_ascii=False,
            )
    except FileNotFoundError:
        os.makedirs(filename[:filename.rfind(os.path.sep)], exist_ok=True)
        save_to_json(filename, obj)
