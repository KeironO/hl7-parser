from __future__ import annotations

from dataclasses import dataclass

from hl7parser.ir import ComponentDef


@dataclass
class DataTypeDef:
    name: str
    components: list[ComponentDef]
