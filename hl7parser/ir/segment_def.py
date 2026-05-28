from __future__ import annotations

from dataclasses import dataclass

from hl7parser.ir.field_ref import FieldRef


@dataclass
class SegmentDef:
    name: str
    fields: list[FieldRef]
