from hl7parser.consts import FIELD_INDENT, PRIMITIVE_PYTHON_TYPE
from hl7parser.generators.multi_field import make_field
from hl7parser.helpers.name import cardinality, field_name, xml_to_field_name
from hl7parser.ir import DataTypeDef


def generate_datatype(dt: DataTypeDef, all_datatype_names: set[str]) -> str:
    imports: list[str] = []
    fields: list[list[str]] = []
    need_list = False

    for comp in dt.components:
        if comp.is_primitive or comp.base_type not in all_datatype_names:
            py_type = PRIMITIVE_PYTHON_TYPE
        else:
            py_type = comp.base_type
            imports.append(f"from .{py_type} import {py_type}")

        ann, default = cardinality(comp.min_occurs, comp.max_occurs, py_type)
        if "List[" in ann:
            need_list = True

        fname = xml_to_field_name(comp.xml_name)
        long_alias = field_name(comp.long_name, comp.xml_name)
        fields.append(
            make_field(
                fname,
                ann,
                default,
                fname,
                long_alias,
                comp.xml_name,
                title=comp.long_name,
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
    out.append(f"class {dt.name}(BaseModel):")
    out.append(f'{FIELD_INDENT}"""HL7 v2 {dt.name} data type."""')
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
