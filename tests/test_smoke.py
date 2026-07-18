from __future__ import annotations

import sys
import types
from typing import Any

import pydantic
import pytest

from hl7parser.generators.datatype import generate_datatype
from hl7parser.generators.group import generate_group
from hl7parser.generators.message import generate_message
from hl7parser.generators.segment import generate_segment
from hl7parser.ir import (
    ComponentDef,
    DataTypeDef,
    FieldRef,
    GroupDef,
    MemberRef,
    MessageDef,
    SegmentDef,
)


def _exec_source(source: str, name: str = "generated") -> dict[str, Any]:
    """Execute *source* in a real module so Pydantic can resolve annotations."""
    module = types.ModuleType(name)
    module.pydantic = pydantic
    sys.modules[name] = module
    compiled = compile(source, f"{name}.py", "exec")
    exec(compiled, module.__dict__)
    return module.__dict__


class TestGenerateDatatype:
    def test_basic_output(self) -> None:
        dt = DataTypeDef(
            name="SI",
            components=[
                ComponentDef(
                    xml_name="SI.1",
                    long_name="Sequence ID",
                    base_type="SI",
                    is_primitive=True,
                    min_occurs=0,
                    max_occurs=1,
                    max_length=4,
                ),
            ],
        )
        source = generate_datatype(dt, {"SI"}, version="2.5.1")

        assert "model_config = ConfigDict(populate_by_name=True)" in source
        assert "_RE_SI = re.compile(r'\\d*')" in source
        assert "_RE_SI.fullmatch(v or '')" in source
        assert source.count("import re") == 1  # module-level only
        assert "re.fullmatch(r'" not in source  # no inline recompilation

        namespace = _exec_source(source, "SI")
        cls = namespace["SI"]
        assert cls.model_config["populate_by_name"] is True
        # Empty string and valid integer are accepted by the SI validator.
        assert cls(si_1="").si_1 == ""
        assert cls(si_1="123").si_1 == "123"
        with pytest.raises(pydantic.ValidationError):
            cls(si_1="abc")

    def test_fallback_validator_imports_for_hl7types(self) -> None:
        dt = DataTypeDef(
            name="DTM",
            components=[
                ComponentDef(
                    xml_name="DTM.1",
                    long_name="DateTime",
                    base_type="DTM",
                    is_primitive=True,
                    min_occurs=0,
                    max_occurs=1,
                ),
            ],
        )
        source = generate_datatype(dt, {"DTM"}, version="2.5.1", for_hl7types=True)

        assert "from pydantic import" in source and "ValidationInfo" in source
        assert "from hl7types.hl7._validators import _apply_dt_fallback" in source
        assert "_RE_DTM = re.compile" in source
        assert "_RE_DTM.fullmatch(v or '')" in source
        assert source.count("import re") == 1

    def test_duplicate_field_names_are_deduplicated(self) -> None:
        dt = DataTypeDef(
            name="DUP",
            components=[
                ComponentDef(
                    xml_name="DUP.1",
                    long_name="Value",
                    base_type="ST",
                    is_primitive=True,
                    min_occurs=0,
                    max_occurs=1,
                ),
                ComponentDef(
                    xml_name="DUP.1",
                    long_name="Value Again",
                    base_type="ST",
                    is_primitive=True,
                    min_occurs=0,
                    max_occurs=1,
                ),
            ],
        )
        source = generate_datatype(dt, set(), version="2.5.1")

        assert "dup_1: Optional[str]" in source
        assert "dup_1_2: Optional[str]" in source

        namespace = _exec_source(source, "DUP")
        cls = namespace["DUP"]
        assert "dup_1" in cls.model_fields
        assert "dup_1_2" in cls.model_fields


class TestGenerateSegment:
    def test_basic_output(self) -> None:
        seg = SegmentDef(
            name="TEST",
            fields=[
                FieldRef(
                    xml_name="TEST.1",
                    field_type="ST",
                    long_name="Test Field",
                    is_primitive=True,
                    min_occurs=0,
                    max_occurs=1,
                ),
            ],
        )
        source = generate_segment(seg, set(), version="2.5.1")

        assert "model_config = ConfigDict(populate_by_name=True)" in source
        assert "import re" not in source  # no validators -> no re import

        namespace = _exec_source(source, "TEST")
        cls = namespace["TEST"]
        assert cls.model_config["populate_by_name"] is True
        instance = cls(test_1="hello")
        assert instance.test_1 == "hello"

    def test_validation_info_import_for_hl7types(self) -> None:
        seg = SegmentDef(
            name="TEST",
            fields=[
                FieldRef(
                    xml_name="TEST.1",
                    field_type="DTM",
                    long_name="Test DateTime",
                    is_primitive=True,
                    min_occurs=0,
                    max_occurs=1,
                ),
            ],
        )
        source = generate_segment(seg, {"DTM"}, version="2.5.1", for_hl7types=True)

        assert "from pydantic import" in source and "ValidationInfo" in source
        assert "from hl7types.hl7._validators import _apply_dt_fallback" in source
        assert "_RE_DTM = re.compile" in source
        assert "_RE_DTM.fullmatch(v or '')" in source
        assert source.count("import re") == 1


class TestGenerateGroup:
    def test_basic_output(self) -> None:
        grp = GroupDef(
            name="GROUP.1",
            members=[MemberRef(xml_name="TEST", is_group=False, min_occurs=0, max_occurs=1)],
        )
        source = generate_group(grp, {"TEST"}, version="2.5.1")

        assert "model_config = ConfigDict(populate_by_name=True)" in source
        assert "from pydantic import BaseModel, ConfigDict, Field" in source
        assert "_TEST = TEST" in source
        compile(source, "group.py", "exec")


class TestGenerateMessage:
    def test_basic_output(self) -> None:
        msg = MessageDef(
            name="MSG",
            groups=[],
            members=[MemberRef(xml_name="TEST", is_group=False, min_occurs=0, max_occurs=1)],
        )
        source = generate_message(msg, {"TEST"}, set(), version="2.5.1")

        assert "model_config = ConfigDict(populate_by_name=True)" in source
        assert "from pydantic import BaseModel, ConfigDict, Field" in source
        assert "_TEST = TEST" in source
        compile(source, "message.py", "exec")


class TestParserHelpers:
    def test_parse_content_type_simple(self) -> None:
        from lxml import etree

        from hl7parser.parser import HL7XSDParser

        parser = HL7XSDParser.__new__(HL7XSDParser)
        xml_simple = (
            '<xs:complexType xmlns:xs="http://www.w3.org/2001/XMLSchema" name="SI.1.CONTENT">'
            '<xs:simpleContent><xs:extension base="SI"/></xs:simpleContent></xs:complexType>'
        )
        assert parser._parse_content_type(etree.fromstring(xml_simple)) == "SI"

    def test_parse_content_type_namespaced(self) -> None:
        from lxml import etree

        from hl7parser.parser import HL7XSDParser

        parser = HL7XSDParser.__new__(HL7XSDParser)
        xml_complex = (
            '<xs:complexType xmlns:xs="http://www.w3.org/2001/XMLSchema" name="XCN.1.CONTENT">'
            '<xs:complexContent><xs:extension base="hl7:XCN"/></xs:complexContent></xs:complexType>'
        )
        assert parser._parse_content_type(etree.fromstring(xml_complex)) == "XCN"
