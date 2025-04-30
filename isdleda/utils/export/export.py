import csv
import json
import os
import pickle
from dataclasses import asdict
from pathlib import Path
from typing import Any, List

from isdleda.utils.common import ISDValue, LEDAValue, dict_to_isd_value, dict_to_leda_value


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
        fn = filename + ".pkl" if not Path(
            filename).suffix == ".pkl" else filename
        if fn == filename:
            raise e
        with open(fn, "rb") as fp:
            return pickle.load(fp)


def load_from_json(filename: str, **kwargs) -> Any:
    try:
        with open(filename, "r") as fp:
            return json.load(fp, **kwargs)
    except FileNotFoundError as e:
        fn = filename + ".json" if not Path(
            filename).suffix == ".json" else filename
        if fn == filename:
            raise e
        with open(fn, "r") as fp:
            return json.load(fp, **kwargs)


def save_to_txt(filename: str, obj: Any):
    fn = filename + ".txt" if not Path(filename).suffix == ".txt" else filename
    try:
        with open(fn, "w") as fp:
            print(obj, file=fp)
    except FileNotFoundError:
        os.makedirs(filename[:filename.rfind(os.path.sep)], exist_ok=True)
        print(obj, file=fp)


def save_to_json(filename: str, obj: Any, cls=None):
    fn = filename + ".json" if not Path(
        filename).suffix == ".json" else filename
    try:
        with open(fn, "w") as fp:
            json.dump(
                obj,
                fp,
                indent=4,
                ensure_ascii=False,
                cls=cls,
            )
    except FileNotFoundError:
        os.makedirs(filename[:filename.rfind(os.path.sep)], exist_ok=True)
        save_to_json(filename, obj)


class LEDAValueEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, LEDAValue):
            return asdict(obj)
        return super().default(obj)

def ledavalue_decoder(data):
    """For leda values"""
    if isinstance(data, dict):
        if 'p' in data and 'n0' in data and 't' in data and 'v' in data:
            return dict_to_leda_value(data)
        return {key: ledavalue_decoder(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [ledavalue_decoder(item) for item in data]
    else:
        return data


def save_ledavalues_to_csv(isdvalues: List[LEDAValue], csv_file: str):
    # Get the field names from the ISDValue dataclass (excluding 'k')
    fieldnames = ['p', 'n0', 'v', 't']

    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for isdvalue in isdvalues:
            # Convert each ISDValue instance to a dictionary
            row = asdict(isdvalue)
            # Serialize the 'msgs' list to a string
            writer.writerow(row)


class ISDValueEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, ISDValue):
            return asdict(obj)
        return super().default(obj)


def save_isdvalues_to_csv(isdvalues: List[ISDValue], csv_file: str):
    # Get the field names from the ISDValue dataclass (excluding 'k')
    fieldnames = ['n', 'r', 't']

    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for isdvalue in isdvalues:
            # Convert each ISDValue instance to a dictionary
            row = asdict(isdvalue)
            # Serialize the 'msgs' list to a string
            writer.writerow(row)

def isdvalue_decoder(data):
    """For leda values"""
    if isinstance(data, dict):
        if 'n' in data and 'r' in data and 't' in data:
            return dict_to_isd_value(data)
        return {key: isdvalue_decoder(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [isdvalue_decoder(item) for item in data]
    else:
        return data

def from_csv_to_isdvalue(csv_path: str) -> List[ISDValue]:
    result = []
    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            n = int(row['n'])
            r = int(row['r'])
            t = int(row['t'])
            msgs = row.get('msgs', '')
            msgs_list = [msg.strip() for msg in msgs.split(';') if msg.strip()]
            result.append(ISDValue(n=n, r=r, t=t, msgs=msgs_list))
    return result

def from_csv_to_ledavalue(csv_path: str) -> List[LEDAValue]:
    result = []
    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            p = int(row['p'])
            n0 = int(row['n0'])
            t = int(row['t'])
            v = int(row['v'])
            tau_raw = row.get('tau', '')
            tau = int(tau_raw) if tau_raw.strip() else None
            msgs = row.get('msgs', '')
            msgs_list = [msg.strip() for msg in msgs.split(';') if msg.strip()]
            result.append(LEDAValue(p=p, n0=n0, t=t, v=v, tau=tau, msgs=msgs_list))
    return result
