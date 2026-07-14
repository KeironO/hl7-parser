from hl7parser.consts import FIELD_INDENT, PRIMITIVE_PYTHON_TYPE, STRING_PRIMITIVE_DATATYPES
from hl7parser.db import load_db
from hl7parser.generators.multi_field import make_field
from hl7parser.helpers.name import cardinality, field_name, xml_to_field_name
from hl7parser.helpers.string import numpy_docstring
from hl7parser.ir import DataTypeDef
from hl7parser.primitive_validators import (
    _TS_PRE25_KEY,
    FIELD_VALIDATORS,
    TS_PRE25_XML_NAME,
    _is_v25_or_later,
    fallback_validator_imports,
    make_field_validators,
    needs_validation_info,
)


def generate_datatype(
    dt: DataTypeDef,
    all_datatype_names: set[str],
    *,
    version: str = "2.5.1",
    for_hl7types: bool = False,
) -> str:
    imports: list[str] = []
    fields: list[list[str]] = []
    doc_entries: list[tuple[str, str, str]] = []
    need_list = False
    # {validator_key: [field_name, ...]} — groups fields that share a validator
    validator_fields: dict[str, list[str]] = {}
    pre_v25 = not _is_v25_or_later(version)

    for comp in dt.components:
        vkey = None
        if comp.is_primitive or comp.base_type not in all_datatype_names or comp.base_type in STRING_PRIMITIVE_DATATYPES:
            py_type = PRIMITIVE_PYTHON_TYPE
            if comp.is_primitive:
                if pre_v25 and comp.xml_name == TS_PRE25_XML_NAME and comp.base_type == "ST":
                    vkey = _TS_PRE25_KEY
                elif comp.base_type in FIELD_VALIDATORS:
                    vkey = comp.base_type
                if vkey:
                    validator_fields.setdefault(vkey, [])
        else:
            py_type = comp.base_type
            imports.append(f"from .{py_type} import {py_type}")

        ann, default = cardinality(comp.min_occurs, comp.max_occurs, py_type)
        if "List[" in ann:
            need_list = True

        fname = xml_to_field_name(comp.xml_name)
        long_alias = field_name(comp.long_name, comp.xml_name)
        flags = ["opt" if comp.min_occurs == 0 else "req"]
        if comp.max_occurs is None or comp.max_occurs > 1:
            flags.append("rep")
        desc = f"{comp.xml_name} ({', '.join(flags)}) - {comp.long_name} ({comp.base_type})"
        doc_entries.append((fname, ann, desc))
        fields.append(
            make_field(
                fname,
                ann,
                default,
                fname,
                long_alias,
                comp.xml_name,
                title=comp.long_name,
                max_length=comp.max_length if comp.is_primitive else None,
                min_occurs=comp.min_occurs,
            )
        )

        if vkey and comp.is_primitive:
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
        if for_hl7types and needs_validation_info(validator_fields):
            pydantic_parts.append("ValidationInfo")
    if for_hl7types:
        if pydantic_parts:
            out.append(f"from pydantic import {', '.join(pydantic_parts)}")
        out.append("from hl7types.hl7 import HL7Model")
        out.extend(fallback_validator_imports(validator_fields))
    else:
        pydantic_parts_with_base = ["BaseModel"] + pydantic_parts
        out.append(f"from pydantic import {', '.join(pydantic_parts_with_base)}")
    if unique_imports:
        out.append("")
        out.extend(unique_imports)
    out.append("")
    out.append("")
    base = "HL7Model" if for_hl7types else "BaseModel"
    out.append(f"class {dt.name}({base}):")
    db_dt = load_db(version).datatypes.get(dt.name)
    if db_dt and db_dt.description:
        sec = f" (S{db_dt.section})" if db_dt.section else ""
        headline = f"{db_dt.description.capitalize()}{sec}."
    else:
        headline = f"HL7 v2 {dt.name} data type."
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
    out.append(f'{FIELD_INDENT}model_config = {{"populate_by_name": True}}')
    out.append("")
    return "\n".join(out)
