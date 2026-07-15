"""Access for docstring generation."""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from hl7parser.aliases import _load


@dataclass
class FieldInfo:
    position: int
    name: str
    section: str = ""
    table: str = ""
    item: str = ""
    length: str = ""
    usage: str = ""
    rep: str = ""
    datatype: str = ""


@dataclass
class SegmentInfo:
    description: str
    section: str
    fields: list[FieldInfo] = field(default_factory=list)


@dataclass
class DatatypeInfo:
    description: str
    section: str


@dataclass
class MessageInfo:
    description: str
    section: str


@dataclass
class EventInfo:
    description: str
    section: str


@dataclass
class VersionDB:
    segments: dict[str, SegmentInfo]
    datatypes: dict[str, DatatypeInfo]
    messages: dict[str, MessageInfo]
    events: dict[str, EventInfo]


@lru_cache(maxsize=None)
def load_db(version: str) -> VersionDB:
    raw = _load(version)

    segments = {
        sid: SegmentInfo(
            description=s["description"],
            section=s.get("section", ""),
            fields=[
                FieldInfo(
                    position=f["position"],
                    name=f["name"],
                    section=f.get("section", ""),
                    table=f.get("table", ""),
                    item=f.get("item", ""),
                    length=f.get("length", ""),
                    usage=f.get("usage", ""),
                    rep=f.get("rep", ""),
                    datatype=f.get("datatype", ""),
                )
                for f in s.get("fields", [])
            ],
        )
        for sid, s in raw.get("segments", {}).items()
    }

    datatypes = {
        did: DatatypeInfo(description=d["description"], section=d.get("section", ""))
        for did, d in raw.get("datatypes", {}).items()
    }

    messages = {
        mid: MessageInfo(description=m["description"], section=m.get("section", ""))
        for mid, m in raw.get("messages", {}).items()
    }

    events = {
        eid: EventInfo(description=e["description"], section=e.get("section", ""))
        for eid, e in raw.get("events", {}).items()
    }

    return VersionDB(segments=segments, datatypes=datatypes, messages=messages, events=events)
