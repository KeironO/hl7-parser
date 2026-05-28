from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hl7parser.parser import HL7XSDParser

from .writer import write_version


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="hl7parser",
        description="Generate Pydantic models from HL7 v2.x XSD files.",
    )
    parser.add_argument(
        "--xsd-dir",
        required=True,
        type=Path,
        help="Root XSD directory containing per-version subdirectories (e.g. 2.5.1/).",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Output directory for generated Python packages (e.g. hl7types/).",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--version",
        metavar="VER",
        help="Single version to generate (e.g. 2.5.1).",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Generate all versions found under --xsd-dir.",
    )

    args = parser.parse_args()

    xsd_root: Path = args.xsd_dir
    output_dir: Path = args.output_dir

    if not xsd_root.is_dir():
        print(f"error: --xsd-dir {xsd_root} is not a directory", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    if args.version:
        versions = [args.version]
    else:
        versions = sorted(d.name for d in xsd_root.iterdir() if d.is_dir())

    for version in versions:
        version_dir = xsd_root / version
        if not version_dir.is_dir():
            print(f"warning: {version_dir} not found, skipping", file=sys.stderr)
            continue
        if not (version_dir / "datatypes.xsd").exists():
            print(f"warning: {version_dir}/datatypes.xsd not found, skipping", file=sys.stderr)
            continue
        print(f"Generating v{version}...")
        irp = HL7XSDParser(version_dir)
        ir = irp.parse_version()
        write_version(ir, output_dir)

    print("Yay!")


if __name__ == "__main__":
    main()
