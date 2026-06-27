"""
Inline field validator generation for HAPI-equivalent primitive datatype validation.

Regexes taken verbatim from HAPI's DefaultValidationWithoutTNBuilder.
Each entry in FIELD_VALIDATORS maps an HL7 primitive type name to the
(validator_fn_name, regex_pattern, error_description) needed to emit a
@field_validator in the generated class body.

Types that need no validation beyond max_length (ST, TX, FT, ID, IS) are absent.
"""

from __future__ import annotations

from hl7parser.consts import FIELD_INDENT, INNER_INDENT

# (validator function name, regex string as it appears in re.compile(), error label)
FIELD_VALIDATORS: dict[str, tuple[str, str, str]] = {
    "SI": ("_validate_si", r"\d*", "empty or a non-negative integer"),
    "NM": ("_validate_nm", r"(\+|\-)?\d*\.?\d*", "empty or numeric"),
    "DT": (
        "_validate_dt",
        r"(\d{4}([01]\d(\d{2})?)?)?",
        "empty or a valid HL7 date (YYYY[MM[DD]])",
    ),
    "TM": (
        "_validate_tm",
        r"([012]\d([0-5]\d([0-5]\d(\.\d(\d(\d(\d)?)?)?)?)?)?)?([+\-]\d{4})?",
        "empty or a valid HL7 time",
    ),
    "DTM": (
        "_validate_dtm",
        r"(\d{4}([01]\d(\d{2}([012]\d([0-5]\d([0-5]\d(\.\d(\d(\d(\d)?)?)?)?)?)?)?)?)?)?([+\-]\d{4})?",
        "empty or a valid HL7 datetime",
    ),
    "NULLDT": ("_validate_nulldt", None, "always empty (withdrawn datatype)"),
    # TS.1 in pre-v2.5 XSDs has base_type ST; detected by xml_name instead.
    "_TS_PRE25": (
        "_validate_ts_pre25",
        r"(\d{4}([01]\d(\d{2}([012]\d[0-5]\d([0-5]\d(\.\d(\d(\d(\d)?)?)?)?)?)?)?)?)?([+\-]\d{4})?",
        "empty or a valid HL7 pre-v2.5 datetime",
    ),
}

# xml_name that triggers pre-v2.5 TS validation when base_type is ST
TS_PRE25_XML_NAME = "TS.1"
_TS_PRE25_KEY = "_TS_PRE25"


def _is_v25_or_later(version: str) -> bool:
    try:
        parts = [int(x) for x in version.split(".")]
        major = parts[0] if len(parts) > 0 else 0
        minor = parts[1] if len(parts) > 1 else 0
        return (major, minor) >= (2, 5)
    except (ValueError, IndexError):
        return True


# Validator keys that support context-aware fallback parsing via _apply_dt_fallback.
# Maps key -> context key name used to look up the user-supplied parser callable.
_FALLBACK_VALIDATORS: dict[str, str] = {
    "DTM": "dtm_parser",
    "_TS_PRE25": "dt_parser",
}


def needs_validation_info(validator_fields: dict[str, list[str]]) -> bool:
    """Return True if any of the validators require ValidationInfo (context-aware)."""
    return any(k in _FALLBACK_VALIDATORS for k in validator_fields)


def make_field_validators(validator_fields: dict[str, list[str]]) -> list[str]:
    """
    Return source lines for all @field_validator methods needed by a class.

    """
    out: list[str] = []
    for key, fnames in validator_fields.items():
        if not fnames:
            continue
        fn_name, pattern, description = FIELD_VALIDATORS[key]
        field_args = ", ".join(f'"{f}"' for f in fnames)
        out.append(f"{FIELD_INDENT}@field_validator({field_args}, mode='before')")
        out.append(f"{FIELD_INDENT}@classmethod")

        if key in _FALLBACK_VALIDATORS:
            ctx_key = _FALLBACK_VALIDATORS[key]
            datatype = "DTM" if key == "DTM" else "DT"
            out.append(f"{FIELD_INDENT}def {fn_name}(cls, v: str, info: ValidationInfo) -> str:")
            out.append(f"{INNER_INDENT}import re")
            out.append(f"{INNER_INDENT}if re.fullmatch(r'{pattern}', v or ''):")
            out.append(f"{INNER_INDENT}    return v")
            out.append(f"{INNER_INDENT}from hl7types.hl7._validators import _apply_dt_fallback")
            out.append(f"{INNER_INDENT}ctx = info.context or {{}}")
            out.append(
                f'{INNER_INDENT}return _apply_dt_fallback(v, parser=ctx.get("{ctx_key}"), datatype="{datatype}", field_path="TS.1")'
            )
        elif key == "NULLDT":
            out.append(f"{FIELD_INDENT}def {fn_name}(cls, v: str) -> str:")
            out.append(f'{INNER_INDENT}if v != "":')
            out.append(
                f'{INNER_INDENT}    raise ValueError(f"NULLDT is a withdrawn datatype and must be empty, got {{v!r}}")'
            )
            out.append(f"{INNER_INDENT}return v")
        else:
            out.append(f"{FIELD_INDENT}def {fn_name}(cls, v: str) -> str:")
            out.append(f"{INNER_INDENT}import re")
            out.append(f"{INNER_INDENT}if not re.fullmatch(r'{pattern}', v or ''):")
            out.append(f'{INNER_INDENT}    raise ValueError(f"{{v!r}} is not {description}")')
            out.append(f"{INNER_INDENT}return v")

        out.append("")
    return out
