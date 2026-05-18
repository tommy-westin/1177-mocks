"""
GetPersonsForProfile 5.0 — and shared logic for Unrestricted variant.

Primary use-case for VVH: given a list of personnummer, return folkbokföring
(countyCode) and address so VVH can detect patients who have moved out of county.

Profile semantics (simplified):
  P1 → identity + name
  P2 → P1 + address + populationRegistrationLocality   ← what VVH needs
  P3+ → P2 (mock returns same data regardless)

Protected persons (protectedPersonIndicator=true) get only skeleton identity data.
Unknown persons get a requestedPersonRecord with no personRecord child.
"""
import json
import os
from lxml import etree
from .xml_utils import (
    CORE_NS, RESP_NS, soap_response, sub, add_ii_type,
    parse_body, local_text, all_local, PERSON_ID_ROOT,
)
import logging_config  # noqa: F401

log = logging_config.request_logger

_CONFIG = os.path.join(os.path.dirname(__file__), "../../config/person/persons.json")


def _load_persons() -> list[dict]:
    with open(_CONFIG, encoding="utf-8") as f:
        return json.load(f)


def _person_by_id(persons: list[dict], pid: str) -> dict | None:
    return next((p for p in persons if p.get("personId") == pid), None)


def handle(raw_xml: bytes, operation: str = "GetPersonsForProfile") -> bytes:
    body = parse_body(raw_xml)
    ns = RESP_NS[operation]

    # Collect all requested personIds
    requested_ids: list[str] = []
    for pid_el in all_local(body, "personId"):
        ext = local_text(pid_el, "extension")
        if ext:
            requested_ids.append(ext)

    profile = local_text(body, "profile") or "P2"
    log.info("%s – profile=%s persons=%s", operation, profile, requested_ids)

    persons = _load_persons()

    resp = etree.Element(f"{{{ns}}}{operation}Response", nsmap={
        "resp": ns, "core": CORE_NS
    })

    for pid in requested_ids:
        person = _person_by_id(persons, pid)
        rec_el = sub(resp, ns, "requestedPersonRecord")

        # Always echo back the requested identity
        req_id_el = sub(rec_el, CORE_NS, "requestedPersonalIdentity")
        add_ii_type(req_id_el, PERSON_ID_ROOT, pid)

        if person is None or person.get("scenario") == "not_found":
            log.info("  %s → not found", pid)
            continue

        pr_el = sub(rec_el, CORE_NS, "personRecord")
        _build_person_record(pr_el, person, profile)
        log.info("  %s → %s", pid, person.get("scenario"))

    return soap_response(resp)


def _build_person_record(pr: etree._Element, person: dict, profile: str) -> None:
    """Populate a PersonRecordType element from a persons.json entry."""
    pid = person["personId"]
    is_protected = person.get("protectedPersonIndicator", False)

    # Identity (always)
    pid_el = sub(pr, CORE_NS, "personalIdentity")
    add_ii_type(pid_el, PERSON_ID_ROOT, pid)
    sub(pr, CORE_NS, "protectedPersonIndicator",
        "true" if is_protected else "false")
    sub(pr, CORE_NS, "testIndicator",
        "true" if person.get("testIndicator", True) else "false")
    sub(pr, CORE_NS, "primaryIdentity", "true")

    # Name — omit for protected persons
    if not is_protected and (person.get("givenName") or person.get("surname")):
        name_el = sub(pr, CORE_NS, "name")
        if person.get("givenName"):
            sub(name_el, CORE_NS, "givenName", person["givenName"])
        if person.get("surname"):
            sub(name_el, CORE_NS, "surname", person["surname"])

    # P2+ → address + folkbokföring
    if profile >= "P2" and not is_protected:
        _build_population_registration(pr, person)
        _build_address(pr, person)

    # Deregistration (avregistrering) — always if present
    if person.get("deregistrationReasonCode") and not is_protected:
        dereg_el = sub(pr, CORE_NS, "deregistration")
        sub(dereg_el, CORE_NS, "deregistrationReasonCode",
            person["deregistrationReasonCode"])
        if person.get("deregistrationDate"):
            date_el = sub(dereg_el, CORE_NS, "deregistrationDate")
            sub(date_el, CORE_NS, "format", "YYYY-MM-DD")
            sub(date_el, CORE_NS, "value", person["deregistrationDate"])


def _build_population_registration(pr: etree._Element, person: dict) -> None:
    if not person.get("countyCode"):
        return
    loc_el = sub(pr, CORE_NS, "populationRegistrationLocality")
    sub(loc_el, CORE_NS, "countyCode", person["countyCode"])
    if person.get("municipalityCode"):
        sub(loc_el, CORE_NS, "municipalityCode", person["municipalityCode"])


def _build_address(pr: etree._Element, person: dict) -> None:
    if not any(person.get(k) for k in ("postalAddress1", "postalCode", "city")):
        return
    addr_info_el = sub(pr, CORE_NS, "addressInformation")
    res_addr_el = sub(addr_info_el, CORE_NS, "residentialAddress")
    if person.get("postalAddress1"):
        sub(res_addr_el, CORE_NS, "postalAddress1", person["postalAddress1"])
    if person.get("postalCode") is not None:
        sub(res_addr_el, CORE_NS, "postalCode", str(person["postalCode"]))
    if person.get("city"):
        sub(res_addr_el, CORE_NS, "city", person["city"])
