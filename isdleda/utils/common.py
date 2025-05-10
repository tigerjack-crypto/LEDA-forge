from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import Any, Dict, List, Optional, Tuple


class Attack(StrEnum):
    KeyR1 = auto()
    KeyR2 = auto()
    KeyR3 = auto()
    MsgR = auto()


@dataclass(eq=True, frozen=True, order=True)
class ISDValue:
    n: int
    # r: int
    k: int
    w: int
    # k: int = field(init=False, compare=False)
    msgs: List[str] = field(default_factory=list, compare=False)


# especially useful for json
def dict_to_isd_value(dct):
    if 'n' in dct and 'k' in dct and 'w' in dct:
        return ISDValue(**dct)
    raise Exception("Wrong dictionary for ISDValue")


@dataclass(eq=True, frozen=True, order=True)
class LEDAValue:
    p: int
    n0: int
    t: int
    v: int
    tau: Optional[int] = field(default=None, compare=False)
    msgs: List[str] = field(default_factory=list, compare=False)


def dict_to_leda_value(dct):
    if 'p' in dct and 'n0' in dct and 't' in dct and 'v' in dct:
        return LEDAValue(**dct)
    raise Exception("Wrong dictionary for LEDAValue")


@dataclass(order=True)
class LEDAValueAttackCost:
    ledaval: LEDAValue
    c_costs: Dict[Attack, float]
    q_costs: Dict[Attack, float]
    c_best: Tuple[Attack, float]
    q_best: Tuple[Attack, float]
    msgs: Optional[Dict[str, Any]] = field(default=None, compare=False)


@dataclass(order=True)
class ISDVariant:
    value: ISDValue
    attack: Attack = field(compare=False)
    isd_variant: str
    isd_variant_options: Dict[str, Any]
