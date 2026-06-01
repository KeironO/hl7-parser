from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FieldRef:
    xml_name: str
    field_type: str
    long_name: str
    is_primitive: bool
    item_num: str | None = None
    table: str | None = None
    min_occurs: int = 0
    max_occurs: int | None = 1
    max_length: int | None = None
