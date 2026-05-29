from hl7parser.consts import FIELD_INDENT, WILDCARD_SEGMENTS
from hl7parser.generators.multi_field import make_member_field
from hl7parser.helpers.name import cardinality, group_class_name, group_field_name
from hl7parser.helpers.string import docstring
from hl7parser.ir import GroupDef


def generate_group(grp: GroupDef, known_segments: set[str]) -> str:
    segment_imports: set[str] = set()
    group_imports: set[str] = set()
    lines: list[str] = []
    doc_entries: list[str] = []
    need_list = False
    need_any = False
    # Map from original type name to alias used in annotations to deal with Python 3.14 fuckery
    type_aliases: dict[str, str] = {}  # orig to alias

    for member in grp.members:
        if member.xml_name in WILDCARD_SEGMENTS or (
            not member.is_group and member.xml_name not in known_segments
        ):
            need_any = True
            py_type = "Any"
            fname = member.xml_name.lower()
        elif member.is_group:
            class_name = group_class_name(member.xml_name)
            group_imports.add(f"from .{class_name} import {class_name}")
            py_type = class_name
            fname = group_field_name(member.xml_name)
        else:
            seg = member.xml_name
            segment_imports.add(f"from ..segments.{seg} import {seg}")
            py_type = seg
            fname = seg

        ann, default = cardinality(member.min_occurs, member.max_occurs, py_type)
        if "List[" in ann:
            need_list = True

        req = "required" if default == "..." else "optional"
        doc_entries.append(f"        {fname} ({ann}): {req}")

        if py_type == "Any":
            if default == "...":
                lines.append(f"{FIELD_INDENT}{fname}: {ann}")
            else:
                lines.append(f"{FIELD_INDENT}{fname}: {ann} = None")
        else:
            # Always alias: Field(default=...) also assigns to the name in the
            # class dict, which shadows the import under Python 3.14 lazy eval.
            if py_type not in type_aliases:
                type_aliases[py_type] = f"_{py_type}"
            alias = type_aliases[py_type]
            aliased_ann = ann.replace(py_type, alias)
            lines.extend(
                make_member_field(fname, aliased_ann, default, member.min_occurs, member.max_occurs)
            )
        lines.append("")

    class_name = group_class_name(grp.name)
    out: list[str] = ["from __future__ import annotations", ""]
    typing_parts = ["Optional"]
    if need_list:
        typing_parts.append("List")
    if need_any:
        typing_parts.append("Any")
    out.append(f"from typing import {', '.join(typing_parts)}")
    out.append("from pydantic import BaseModel, Field")
    if segment_imports:
        out.append("")
        out.extend(sorted(segment_imports))
    if group_imports:
        out.append("")
        out.extend(sorted(group_imports))
    if type_aliases:
        out.append("")
        for orig, alias in sorted(type_aliases.items()):
            out.append(f"{alias} = {orig}")
    out.append("")
    out.append("")
    out.append(f"class {class_name}(BaseModel):")
    out.extend(docstring(f"HL7 v2 {grp.name} group.", "Attributes", doc_entries))
    out.append("")
    if lines:
        out.extend(lines)
    else:
        out.append(f"{FIELD_INDENT}pass")
        out.append("")
    out.append(f'{FIELD_INDENT}model_config = {{"populate_by_name": True}}')
    out.append("")
    return "\n".join(out)
