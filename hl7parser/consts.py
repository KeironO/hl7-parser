PRIMITIVE_PYTHON_TYPE = "str"
# HL7 datatypes that are plain strings with no sub-components in the spec.
# Mapped to `str` directly; no model class is generated for them.
# https://hl7.eu/refactored/dtTX.html
STRING_PRIMITIVE_DATATYPES = frozenset({"FT", "TX"})
WILDCARD_SEGMENTS = frozenset({"anyHL7Segment"})
DELIM_DEF_SEGMENTS = frozenset({"MSH", "FHS", "BHS"})
DELIM_DEFAULTS = {"1": '"|"', "2": '"^~\\\\&"'}

MAX_WIDTH = 80
FIELD_INDENT = "    "  # 4 spaces  (inside class body)
INNER_INDENT = "        "  # 8 spaces  (Field() kwargs)
ALIAS_INDENT = "            "  # 12 spaces (AliasChoices args)

HL7_NS = "urn:hl7-org:v2xml"
