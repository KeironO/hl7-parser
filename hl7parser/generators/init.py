def _fmt_names(names: list[str]) -> str:
    indent = "    "
    rows: list[str] = []
    current = indent
    for i, name in enumerate(sorted(names)):
        item = f"'{name}'" + ("," if i < len(names) - 1 else "")
        if current != indent and len(current) + 1 + len(item) > 79:
            rows.append(current)
            current = indent + item
        else:
            current = (current + " " + item) if current != indent else indent + item
    if current != indent:
        rows.append(current)
    return "_NAMES = {\n" + "\n".join(rows) + "\n}"


def generate_init(names: list[str], import_from: str = ".") -> str:
    lines = [
        "import importlib",
        "",
        _fmt_names(names),
        "",
        "",
        "def __getattr__(name: str):  # type: ignore[misc]",
        "    if name not in _NAMES:",
        "        raise AttributeError(f'module {__name__!r} has no attribute {name!r}')",
        "    mod = importlib.import_module(f'.{name}', __name__)",
        "    return getattr(mod, name)",
    ]
    return "\n".join(lines) + "\n"


def generate_init_stub(names: list[str]) -> str:
    lines = [f"from .{name} import {name} as {name}" for name in sorted(names)]
    return "\n".join(lines) + "\n"


def generate_version_init(module_name: str) -> str:
    lines = [
        "import importlib",
        "",
        "_NAMES = {'datatypes', 'groups', 'messages', 'segments'}",
        "",
        "",
        "def __getattr__(name: str):  # type: ignore[misc]",
        "    if name not in _NAMES:",
        "        raise AttributeError(f'module {__name__!r} has no attribute {name!r}')",
        "    mod = importlib.import_module(f'.{name}', __name__)",
        "    return mod",
    ]
    return "\n".join(lines) + "\n"


def generate_version_init_stub() -> str:
    lines = [
        f"from . import {sub} as {sub}" for sub in ("datatypes", "groups", "messages", "segments")
    ]
    return "\n".join(lines) + "\n"
