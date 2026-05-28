from hl7parser.consts import DELIM_DEF_SEGMENTS, DELIM_DEFAULTS, FIELD_INDENT, PRIMITIVE_PYTHON_TYPE
from hl7parser.generators.multi_field import make_field
from hl7parser.helpers.name import cardinality, field_name, xml_to_field_name
from hl7parser.ir import SegmentDef


def generate_segment(seg: SegmentDef, all_datatype_names: set[str]) -> str:
    imports: list[str] = []
    fields: list[list[str]] = []
    need_list = False
    seen_field_names: dict[str, int] = {}

    for field in seg.fields:
        if field.is_primitive or field.field_type not in all_datatype_names:
            py_type = PRIMITIVE_PYTHON_TYPE
        else:
            py_type = field.field_type
            imports.append(f"from ..datatypes.{py_type} import {py_type}")

        ann, default = cardinality(field.min_occurs, field.max_occurs, py_type)
        if "List[" in ann:
            need_list = True

        fname = xml_to_field_name(field.xml_name)
        long_alias = field_name(field.long_name, field.xml_name)
        if fname in seen_field_names:
            seen_field_names[fname] += 1
            fname = f"{fname}_{seen_field_names[fname]}"
        else:
            seen_field_names[fname] = 1

        pos_suffix = field.xml_name.rsplit(".", 1)[-1]
        if seg.name in DELIM_DEF_SEGMENTS and pos_suffix in DELIM_DEFAULTS:
            default = DELIM_DEFAULTS[pos_suffix]

        # title = human name; description = HL7 metadata (item / table)
        meta_parts: list[str] = []
        if field.item_num:
            meta_parts.append(f"Item #{field.item_num}")
        if field.table:
            meta_parts.append(f"Table {field.table}")

        fields.append(
            make_field(
                fname,
                ann,
                default,
                fname,
                long_alias,
                field.xml_name,
                title=field.long_name,
                description=" | ".join(meta_parts),
            )
        )

    unique_imports = sorted(set(imports))
    out: list[str] = ["from __future__ import annotations", ""]
    typing_parts = ["Optional"]
    if need_list:
        typing_parts.append("List")
    out.append(f"from typing import {', '.join(typing_parts)}")
    out.append("from pydantic import AliasChoices, BaseModel, Field")
    if unique_imports:
        out.append("")
        out.extend(unique_imports)
    out.append("")
    out.append("")
    out.append(f"class {seg.name}(BaseModel):")
    out.append(f'{FIELD_INDENT}"""HL7 v2 {seg.name} segment."""')
    out.append("")
    if fields:
        for i, field_lines in enumerate(fields):
            out.extend(field_lines)
            if i < len(fields) - 1:
                out.append("")
    else:
        out.append(f"{FIELD_INDENT}pass")
    out.append("")
    out.append(f'{FIELD_INDENT}model_config = {{"populate_by_name": True}}')
    out.append("")
    return "\n".join(out)
