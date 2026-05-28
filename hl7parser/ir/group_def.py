from __future__ import annotations

from dataclasses import dataclass

from hl7parser.ir import MemberRef


@dataclass
class GroupDef:
    name: str
    members: list[MemberRef]
