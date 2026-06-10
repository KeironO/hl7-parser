from hl7parser.consts import DELIM_DEF_SEGMENTS, DELIM_DEFAULTS, FIELD_INDENT, PRIMITIVE_PYTHON_TYPE, STRING_PRIMITIVE_DATATYPES
from hl7parser.generators.multi_field import make_field
from hl7parser.helpers.name import cardinality, field_name, xml_to_field_name
from hl7parser.helpers.string import numpy_docstring
from hl7parser.ir import DataTypeDef, SegmentDef
from hl7parser.primitive_validators import (
    _TS_PRE25_KEY,
    FIELD_VALIDATORS,
    TS_PRE25_XML_NAME,
    _is_v25_or_later,
    make_field_validators,
)


def _has_required_components(dt: DataTypeDef) -> bool:
    return any(c.min_occurs >= 1 for c in dt.components)


def generate_segment(
    seg: SegmentDef,
    all_datatype_names: set[str],
    *,
    datatype_map: dict[str, DataTypeDef] | None = None,
    version: str = "2.5.1",
    for_hl7types: bool = False,
) -> str:
    imports: list[str] = []
    fields: list[list[str]] = []
    doc_entries: list[tuple[str, str, str]] = []
    need_list = False
    seen_field_names: dict[str, int] = {}
    validator_fields: dict[str, list[str]] = {}
    pre_v25 = not _is_v25_or_later(version)

    for field in seg.fields:
        vkey = None
        if field.is_primitive or field.field_type not in all_datatype_names or field.field_type in STRING_PRIMITIVE_DATATYPES:
            py_type = PRIMITIVE_PYTHON_TYPE
            if field.is_primitive:
                if pre_v25 and field.xml_name == TS_PRE25_XML_NAME and field.field_type == "ST":
                    vkey = _TS_PRE25_KEY
                elif field.field_type in FIELD_VALIDATORS:
                    vkey = field.field_type
                if vkey:
                    validator_fields.setdefault(vkey, [])
        else:
            py_type = field.field_type
            imports.append(f"from ..datatypes.{py_type} import {py_type}")

        is_rep = field.max_occurs is None or field.max_occurs > 1
        effective_min = field.min_occurs

        ann, default = cardinality(effective_min, field.max_occurs, py_type)
        if "List[" in ann:
            need_list = True

        fname = xml_to_field_name(field.xml_name)
        long_alias = field_name(field.long_name, field.xml_name)
        if fname in seen_field_names:
            seen_field_names[fname] += 1
            fname = f"{fname}_{seen_field_names[fname]}"
        else:
            seen_field_names[fname] = 1

        flags = ["opt" if field.min_occurs == 0 else "req"]
        if field.max_occurs is None or field.max_occurs > 1:
            flags.append("rep")
        desc = f"{field.xml_name} ({', '.join(flags)}) - {field.long_name} ({field.field_type})"
        if effective_min != field.min_occurs:
            desc += f" [optional: {field.field_type} has no required components]"
        doc_entries.append((fname, ann, desc))

        pos_suffix = field.xml_name.rsplit(".", 1)[-1]
        if seg.name in DELIM_DEF_SEGMENTS and pos_suffix in DELIM_DEFAULTS:
            default = DELIM_DEFAULTS[pos_suffix]

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
                max_length=field.max_length if field.is_primitive else None,
                min_occurs=effective_min,
            )
        )

        if vkey and field.is_primitive:
            validator_fields[vkey].append(fname)

    unique_imports = sorted(set(imports))
    need_optional = any("Optional[" in entry[1] for entry in doc_entries)
    need_alias_choices = bool(fields)
    need_field = bool(fields)

    out: list[str] = ["from __future__ import annotations", ""]
    typing_parts = []
    if need_optional:
        typing_parts.append("Optional")
    if need_list:
        typing_parts.append("List")
    if typing_parts:
        out.append(f"from typing import {', '.join(typing_parts)}")
    pydantic_parts = []
    if need_alias_choices:
        pydantic_parts.append("AliasChoices")
    if need_field:
        pydantic_parts.append("Field")
    if validator_fields:
        pydantic_parts.append("field_validator")
    if for_hl7types:
        if pydantic_parts:
            out.append(f"from pydantic import {', '.join(pydantic_parts)}")
        out.append("from hl7types.hl7 import HL7Model")
    else:
        pydantic_parts_with_base = ["BaseModel"] + pydantic_parts
        out.append(f"from pydantic import {', '.join(pydantic_parts_with_base)}")
    if unique_imports:
        out.append("")
        out.extend(unique_imports)
    out.append("")
    out.append("")
    base = "HL7Model" if for_hl7types else "BaseModel"
    out.append(f"class {seg.name}({base}):")
    out.extend(numpy_docstring(f"HL7 v2 {seg.name} segment.", doc_entries))
    out.append("")
    if fields:
        for i, field_lines in enumerate(fields):
            out.extend(field_lines)
            if i < len(fields) - 1:
                out.append("")
    else:
        out.append(f"{FIELD_INDENT}pass")
    out.append("")
    if validator_fields:
        out.extend(make_field_validators(validator_fields))
    out.append(f'{FIELD_INDENT}model_config = {{"populate_by_name": True}}')
    out.append("")
    return "\n".join(out)
