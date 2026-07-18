from hl7parser.consts import (
    DELIM_DEF_SEGMENTS,
    DELIM_DEFAULTS,
    FIELD_INDENT,
    PRIMITIVE_PYTHON_TYPE,
    STRING_PRIMITIVE_DATATYPES,
)
from hl7parser.db import load_db
from hl7parser.generators.multi_field import make_field
from hl7parser.helpers.name import cardinality, field_name, xml_to_field_name
from hl7parser.helpers.string import numpy_docstring
from hl7parser.ir import DataTypeDef, SegmentDef
from hl7parser.primitive_validators import (
    _TS_PRE25_KEY,
    FIELD_VALIDATORS,
    TS_PRE25_XML_NAME,
    _is_v25_or_later,
    fallback_validator_imports,
    make_field_validators,
    make_regex_constants,
    needs_validation_info,
)


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

    db_seg = load_db(version).segments.get(seg.name)
    db_fields_by_pos = {f.position: f for f in db_seg.fields} if db_seg else {}

    for field in seg.fields:
        vkey = None
        if (
            field.is_primitive
            or field.field_type not in all_datatype_names
            or field.field_type in STRING_PRIMITIVE_DATATYPES
        ):
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

        try:
            pos = int(field.xml_name.rsplit(".", 1)[-1])
            db_field = db_fields_by_pos.get(pos)
        except (ValueError, IndexError):
            db_field = None

        usage = (
            db_field.usage
            if db_field and db_field.usage
            else ("R" if field.min_occurs > 0 else "O")
        )
        rep_flag = "Y" if (field.max_occurs is None or field.max_occurs > 1) else ""
        desc = f"{field.xml_name} - {field.long_name} ({field.field_type}) {usage}"
        if rep_flag:
            desc += " rep"
        if db_field:
            if db_field.section:
                desc += f" S{db_field.section}"
            if db_field.table:
                desc += f" | {db_field.table}"
        doc_entries.append((fname, ann, desc))

        pos_suffix = field.xml_name.rsplit(".", 1)[-1]
        if seg.name in DELIM_DEF_SEGMENTS and pos_suffix in DELIM_DEFAULTS:
            default = DELIM_DEFAULTS[pos_suffix]

        item = db_field.item if db_field and db_field.item else field.item_num or ""
        db_length = (
            int(db_field.length)
            if db_field
            and db_field.length
            and db_field.length.isdigit()
            and int(db_field.length) > 0
            else None
        )
        doc_length = db_length if field.is_primitive else None

        table = (
            db_field.table
            if db_field and db_field.table
            else (f"{field.table}" if field.table else "")
        )
        meta_parts: list[str] = [usage]
        if item:
            meta_parts.append(f"Item #{item}")
        if table:
            meta_parts.append(f"Table {table}")
        if doc_length:
            meta_parts.append(f"LEN:{doc_length}")

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
                min_occurs=field.min_occurs,
            )
        )

        if vkey and field.is_primitive:
            validator_fields[vkey].append(fname)

    unique_imports = sorted(set(imports))
    need_optional = any("Optional[" in entry[1] for entry in doc_entries)
    need_alias_choices = bool(fields)
    need_field = bool(fields)

    out: list[str] = ["from __future__ import annotations", ""]
    if validator_fields:
        out.append("import re")
        out.append("")
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
        if for_hl7types and needs_validation_info(validator_fields):
            pydantic_parts.append("ValidationInfo")
    pydantic_parts.append("ConfigDict")
    if for_hl7types:
        out.append(f"from pydantic import {', '.join(sorted(pydantic_parts))}")
        out.append("from hl7types.hl7 import HL7Model")
        out.extend(fallback_validator_imports(validator_fields))
    else:
        pydantic_parts_with_base = ["BaseModel"] + pydantic_parts
        out.append(f"from pydantic import {', '.join(sorted(pydantic_parts_with_base))}")
    if unique_imports:
        out.append("")
        out.extend(unique_imports)
    out.append("")
    if validator_fields:
        out.extend(make_regex_constants(validator_fields))
        out.append("")
    out.append("")
    base = "HL7Model" if for_hl7types else "BaseModel"
    out.append(f"class {seg.name}({base}):")
    if db_seg and db_seg.description:
        sec = f" (S{db_seg.section})" if db_seg.section else ""
        headline = f"{db_seg.description}{sec}."
    else:
        headline = f"HL7 v2 {seg.name} segment."
    out.extend(numpy_docstring(headline, doc_entries))
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
    out.append(f"{FIELD_INDENT}model_config = ConfigDict(populate_by_name=True)")
    out.append("")
    return "\n".join(out)
