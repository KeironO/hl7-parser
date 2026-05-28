def generate_init(names: list[str], import_from: str = ".") -> str:
    lines = [f"from {import_from}{name} import {name}" for name in sorted(names)]
    return "\n".join(lines) + "\n"


def generate_version_init(module_name: str) -> str:
    return "from . import datatypes, groups, messages, segments\n"
