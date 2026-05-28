PRIMITIVE_PYTHON_TYPE = "str"
WILDCARD_SEGMENTS = frozenset({"anyHL7Segment"})
DELIM_DEF_SEGMENTS = frozenset({"MSH", "FHS", "BHS"})
DELIM_DEFAULTS = {"1": '"|"', "2": '"^~\\\\&"'}

MAX_WIDTH = 80
FIELD_INDENT = "    "  # 4 spaces  (inside class body)
INNER_INDENT = "        "  # 8 spaces  (Field() kwargs)
ALIAS_INDENT = "            "  # 12 spaces (AliasChoices args)

HL7_NS = "urn:hl7-org:v2xml"
