"""Shared XML building and parsing utilities for carelisting SOAP services."""
from lxml import etree

SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
CORE_NS = "urn:riv:supportprocess:logistics:carelisting:2"
EXT_NS = "urn:riv:supportprocess:logistics:carelisting:2.1"

LISTING_TYPE_CODESYSTEM = "1.2.752.129.2.2.4.1"
PERSON_ID_ROOT = "1.2.752.129.2.1.3.1"

RESP_NS = {
    "GetListingTypes":                    "urn:riv:supportprocess:logistics:carelisting:GetListingTypesResponder:2",
    "GetAvailableHealthcareFacilities":   "urn:riv:supportprocess:logistics:carelisting:GetAvailableHealthcareFacilitiesResponder:2",
    "GetAvailableHealthcarePersonnel":    "urn:riv:supportprocess:logistics:carelisting:GetAvailableHealthcarePersonnelResponder:2",
    "GetListing":                         "urn:riv:supportprocess:logistics:carelisting:GetListingResponder:2",
    "CreateListing":                      "urn:riv:supportprocess:logistics:carelisting:CreateListingResponder:2",
    "UpdateListing":                      "urn:riv:supportprocess:logistics:carelisting:UpdateListingResponder:2",
}


# ---------------------------------------------------------------------------
# Response building
# ---------------------------------------------------------------------------

def soap_response(body_element: etree._Element) -> bytes:
    env = etree.Element(f"{{{SOAP_NS}}}Envelope", nsmap={"soapenv": SOAP_NS})
    body = etree.SubElement(env, f"{{{SOAP_NS}}}Body")
    body.append(body_element)
    return etree.tostring(env, xml_declaration=True, encoding="UTF-8", pretty_print=True)


def sub(parent: etree._Element, ns: str, tag: str, text: str | None = None) -> etree._Element:
    el = etree.SubElement(parent, f"{{{ns}}}{tag}")
    if text is not None:
        el.text = text
    return el


def add_cv_type(parent: etree._Element, code: str, code_system: str, display_name: str | None = None) -> None:
    """Append CVType child elements (in CORE_NS) to parent."""
    sub(parent, CORE_NS, "code", code)
    sub(parent, CORE_NS, "codeSystem", code_system)
    if display_name:
        sub(parent, CORE_NS, "displayName", display_name)


def add_hcf(parent: etree._Element, facility: dict) -> None:
    """Append HealthcareFacilityType children (in CORE_NS) to parent."""
    sub(parent, CORE_NS, "id", facility["hsaId"])
    sub(parent, CORE_NS, "name", facility["name"])
    sub(parent, CORE_NS, "hasQueue", "true" if facility.get("hasQueue") else "false")
    for lt_code in facility.get("supportedListingTypes", []):
        lt_el = sub(parent, CORE_NS, "supportedListingTypes")
        add_cv_type(lt_el, lt_code, facility.get("codeSystem", LISTING_TYPE_CODESYSTEM))
    sub(parent, CORE_NS, "supportsHealthcarePersonnel",
        "true" if facility.get("supportsHealthcarePersonnel") else "false")


def add_hcp(parent: etree._Element, personnel: dict) -> None:
    """Append HealthcarePersonnelType children (in CORE_NS) to parent."""
    sub(parent, CORE_NS, "id", personnel["hsaId"])
    sub(parent, CORE_NS, "name", personnel["name"])
    if personnel.get("title"):
        sub(parent, CORE_NS, "title", personnel["title"])


# ---------------------------------------------------------------------------
# Request parsing
# ---------------------------------------------------------------------------

def parse_body(xml_bytes: bytes) -> etree._Element | None:
    """Return the first child element of the SOAP Body."""
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError:
        return None
    body = root.find(f"{{{SOAP_NS}}}Body")
    if body is not None and len(body):
        return body[0]
    return None


def find_local(element: etree._Element | None, *local_names: str) -> etree._Element | None:
    """Navigate a path using only local names (namespace-agnostic)."""
    el = element
    for name in local_names:
        if el is None:
            return None
        found = None
        for child in el:
            if etree.QName(child.tag).localname == name:
                found = child
                break
        el = found
    return el


def local_text(element: etree._Element | None, *path: str) -> str | None:
    """Return text of a nested element navigated by local names."""
    el = find_local(element, *path)
    return el.text if el is not None else None


def all_local(element: etree._Element | None, local_name: str) -> list[etree._Element]:
    """Return all direct children with the given local name."""
    if element is None:
        return []
    return [c for c in element if etree.QName(c.tag).localname == local_name]
