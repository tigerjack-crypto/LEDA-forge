import csv
import fcntl
import os
import re
import sys
from dataclasses import asdict, dataclass, fields, field
from typing import ClassVar, List, Optional, Set, Tuple


@dataclass(frozen=True)
class SearchParamsResult:
    N: int
    K: int
    W: int
    problem: str
    attack: str

    I: Optional[int] = None
    RE: Optional[int] = None
    X: Optional[int] = None
    YX: Optional[int] = None
    P: Optional[int] = None
    L: Optional[int] = None
    L0: Optional[int] = None
    L1: Optional[int] = None
    WI: Optional[int] = None
    PI: Optional[int] = None
    PIJ: Optional[int] = None
    D: Optional[int] = None
    Z: Optional[int] = None
    QU: Optional[int] = None
    QF: Optional[int] = None
    QU0: Optional[int] = None
    QF0: Optional[int] = None
    WI0: Optional[int] = None
    QU1: Optional[int] = None
    QF1: Optional[int] = None
    WI1: Optional[int] = None
    FW: Optional[int] = None
    CP: Optional[int] = None
    CS: Optional[int] = None

    cost: Optional[int] = None
    lgratio: Optional[Tuple[float, ...]] = None
    lgcost: Optional[Tuple[float, ...]] = None
    prob: Optional[Tuple[float, ...]] = None
    lgprob: Optional[Tuple[float, ...]] = None

    # # Class-level config: fields to include in equality/hash
    # _compare_fields: Set[str] = field(default_factory=lambda: {"N", "K", "W", "problem", "attack"}, repr=False, compare=False, hash=False)

    # def __eq__(self, other):
    #     if not isinstance(other, SearchParamsResult):
    #         return NotImplemented
    #     return all(
    #         getattr(self, f) == getattr(other, f)
    #         for f in self._compare_fields)

    # def __hash__(self):
    #     return hash(tuple(getattr(self, f) for f in self._compare_fields))


def parse_list(text: str) -> Optional[List[float]]:
    try:
        return [float(x.strip()) for x in text.strip("[]").split(',')]
    except ValueError:
        return None


def parse_searchparams_line(line: str) -> SearchParamsResult:
    if "searchparams" in line:
        line = line.split("searchparams", 1)[1].strip()

    fields = {}

    # Combined pattern:
    pattern = re.finditer(
        r"""
        (\b\w+)=([^\s,\[]+)              # key=value
        |(\b\w+)\s+\[([^\]]+)\]          # key [list]
        |(\b\w+)\s+([^\s\[]+)            # key value
    """, line, re.VERBOSE)
    for match in pattern:
        if match.group(1):  # key=value
            key, val = match.group(1), match.group(2)
            # print("1",key, val)
            if key == 'problem':
                fields['problem'] = val
            elif key == 'attack':
                fields['attack'] = val
            else:
                fields[key] = int(val)
        elif match.group(3):  # key [list]
            key, val = match.group(3), match.group(4)
            # print("3",key, val)

            parsed_list = parse_list(f"[{val}]")
            if parsed_list:
                fields[key] = parsed_list
        elif match.group(5):  # key value
            # should be only for cost
            key, val = match.group(5), match.group(6)
            # print("5",key, val)
            # in theory it's an integer, but it can be very large
            fields[key] = val

    required = ['N', 'K', 'W', 'problem', 'attack']
    for r in required:
        if r not in fields:
            raise ValueError(f"Missing required field '{r}' in line")

    return SearchParamsResult(**fields)


def append_result_to_csv(result: SearchParamsResult,
                         filepath: str,
                         should_lock=False):
    # Only include fields defined in the dataclass
    allowed_fields = [f.name for f in fields(SearchParamsResult)]
    result_dict = asdict(result)

    row = {}
    field_names = []

    for name in allowed_fields:
        val = result_dict.get(name)
        if isinstance(val, list) or isinstance(val, tuple):
            for i, v in enumerate(val):
                col_name = f"{name}_{i}"
                field_names.append(col_name)
                row[col_name] = v
        else:
            field_names.append(name)
            row[name] = val

    # Write header if file doesn't exist or is empty
    write_header = not os.path.exists(filepath) or os.path.getsize(
        filepath) == 0

    with open(filepath, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=field_names)
        if should_lock:
            fcntl.flock(f, fcntl.LOCK_EX)
        if write_header:
            writer.writeheader()
        writer.writerow(row)
        if should_lock:
            fcntl.flock(f, fcntl.LOCK_UN)


def load_results_from_csv(filepath: str) -> List[SearchParamsResult]:
    # Get the set of dataclass fields
    field_defs = {f.name: f.type for f in fields(SearchParamsResult)}
    list_fields = {
        name
        for name, typ in field_defs.items()
        if typ in [Optional[List[float]], Optional[Tuple[float, ...]]]
    }

    results = []

    with open(filepath, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed = {}
            list_field_buffers = {name: [] for name in list_fields}

            for key, value in row.items():
                if value == '':
                    continue  # Skip missing values

                # Handle flattened list fields
                for lf in list_fields:
                    if key.startswith(f"{lf}_"):
                        try:
                            list_field_buffers[lf].append(float(value))
                        except ValueError:
                            pass
                        break
                else:
                    # Handle scalar fields
                    field_type = field_defs.get(key)
                    if field_type in [int, Optional[int]]:
                        parsed[key] = int(value)
                    elif field_type in [str, Optional[str]]:
                        parsed[key] = value
                    elif field_type in [float, Optional[float]]:
                        parsed[key] = float(value)

            # Attach collected list fields
            for lf, val in list_field_buffers.items():
                if val:
                    parsed[lf] = val

            # Instantiate the dataclass
            results.append(SearchParamsResult(**parsed))

    return results


def _test_a():
    line1 = "N=1284,W=24 attack=isd0,P=0,L=0,FW=1 searchparams problem=uniformmatrix N=1284,K=1020,W=24 attack=isd0 I=65536,RE=1,X=1,YX=1,P=0,L=0,Z=0,QU=1,QF=1,FW=1 lgratio [85.990064,85.9900642] cost 76211124242999 lgcost [46.1150668,46.1150669] prob [9.91812895e-13,9.91812898e-13] lgprob [-39.8749973,-39.8749972]"
    line2 = "N=1284,W=24 attack=isd2,PI=2,PIJ=1,CP=1,CS=0,FW=1 searchparams problem=uniformmatrix N=1284,K=1020,W=24 attack=isd2 I=1,RE=1,X=1,YX=1,PIJ=1,PI=2,L0=9,L1=16,CP=1,CS=0,D=21,Z=0,QU0=5,QF0=6,WI0=4,QU1=5,QF1=288,WI1=1,FW=1 lgratio [70.9699274,70.9699275] cost 701475184 lgcost [29.3858168,29.3858169] prob [3.03343965e-13,3.03343966e-13] lgprob [-41.5841107,-41.5841106]"
    line = line1
    print(line)
    parsed = parse_searchparams_line(line)
    print(parsed)


def _test_b():
    input_file = sys.argv[1]

    with open(input_file, 'r') as f:
        for line in f.readlines():
            parsed = parse_searchparams_line(line)
            print(parsed)


if __name__ == '__main__':
    _test_b()
