from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ComponentDef:
    xml_name: str
    long_name: str
    base_type: str
    is_primitive: bool
    min_occurs: int = 0
    max_occurs: int | None = 1  # None = unbounded
    max_length: int | None = None
