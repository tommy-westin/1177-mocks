from lxml import etree
from .xml_utils import CORE_NS, RESP_NS, soap_response, sub, add_hcp, parse_body, all_local, local_text
import logging_config  # noqa: F401
import db

log = logging_config.request_logger
NS  = RESP_NS["GetAvailableHealthcarePersonnel"]

DOCTOR_CODES     = {"DOCTOR"}
NON_DOCTOR_CODES = {"NURSE", "OTHER"}


def handle(raw_xml: bytes) -> bytes:
    body        = parse_body(raw_xml)
    person_id   = local_text(body, "personId", "extension")
    facility_id = local_text(body, "healthcareFacilityHSAId")
    lt_codes    = {local_text(el, "code") for el in all_local(body, "listingTypes")} - {None}

    log.info("GetAvailableHealthcarePersonnel – person=%s facility=%s lt=%s",
             person_id, facility_id, lt_codes or "none")

    if not facility_id:
        return _error("healthcareFacilityHSAId is required")

    personnel = [p for p in db.get_all_personnel() if p["facilityHsaId"] == facility_id]

    if lt_codes:
        if "FAST_DOCTOR_CONTACT" in lt_codes and "FAST_CARE_CONTACT" not in lt_codes:
            personnel = [p for p in personnel if p.get("professionCode") in DOCTOR_CODES]
        elif "FAST_CARE_CONTACT" in lt_codes and "FAST_DOCTOR_CONTACT" not in lt_codes:
            personnel = [p for p in personnel if p.get("professionCode") in NON_DOCTOR_CODES]

    resp = etree.Element(f"{{{NS}}}GetAvailableHealthcarePersonnelResponse",
                         nsmap={"resp": NS, "core": CORE_NS})
    for p in personnel:
        p_el = sub(resp, NS, "healthcarePersonnel")
        add_hcp(p_el, p)

    sub(resp, NS, "resultCode", "OK")
    log.info("GetAvailableHealthcarePersonnel → OK, %d personnel", len(personnel))
    return soap_response(resp)


def _error(message: str) -> bytes:
    resp = etree.Element(f"{{{NS}}}GetAvailableHealthcarePersonnelResponse")
    sub(resp, NS, "resultCode", "ERROR")
    sub(resp, NS, "resultText", message)
    return soap_response(resp)
