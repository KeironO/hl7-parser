from __future__ import annotations

from dataclasses import dataclass

from hl7parser.ir.datatype_def import DataTypeDef
from hl7parser.ir.group_def import GroupDef
from hl7parser.ir.message_def import MessageDef
from hl7parser.ir.segment_def import SegmentDef


@dataclass
class VersionIR:
    version: str
    primitives: set[str]
    datatypes: list[DataTypeDef]
    segments: list[SegmentDef]
    groups: list[GroupDef]
    messages: list[MessageDef]
