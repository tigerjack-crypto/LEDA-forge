import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum, auto
from typing import Any, Dict, List, Optional


class Attacks(StrEnum):
    KeyR1 = auto()
    KeyR2 = auto()
    KeyR3 = auto()
    MsgR = auto()


@dataclass(eq=True, frozen=True, order=True)
class ISDValue:
    n: int
    r: int
    t: int
    # k: int = field(init=False, compare=False)
    msgs: List[str] = field(default_factory=list, compare=False)

class ISDValueEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, ISDValue):
            return asdict(obj)
        return super().default(obj)


@dataclass(eq=True, frozen=True, order=True)
class LEDAValue:
    p: int
    n0: int
    t: int
    v: int
    tau: Optional[int] = field(default=None, compare=False)
    msgs: List[str] = field(default_factory=list, compare=False)


class LEDAValueEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, LEDAValue):
            return asdict(obj)
        return super().default(obj)


# especially useful for json
def dict_to_isd_value(dct):
    if 'n' in dct and 'r' in dct and 't' in dct:
        return ISDValue(**dct)
    return dct


def dict_to_leda_value(dct):
    if 'p' in dct and 'n0' in dct and 't' in dct and 'v' in dct:
        return LEDAValue(**dct)
    return dct


@dataclass(order=True)
class ISDVariant:
    value: ISDValue
    attack: Attacks = field(compare=False)
    isd_variant: str
    isd_variant_options: Dict[str, Any]
