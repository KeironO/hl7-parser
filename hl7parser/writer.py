from __future__ import annotations

from pathlib import Path

from hl7parser.consts import HL7_NS
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
from hl7parser.helpers.name import group_class_name
from hl7parser.ir import VersionIR


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


def write_version(ir: VersionIR, output_dir: Path, *, for_hl7types: bool = False) -> None:
    mod_name = _normalise_version(ir.version)
    version_dir = output_dir / mod_name
    version_dir.mkdir(parents=True, exist_ok=True)

    all_dt_names = {dt.name for dt in ir.datatypes}
    all_seg_names = {seg.name for seg in ir.segments}
    all_group_names = {group_class_name(grp.name) for grp in ir.groups}

    # datatypes
    dt_dir = version_dir / "datatypes"
    dt_dir.mkdir(exist_ok=True)
    for dt in ir.datatypes:
        _write(
            dt_dir / f"{dt.name}.py",
            dt.name,
            "Datatype",
            ir.version,
            generate_datatype(dt, all_dt_names, for_hl7types=for_hl7types),
        )
    dt_names = [dt.name for dt in ir.datatypes]
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
            generate_segment(seg, all_dt_names, for_hl7types=for_hl7types),
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
            generate_group(grp, all_seg_names, for_hl7types=for_hl7types),
        )
    grp_names = sorted(all_group_names)
    (grp_dir / "__init__.py").write_text(generate_init(grp_names))
    (grp_dir / "__init__.pyi").write_text(generate_init_stub(grp_names))

    # messages
    msg_dir = version_dir / "messages"
    msg_dir.mkdir(exist_ok=True)
    for msg in ir.messages:
        _write(
            msg_dir / f"{msg.name}.py",
            msg.name,
            "Message",
            ir.version,
            generate_message(msg, all_seg_names, all_group_names, for_hl7types=for_hl7types),
        )
    msg_names = [msg.name for msg in ir.messages]
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
        f"{len(ir.messages)} messages"
    )
