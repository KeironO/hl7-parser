# hl7-parser

A little Python tool that parses HL7 v2 specification files and generates Python classes from them.

This project is heavily inspired by [Nazrul Islam](https://github.com/nazrulworld)'s excellent work on `fhir-parser` and `fhir.resources`. His approach to bringing modern Python tooling and Pydantic support to healthcare data standards showed the way forward. This tool applies that same philosophy to HL7 v2.

## Overview

The parser reads HL7 v2 XSD specification files and generates strongly-typed Python classes from them. This makes it easier to work with HL7 v2 data in modern Python applications with full IDE support and type hints.

The generated classes are used by the companion library [hl7types](https://github.com/KeironO/hl7types), which provides a Pydantic-based client for HL7 v2.

## Installation

Requires Python 3.9+ and `uv` to be installed. Install dependencies with:

```bash
uv sync
```

## Usage

Generate classes for all HL7 v2 specifications:

```bash
uv run python -m hl7parser --xsd-dir /path/to/hl7v2xsd --output-dir /tmp/ --all
```

Replace `/path/to/hl7v2xsd` with the directory containing your HL7 v2 XSD files.

## How It Works

The parser reads HL7 v2 XSD files (datatypes, fields, segments, and message definitions) and converts them into an intermediate representation. This is then used to generate Pydantic model classes for:

- **Datatypes** - Composite data types like XCN (extended person name), AD (address), etc.
- **Segments** - Individual segments like MSH (message header), PID (patient identification), etc.
- **Groups** - Repeating segment groups within messages (e.g. PROCEDURE in ADT_A01)
- **Messages** - Complete message structures like ADT_A01, ACK, etc.

Each generated class includes:

- Type hints for IDE support and static analysis
- Pydantic validation
- Field metadata (HL7 item numbers, reference tables, long names)
- Proper handling of required vs optional fields and repetition

Note: The parser handles most HL7 v2 patterns, but there may be edge cases that aren't fully covered. The generated output should be validated for your use case.

## Output

Generated classes are organised by version under the output directory:

```
hl7types/
├── v2_5_1/
│   ├── datatypes/     # Composite data types
│   ├── segments/      # Individual segments
│   ├── groups/        # Message groups
│   ├── messages/      # Complete message structures
│   └── __init__.py
└── v2_4/
    └── ...
```

## License

This project is licensed under the MIT License. See the LICENSE file for details.

HL7 is the registered trademark of HL7 International.