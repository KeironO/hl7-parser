from __future__ import annotations

from pathlib import Path

from hl7parser.aliases import derive_aliases
from hl7parser.db import load_db
from hl7parser.consts import HL7_NS, STRING_PRIMITIVE_DATATYPES
from hl7parser.generators import (
    generate_datatype,
    generate_group,
    generate_init,
    generate_init_stub,
    generate_message,
    generate_segment,
    generate_version_init,
    generate_version_init_stub,
)
from hl7parser.helpers.name import cardinality, group_class_name, group_field_name
from hl7parser.helpers.string import docstring as make_docstring
from hl7parser.ir import MessageDef, VersionIR


def _normalise_version(version: str) -> str:
    return "v" + version.replace(".", "_")


def _file_header(class_name: str, class_type: str, version: str) -> str:
    return (
        '"""\n'
        f"Profile: {HL7_NS}\n"
        f"Release: v2\n"
        f"Version: {version}\n"
        f"Class: {class_name}\n"
        f"Type: {class_type}\n"
        '"""\n'
    )


def _write(path: Path, class_name: str, class_type: str, version: str, source: str) -> None:
    path.write_text(_file_header(class_name, class_type, version) + source)


def _write_alias(
    path: Path,
    alias: str,
    canonical: str,
    canonical_msg: MessageDef,
    all_seg_names: set[str],
    class_type: str,
    version: str,
) -> None:
    event_id = alias.split("_", 1)[-1]
    ev = load_db(version).events.get(event_id)
    sec = f" (§{ev.section})" if ev and ev.section else ""
    headline = f"{ev.description}{sec}." if ev else f"Alias for {canonical}."

    db = load_db(version)
    doc_entries: list[str] = []
    seen: dict[str, int] = {}
    for member in canonical_msg.members:
        if member.is_group:
            py_type = group_class_name(member.xml_name)
            fname = group_field_name(member.xml_name)
            member_desc = ""
        else:
            py_type = member.xml_name
            fname = member.xml_name
            db_info = db.segments.get(member.xml_name) if member.xml_name in all_seg_names else None
            member_desc = db_info.description if db_info else ""
        if fname in seen:
            seen[fname] += 1
            fname = f"{fname}_{seen[fname]}"
        else:
            seen[fname] = 1
        ann, default = cardinality(member.min_occurs, member.max_occurs, py_type)
        req = "required" if default == "..." else "optional"
        doc_label = f"{member_desc}, {req}" if member_desc else req
        doc_entries.append(f"        {fname} ({ann}): {doc_label}")

    doc_lines = make_docstring(headline, "Attributes", doc_entries)
    source = (
        "from __future__ import annotations\n\n"
        f"from .{canonical} import {canonical}\n\n\n"
        f"class {alias}({canonical}):\n"
        + "\n".join(doc_lines)
        + "\n\n    pass\n"
    )
    path.write_text(_file_header(alias, class_type, version) + source)


def write_version(ir: VersionIR, output_dir: Path, *, for_hl7types: bool = False) -> None:
    mod_name = _normalise_version(ir.version)
    version_dir = output_dir / mod_name
    version_dir.mkdir(parents=True, exist_ok=True)

    all_dt_names = {dt.name for dt in ir.datatypes}
    dt_map = {dt.name: dt for dt in ir.datatypes}
    all_seg_names = {seg.name for seg in ir.segments}
    all_group_names = {group_class_name(grp.name) for grp in ir.groups}

    # datatypes
    dt_dir = version_dir / "datatypes"
    dt_dir.mkdir(exist_ok=True)
    for dt in ir.datatypes:
        if dt.name in STRING_PRIMITIVE_DATATYPES:
            continue
        _write(
            dt_dir / f"{dt.name}.py",
            dt.name,
            "Datatype",
            ir.version,
            generate_datatype(dt, all_dt_names, version=ir.version, for_hl7types=for_hl7types),
        )
    dt_names = [dt.name for dt in ir.datatypes if dt.name not in STRING_PRIMITIVE_DATATYPES]
    (dt_dir / "__init__.py").write_text(generate_init(dt_names))
    (dt_dir / "__init__.pyi").write_text(generate_init_stub(dt_names))

    # segments
    seg_dir = version_dir / "segments"
    seg_dir.mkdir(exist_ok=True)
    for seg in ir.segments:
        _write(
            seg_dir / f"{seg.name}.py",
            seg.name,
            "Segment",
            ir.version,
            generate_segment(
                seg,
                all_dt_names,
                datatype_map=dt_map,
                version=ir.version,
                for_hl7types=for_hl7types,
            ),
        )
    seg_names = [seg.name for seg in ir.segments]
    (seg_dir / "__init__.py").write_text(generate_init(seg_names))
    (seg_dir / "__init__.pyi").write_text(generate_init_stub(seg_names))

    # groups
    grp_dir = version_dir / "groups"
    grp_dir.mkdir(exist_ok=True)
    for grp in ir.groups:
        class_name = group_class_name(grp.name)
        _write(
            grp_dir / f"{class_name}.py",
            grp.name,
            "Group",
            ir.version,
            generate_group(grp, all_seg_names, for_hl7types=for_hl7types, version=ir.version),
        )
    grp_names = sorted(all_group_names)
    (grp_dir / "__init__.py").write_text(generate_init(grp_names))
    (grp_dir / "__init__.pyi").write_text(generate_init_stub(grp_names))

    # messages
    msg_dir = version_dir / "messages"
    msg_dir.mkdir(exist_ok=True)
    canonical_names = {msg.name for msg in ir.messages}
    for msg in ir.messages:
        _write(
            msg_dir / f"{msg.name}.py",
            msg.name,
            "Message",
            ir.version,
            generate_message(msg, all_seg_names, all_group_names, for_hl7types=for_hl7types, version=ir.version),
        )

    aliases = {
        alias: canonical
        for alias, canonical in derive_aliases(ir.version).items()
        if canonical in canonical_names
    }
    msg_map = {msg.name: msg for msg in ir.messages}
    for alias, canonical in sorted(aliases.items()):
        _write_alias(
            msg_dir / f"{alias}.py",
            alias,
            canonical,
            msg_map[canonical],
            all_seg_names,
            "Message",
            ir.version,
        )

    msg_names = sorted(canonical_names | set(aliases))
    (msg_dir / "__init__.py").write_text(generate_init(msg_names))
    (msg_dir / "__init__.pyi").write_text(generate_init_stub(msg_names))

    # version __init__
    (version_dir / "__init__.py").write_text(generate_version_init(mod_name))
    (version_dir / "__init__.pyi").write_text(generate_version_init_stub())

    print(
        f"  [{ir.version}] "
        f"{len(ir.datatypes)} datatypes, "
        f"{len(ir.segments)} segments, "
        f"{len(ir.groups)} groups, "
        f"{len(ir.messages)} messages, "
        f"{len(aliases)} aliases"
    )
