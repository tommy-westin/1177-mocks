"""Shared XML utilities for person SOAP services."""
from lxml import etree

SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
CORE_NS = "urn:riv:strategicresourcemanagement:persons:person:5"
PERSON_ID_ROOT = "1.2.752.129.2.1.3.1"

RESP_NS = {
    "GetPersonsForProfile":
        "urn:riv:strategicresourcemanagement:persons:person:GetPersonsForProfileResponder:5",
    "GetPersonsForProfileUnrestricted":
        "urn:riv:strategicresourcemanagement:persons:person:GetPersonsForProfileUnrestrictedResponder:5",
}


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


def add_ii_type(parent: etree._Element, root: str, extension: str | None = None) -> None:
    sub(parent, CORE_NS, "root", root)
    if extension:
        sub(parent, CORE_NS, "extension", extension)


def parse_body(xml_bytes: bytes) -> etree._Element | None:
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError:
        return None
    body = root.find(f"{{{SOAP_NS}}}Body")
    if body is not None and len(body):
        return body[0]
    return None


def find_local(element: etree._Element | None, *local_names: str) -> etree._Element | None:
    el = element
    for name in local_names:
        if el is None:
            return None
        found = next((c for c in el if etree.QName(c.tag).localname == name), None)
        el = found
    return el


def local_text(element: etree._Element | None, *path: str) -> str | None:
    el = find_local(element, *path)
    return el.text if el is not None else None


def all_local(element: etree._Element | None, local_name: str) -> list[etree._Element]:
    if element is None:
        return []
    return [c for c in element if etree.QName(c.tag).localname == local_name]
