from __future__ import annotations

import re
from pathlib import Path

from lxml import etree

from .ir import (
    ComponentDef,
    DataTypeDef,
    FieldRef,
    GroupDef,
    MemberRef,
    MessageDef,
    SegmentDef,
    VersionIR,
)

XSD_NS = "http://www.w3.org/2001/XMLSchema"


def _tag(local: str) -> str:
    return f"{{{XSD_NS}}}{local}"


class HL7XSDParser:
    """ """

    def __init__(self, path: Path):
        """
        TODO:
        """
        self.path: str = path

    def _parse_occurs(self, elem) -> tuple[int, int | None]:
        min_o = int(elem.get("minOccurs", "1"))
        max_raw = elem.get("maxOccurs", "1")
        max_o = None if max_raw == "unbounded" else int(max_raw)
        return min_o, max_o

    def _merge_member(self, existing: MemberRef, new_min: int, new_max: int | None) -> MemberRef:
        min_o = min(existing.min_occurs, new_min)
        if existing.max_occurs is None or new_max is None:
            max_o = None
        else:
            max_o = max(existing.max_occurs, new_max)
        return MemberRef(existing.xml_name, existing.is_group, min_o, max_o)

    def _parse_attribute_groups(self, root) -> dict[str, dict[str, str]]:
        """Parse X.N.ATTRIBUTES attributeGroups to {base_name: {attr_name: fixed_value}}."""
        result: dict[str, dict[str, str]] = {}
        for elem in root:
            if elem.tag != _tag("attributeGroup"):
                continue
            name = elem.get("name", "")
            if not name.endswith(".ATTRIBUTES"):
                continue
            base = name[: -len(".ATTRIBUTES")]
            attrs: dict[str, str] = {}
            for child in elem:
                if child.tag == _tag("attribute"):
                    attr_name = child.get("name", "")
                    fixed = child.get("fixed", "")
                    if attr_name and fixed:
                        attrs[attr_name] = fixed
            result[base] = attrs
        return result

    def _parse_content_type(self, elem) -> tuple[str | None, bool]:
        """Return (base_type_name, is_primitive) from a X.N.CONTENT complexType element."""
        for child in elem:
            if child.tag == _tag("simpleContent"):
                for sc in child:
                    if sc.tag == _tag("extension"):
                        return sc.get("base"), True
            elif child.tag == _tag("complexContent"):
                for cc in child:
                    if cc.tag == _tag("extension"):
                        base = cc.get("base")
                        # Strip namespace prefix if present (e.g. "hl7:XCN" to "XCN")
                        if base and ":" in base:
                            base = base.split(":")[-1]
                        return base, False
        return None, False

    def _parse_datatypes(
        self, path: Path
    ) -> tuple[set[str], dict[str, tuple[str, bool]], list[DataTypeDef]]:
        """Parse datatypes.xsd.

        Returns:
            primitives: set of primitive simpleType names
            component_info: base_name to (base_type, is_primitive) for X.N sub-component types
            composite_types: list of DataTypeDef
        """
        tree = etree.parse(str(path))
        root = tree.getroot()

        primitives: set[str] = set()
        attribute_groups = self._parse_attribute_groups(root)
        content_type_info: dict[
            str, tuple[str | None, bool]
        ] = {}  # "AD.1.CONTENT" to (base, is_prim)
        element_type_map: dict[str, str] = {}  # "AD.1" to "AD.1.CONTENT"

        for elem in root:
            name = elem.get("name", "")
            if elem.tag == _tag("simpleType") and name:
                primitives.add(name)
            elif elem.tag == _tag("complexType") and name:
                if name.endswith(".CONTENT"):
                    content_type_info[name] = self._parse_content_type(elem)
            elif elem.tag == _tag("element") and name:
                t = elem.get("type")
                if t:
                    element_type_map[name] = t

        composite_types: list[DataTypeDef] = []

        for elem in root:
            name = elem.get("name", "")
            if elem.tag != _tag("complexType") or not name:
                continue
            if name.endswith(".CONTENT") or name == "escapeType":
                continue
            # Top-level composite type (AD, XCN, CE, …)
            components: list[ComponentDef] = []
            for child in elem:
                if child.tag != _tag("sequence"):
                    continue
                for seq_child in child:
                    if seq_child.tag != _tag("element"):
                        continue
                    ref = seq_child.get("ref")
                    if not ref:
                        continue
                    min_o, max_o = self._parse_occurs(seq_child)
                    content_name = element_type_map.get(ref)
                    # Resolve type from attributeGroup (most reliable) then fallback to CONTENT
                    attrs = attribute_groups.get(ref, {})
                    long_name = attrs.get("LongName") or ref
                    type_from_attrs = attrs.get("Type")

                    if type_from_attrs:
                        base_type = type_from_attrs
                        is_prim = type_from_attrs in primitives
                    elif content_name and content_name in content_type_info:
                        base_raw, is_prim = content_type_info[content_name]
                        base_type = base_raw or "ST"
                        is_prim = is_prim or (base_type in primitives)
                    else:
                        base_type = "ST"
                        is_prim = True

                    components.append(
                        ComponentDef(
                            xml_name=ref,
                            long_name=long_name,
                            base_type=base_type,
                            is_primitive=is_prim,
                            min_occurs=min_o,
                            max_occurs=max_o,
                        )
                    )
            composite_types.append(DataTypeDef(name=name, components=components))

        return primitives, {k: v for k, (v, ip) in content_type_info.items()}, composite_types

    def _parse_fields(self, path: Path, primitives: set[str]) -> dict[str, FieldRef]:
        """Parse fields.xsd {xml_name: FieldRef}."""
        tree = etree.parse(str(path))
        root = tree.getroot()

        attribute_groups = self._parse_attribute_groups(root)
        content_type_info: dict[str, tuple[str | None, bool]] = {}
        element_type_map: dict[str, str] = {}

        for elem in root:
            name = elem.get("name", "")
            if elem.tag == _tag("complexType") and name and name.endswith(".CONTENT"):
                content_type_info[name] = self._parse_content_type(elem)
            elif elem.tag == _tag("element") and name:
                t = elem.get("type")
                if t:
                    element_type_map[name] = t

        field_map: dict[str, FieldRef] = {}
        for xml_name, content_name in element_type_map.items():
            if content_name not in content_type_info:
                continue
            attrs = attribute_groups.get(xml_name, {})
            long_name = attrs.get("LongName") or xml_name
            type_from_attrs = attrs.get("Type")
            item_num = attrs.get("Item") or None
            table = attrs.get("Table") or None

            if type_from_attrs:
                field_type = type_from_attrs
                is_prim = field_type in primitives
            else:
                base_raw, is_prim = content_type_info[content_name]
                field_type = base_raw or "ST"
                is_prim = is_prim or (field_type in primitives)

            field_map[xml_name] = FieldRef(
                xml_name=xml_name,
                field_type=field_type,
                long_name=long_name,
                is_primitive=is_prim,
                item_num=item_num,
                table=table,
            )

        return field_map

    def _parse_segments(self, path: Path, field_map: dict[str, FieldRef]) -> list[SegmentDef]:
        """Parse segments.xsd to list[SegmentDef]."""
        tree = etree.parse(str(path))
        root = tree.getroot()

        element_type_map: dict[str, str] = {}
        for elem in root:
            name = elem.get("name", "")
            if elem.tag == _tag("element") and name:
                t = elem.get("type")
                if t:
                    element_type_map[name] = t

        segments: list[SegmentDef] = []

        for elem in root:
            name = elem.get("name", "")
            if elem.tag != _tag("complexType") or not name:
                continue
            if not name.endswith(".CONTENT"):
                continue
            seg_name = name[: -len(".CONTENT")]
            # Only segments (3-letter codes): ABS, ACC, etc.
            if "." in seg_name:
                continue

            fields: list[FieldRef] = []
            seen_names: dict[str, int] = {}  # deduplicate repeated field refs

            for child in elem:
                if child.tag != _tag("sequence"):
                    continue
                for seq_child in child:
                    if seq_child.tag != _tag("element"):
                        continue
                    ref = seq_child.get("ref")
                    if not ref:
                        continue
                    min_o, max_o = self._parse_occurs(seq_child)

                    if ref in field_map:
                        base = field_map[ref]
                        fr = FieldRef(
                            xml_name=base.xml_name,
                            field_type=base.field_type,
                            long_name=base.long_name,
                            is_primitive=base.is_primitive,
                            item_num=base.item_num,
                            table=base.table,
                            min_occurs=min_o,
                            max_occurs=max_o,
                        )
                    else:
                        # Unknown field — treat as string
                        fr = FieldRef(
                            xml_name=ref,
                            field_type="ST",
                            long_name=ref,
                            is_primitive=True,
                            min_occurs=min_o,
                            max_occurs=max_o,
                        )

                    # Deduplicate repeated refs (same field appearing twice in sequence)
                    key = fr.xml_name
                    if key in seen_names:
                        idx = seen_names[key]
                        existing = fields[idx]
                        merged_min = min(existing.min_occurs, fr.min_occurs)
                        if existing.max_occurs is None or fr.max_occurs is None:
                            merged_max = None
                        else:
                            merged_max = max(existing.max_occurs, fr.max_occurs)
                        fields[idx] = FieldRef(
                            xml_name=existing.xml_name,
                            field_type=existing.field_type,
                            long_name=existing.long_name,
                            is_primitive=existing.is_primitive,
                            item_num=existing.item_num,
                            table=existing.table,
                            min_occurs=merged_min,
                            max_occurs=merged_max,
                        )
                    else:
                        seen_names[key] = len(fields)
                        fields.append(fr)

            segments.append(SegmentDef(name=seg_name, fields=fields))

        return segments

    def _parse_message_xsd(
        self, path: Path, known_segments: set[str]
    ) -> tuple[list[GroupDef], MessageDef | None]:
        """Parse a single message XSD (groups, message)."""
        tree = etree.parse(str(path))
        root = tree.getroot()

        groups: list[GroupDef] = []
        message: MessageDef | None = None

        def _build_members(elem) -> list[MemberRef]:
            members: list[MemberRef] = []
            seen: dict[str, int] = {}
            for child in elem:
                if child.tag != _tag("sequence"):
                    continue
                for seq_child in child:
                    if seq_child.tag != _tag("element"):
                        continue
                    ref = seq_child.get("ref")
                    if not ref:
                        continue
                    min_o, max_o = self._parse_occurs(seq_child)
                    is_group = "." in ref  # group refs contain a dot (e.g. ADT_A01.PROCEDURE)

                    if ref in seen:
                        idx = seen[ref]
                        members[idx] = self._merge_member(members[idx], min_o, max_o)
                    else:
                        seen[ref] = len(members)
                        members.append(
                            MemberRef(
                                xml_name=ref, is_group=is_group, min_occurs=min_o, max_occurs=max_o
                            )
                        )
            return members

        for elem in root:
            name = elem.get("name", "")
            if elem.tag != _tag("complexType") or not name:
                continue
            if not name.endswith(".CONTENT"):
                continue

            base = name[: -len(".CONTENT")]

            parts = base.split(".")
            if len(parts) == 1:
                # Message definition (e.g. "ADT_A01")
                message = MessageDef(name=base, groups=[], members=_build_members(elem))
            elif len(parts) >= 2:
                # Group definition (e.g. "ADT_A01.PROCEDURE")
                groups.append(GroupDef(name=base, members=_build_members(elem)))

        if message:
            message.groups = groups

        return groups, message

    def parse_version(self) -> VersionIR:
        version: str = self.path.name

        datatypes_path = self.path / "datatypes.xsd"
        fields_path = self.path / "fields.xsd"
        segments_path = self.path / "segments.xsd"

        primitives, _, composite_types = self._parse_datatypes(datatypes_path)
        field_map = self._parse_fields(fields_path, primitives)
        segments = self._parse_segments(segments_path, field_map)

        known_segments = {s.name for s in segments}

        all_groups: list[GroupDef] = []
        all_messages: list[MessageDef] = []

        for xsd_file in sorted(self.path.glob("*.xsd")):
            stem = xsd_file.stem
            if stem in ("datatypes", "fields", "segments", "messages", "batch"):
                continue
            # Message XSDs: uppercase stems like ADT_A01, ACK, etc - this _should_ work.
            if not re.match(r"^[A-Z]", stem):
                continue
            groups, msg = self._parse_message_xsd(xsd_file, known_segments)
            all_groups.extend(groups)
            if msg:
                all_messages.append(msg)

        return VersionIR(
            version=version,
            primitives=primitives,
            datatypes=composite_types,
            segments=segments,
            groups=all_groups,
            messages=all_messages,
        )
