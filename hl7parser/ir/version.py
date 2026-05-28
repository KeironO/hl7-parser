from __future__ import annotations

from dataclasses import dataclass

from hl7parser.ir import DataTypeDef, GroupDef, MessageDef, SegmentDef


@dataclass
class VersionIR:
    version: str
    primitives: set[str]
    datatypes: list[DataTypeDef]
    segments: list[SegmentDef]
    groups: list[GroupDef]
    messages: list[MessageDef]
