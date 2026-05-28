from __future__ import annotations

from dataclasses import dataclass

from hl7parser.ir import GroupDef, MemberRef


@dataclass
class MessageDef:
    name: str
    groups: list[GroupDef]
    members: list[MemberRef]
