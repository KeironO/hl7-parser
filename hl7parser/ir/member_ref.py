from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MemberRef:
    xml_name: str
    is_group: bool
    min_occurs: int = 0
    max_occurs: int | None = 1
