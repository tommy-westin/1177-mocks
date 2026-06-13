"""
SearchPersonsForProfileByOrder 5.0

Parsar en SimpleQL-fråga, filtrerar persons.json och returnerar ett orderId.
Resultatet hämtas sedan via GetFilesForOrderId + REST order/get.

Stödda fältnamn i WHERE:
  countyCode, municipalityCode, name.givenname, name.surname,
  protectedPersonIndicator

Stödda operatorer:
  =        exakt matchning (skiftlägesokänslig för strängar)
  LIKE     % som wildcard (prefix, suffix, innehåller)
  !=       negation

Stödda logiska operatorer: AND (OR ej implementerat)
"""
import json
import os
import re
from lxml import etree

from .xml_utils import parse_body, local_text, soap_response, sub, CORE_NS
from .get_persons_for_profile import _build_person_record
import db as _db
import scenario
from . import file_orders
import logging_config  # noqa: F401

log = logging_config.request_logger

NS = "urn:riv:strategicresourcemanagement:persons:person:SearchPersonsForProfileByOrderResponder:5"

_FIELD_MAP = {
    "countrycode":              "countyCode",
    "countycode":               "countyCode",
    "municipalitycode":         "municipalityCode",
    "name.givenname":           "givenName",
    "name.surname":             "surname",
    "protectedpersonindicator": "protectedPersonIndicator",
}


def handle(raw_xml: bytes) -> bytes:
    body    = parse_body(raw_xml)
    query   = local_text(body, "query") or ""
    profile = local_text(body, "profile") or "P2"

    log.info("SearchPersonsForProfileByOrder – profile=%s query=%r", profile, query)

    predicates = _parse_where(query)
    persons    = _db.get_all_persons(scenario.get())
    matched    = [p for p in persons if _matches(p, predicates)]

    log.info("SearchPersonsForProfileByOrder → %d träffar", len(matched))

    xml_bytes = _build_xml(matched, profile)
    order_id, _ = file_orders.create(_zip_xml(xml_bytes))

    resp = etree.Element(f"{{{NS}}}SearchPersonsForProfileByOrderResponse",
                         nsmap={"resp": NS})
    sub(resp, NS, "orderId", order_id)
    return soap_response(resp)


# ---------------------------------------------------------------------------
# SimpleQL parser
# ---------------------------------------------------------------------------

_COND_RE = re.compile(
    r"([\w.]+)\s+(LIKE|!=|=)\s+'([^']*)'",
    re.IGNORECASE,
)


def _parse_where(query: str) -> list[tuple[str, str, str]]:
    """Return list of (field, op, value) from WHERE clause."""
    where_match = re.search(r"WHERE\s+(.+?)(?:;|\s*$)", query, re.IGNORECASE | re.DOTALL)
    if not where_match:
        return []
    clause = where_match.group(1)
    return [
        (m.group(1).lower(), m.group(2).upper(), m.group(3))
        for m in _COND_RE.finditer(clause)
    ]


def _matches(person: dict, predicates: list[tuple]) -> bool:
    for field_raw, op, value in predicates:
        json_key = _FIELD_MAP.get(field_raw, field_raw)
        actual   = str(person.get(json_key, ""))
        if op == "=":
            if actual.lower() != value.lower():
                return False
        elif op == "!=":
            if actual.lower() == value.lower():
                return False
        elif op == "LIKE":
            pattern = _like_to_regex(value)
            if not re.fullmatch(pattern, actual, re.IGNORECASE):
                return False
    return True


def _like_to_regex(like: str) -> str:
    parts = like.split("%")
    return ".*".join(re.escape(p) for p in parts)


# ---------------------------------------------------------------------------
# XML + ZIP helpers
# ---------------------------------------------------------------------------

def _build_xml(persons: list[dict], profile: str) -> bytes:
    RESP_NS = "urn:riv:strategicresourcemanagement:persons:person:GetPersonsForProfileResponder:5"
    PERSON_ID_ROOT = "1.2.752.129.2.1.3.1"

    resp_el = etree.Element(f"{{{RESP_NS}}}GetPersonsForProfileResponse",
                            nsmap={"resp": RESP_NS, "core": CORE_NS})

    for person in persons:
        pid    = person["personId"]
        rec_el = etree.SubElement(resp_el, f"{{{RESP_NS}}}requestedPersonRecord")
        req_id = etree.SubElement(rec_el, f"{{{CORE_NS}}}requestedPersonalIdentity")
        etree.SubElement(req_id, f"{{{CORE_NS}}}root").text      = PERSON_ID_ROOT
        etree.SubElement(req_id, f"{{{CORE_NS}}}extension").text = pid
        pr_el = etree.SubElement(rec_el, f"{{{CORE_NS}}}personRecord")
        _build_person_record(pr_el, person, profile)

    return etree.tostring(resp_el, xml_declaration=True,
                          encoding="UTF-8", pretty_print=True)


def _zip_xml(xml_bytes: bytes) -> bytes:
    import io, zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("result.xml", xml_bytes)
    return buf.getvalue()
