from __future__ import annotations

from dataclasses import dataclass

from hl7parser.ir.group_def import GroupDef
from hl7parser.ir.member_ref import MemberRef


@dataclass
class MessageDef:
    name: str
    groups: list[GroupDef]
    members: list[MemberRef]
