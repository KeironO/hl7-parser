"""Derive trigger-event to canonical-structure aliases."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DATA_DIR = Path(__file__).parent / "data" / "hl7db"


@lru_cache(maxsize=None)
def _load(version: str) -> dict:
    path = _DATA_DIR / f"{version}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def derive_aliases(version: str) -> dict[str, str]:
    """Return ``{trigger_name: canonical_name}`` for *version*."""
    return _load(version).get("aliases", {})
