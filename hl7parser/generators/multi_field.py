from hl7parser.consts import ALIAS_INDENT, FIELD_INDENT, INNER_INDENT
from hl7parser.helpers.string import str_kwarg


def make_field(
    fname: str,
    ann: str,
    default: str,
    short_name: str,
    long_alias: str,
    ser_alias: str,
    title: str,
    description: str = "",
) -> list[str]:
    """Return indented lines for one Field() declaration."""
    out = [f"{FIELD_INDENT}{fname}: {ann} = Field("]
    out.append(f"{INNER_INDENT}default={default},")
    out.append(f"{INNER_INDENT}validation_alias=AliasChoices(")
    out.append(f'{ALIAS_INDENT}"{short_name}",')
    out.append(f'{ALIAS_INDENT}"{long_alias}",')
    out.append(f'{ALIAS_INDENT}"{ser_alias}",')
    out.append(f"{INNER_INDENT}),")
    out.append(f'{INNER_INDENT}serialization_alias="{ser_alias}",')
    if title:
        out.extend(str_kwarg("title", title))
    if description:
        out.extend(str_kwarg("description", description))
    out.append(f"{FIELD_INDENT})")
    return out


def make_member_field(
    fname: str,
    ann: str,
    default: str,
    min_occurs: int,
    max_occurs: int | None,
) -> list[str]:
    """Return indented lines for a group/message member Field() declaration."""
    repeating = max_occurs is None or max_occurs > 1
    required = min_occurs >= 1
    cardinality = ("Required" if required else "Optional") + (", repeating" if repeating else "")
    out = [f"{FIELD_INDENT}{fname}: {ann} = Field("]
    out.append(f"{INNER_INDENT}default={default},")
    out.extend(str_kwarg("title", fname))
    out.extend(str_kwarg("description", cardinality))
    out.append(f"{FIELD_INDENT})")
    return out
