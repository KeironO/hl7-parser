import keyword
import re


def to_snake_case(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    text = text.lower().strip()
    text = re.sub(r"\s+", "_", text)
    text = text.strip("_")
    if not text or text[0].isdigit():
        text = f"field_{text}"
    if keyword.iskeyword(text) or keyword.issoftkeyword(text):
        text = f"{text}_"
    return text or "field"


def xml_to_field_name(xml_name: str) -> str:
    return xml_name.replace(".", "_").lower()


def field_name(long_name: str, xml_name: str) -> str:
    name = to_snake_case(long_name)
    if not name or name == "field":
        name = xml_to_field_name(xml_name)
    return name


def cardinality(min_o: int, max_o: int | None, type_str: str) -> tuple[str, str]:
    is_list = max_o is None or max_o > 1
    is_required = min_o >= 1 and not is_list
    if is_list:
        if min_o >= 1:
            return f"List[{type_str}]", "..."
        return f"Optional[List[{type_str}]]", "None"
    if is_required:
        return type_str, "..."
    return f"Optional[{type_str}]", "None"


def group_class_name(xml_name: str) -> str:
    """'ADT_A01.PROCEDURE' 'ADT_A01_PROCEDURE', hyphens also replaced."""
    return xml_name.replace(".", "_").replace("-", "_")


def group_field_name(xml_name: str) -> str:
    """'ADT_A01.PROCEDURE' 'PROCEDURE', hyphens replaced."""
    return xml_name.split(".")[-1].replace("-", "_")
