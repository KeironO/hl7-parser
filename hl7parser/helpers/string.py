from hl7parser.consts import FIELD_INDENT, INNER_INDENT, MAX_WIDTH


def _esc(text: str) -> str:
    """Escape for embedding inside a double-quoted Python string literal."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def str_kwarg(name: str, text: str) -> list[str]:
    """Emit  ``name="<text>",`` wrapping long values with parenthesised
    implicit string concatenation at 80 chars."""
    escaped = _esc(text)
    single = f'{INNER_INDENT}{name}="{escaped}",'
    if len(single) <= MAX_WIDTH:
        return [single]

    # Wrap: split at word boundaries into <= 72-char chunks (room for quotes and
    # indent), emit as parenthesised implicit concatenation.
    chunk_width = MAX_WIDTH - len(INNER_INDENT) - 4  # quotes + indent
    words = escaped.split()
    lines: list[str] = [f"{INNER_INDENT}{name}=("]
    current = ""
    for word in words:
        candidate = (current + " " + word).lstrip() if current else word
        if len(candidate) > chunk_width and current:
            lines.append(f'{INNER_INDENT}    "{current} "')
            current = word
        else:
            current = candidate
    if current:
        lines.append(f'{INNER_INDENT}    "{current}"')
    lines.append(f"{INNER_INDENT}),")
    return lines


def docstring(headline: str, section: str, entries: list[str]) -> list[str]:
    """Return indented docstring lines."""
    headline = headline.replace('"', '\\"')
    if not entries:
        return [f'{FIELD_INDENT}"""{headline}"""']
    out = [f'{FIELD_INDENT}"""{headline}', "", f"{FIELD_INDENT}{section}:"]
    out.extend(entries)
    out.append(f'{FIELD_INDENT}"""')
    return out


def _ann_to_union(ann: str) -> str:
    if ann.startswith("Optional[List[") and ann.endswith("]]"):
        return f"list[{ann[14:-2]}] | None"
    if ann.startswith("Optional[") and ann.endswith("]"):
        return f"{ann[9:-1]} | None"
    if ann.startswith("List[") and ann.endswith("]"):
        return f"list[{ann[5:-1]}]"
    return ann


def numpy_docstring(headline: str, entries: list[tuple[str, str, str]]) -> list[str]:
    """Return indented NumPy-style docstring lines.

    entries: list of (field_name, annotation, description)
    """
    if not entries:
        return [f'{FIELD_INDENT}"""{headline}"""']
    out = [
        f'{FIELD_INDENT}"""{headline}',
        "",
        f"{FIELD_INDENT}Attributes",
        f"{FIELD_INDENT}----------",
    ]
    for i, (fname, ann, desc) in enumerate(entries):
        out.append(f"{FIELD_INDENT}{fname} : {_ann_to_union(ann)}")
        out.append(f"{INNER_INDENT}{desc}")
        if i < len(entries) - 1:
            out.append("")
    out.append(f'{FIELD_INDENT}"""')
    return out
