from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import Any, Dict, List, Optional


class Attacks(StrEnum):
    KeyR1 = auto()
    KeyR2 = auto()
    KeyR3 = auto()
    MsgR = auto()


@dataclass(eq=True, frozen=True, order=True)
class Value:
    n: int
    r: int
    t: int
    # k: int = field(init=False, compare=False)
    prime: Optional[int] = field(default=None, compare=False)
    n0: Optional[int] = field(default=None, compare=False)
    v: Optional[int] = field(default=None, compare=False)
    lambd: Optional[int] = field(default=None, compare=False)
    msgs: List[str] = field(default_factory=list, compare=False)


@dataclass(order=True)
class ISDVariant:
    value: Value
    attack: Attacks = field(compare=False)
    isd_variant: str
    isd_variant_options: Dict[str, Any]
