import json
import os
from lxml import etree
from .xml_utils import (
    CORE_NS, RESP_NS, soap_response, sub, add_cv_type, add_hcf, add_hcp,
    parse_body, local_text, LISTING_TYPE_CODESYSTEM
)
import logging_config  # noqa: F401
import state
import scenario

log = logging_config.request_logger

_PATIENTS_CFG = os.path.join(os.path.dirname(__file__), "../../config/carelisting/patients.json")
_FACILITIES_CFG = os.path.join(os.path.dirname(__file__), "../../config/carelisting/facilities.json")
_PERSONNEL_CFG = os.path.join(os.path.dirname(__file__), "../../config/carelisting/personnel.json")

NS = RESP_NS["GetListing"]


def _load(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _fac_by_id(facilities: list[dict], hsa_id: str) -> dict | None:
    return next((f for f in facilities if f["hsaId"] == hsa_id), None)


def _person_by_id(personnel: list[dict], hsa_id: str) -> dict | None:
    return next((p for p in personnel if p["hsaId"] == hsa_id), None)


def handle(raw_xml: bytes) -> bytes:
    body = parse_body(raw_xml)
    person_id = local_text(body, "personId", "extension")
    log.info("GetListing – person=%s", person_id)

    facilities = _load(_FACILITIES_CFG)
    personnel = _load(_PERSONNEL_CFG)

    # In-memory state from CreateListing takes priority
    created = state.get_created_listings(person_id) if person_id else None
    if created is not None:
        patient_listings = created
    else:
        patients = _load(scenario.resolve(_PATIENTS_CFG))
        patient = next((p for p in patients if p.get("personId") == person_id), None)
        if patient is None or patient.get("scenario") == "not_listed":
            return _ok_empty()
        patient_listings = _build_patient_listing_list(patient)

    resp = etree.Element(f"{{{NS}}}GetListingResponse", nsmap={
        "resp": NS, "core": CORE_NS
    })

    for listing in patient_listings:
        fac = _fac_by_id(facilities, listing.get("facilityHsaId", ""))
        if fac is None:
            continue

        listing_el = sub(resp, NS, "listings")

        lt_el = sub(listing_el, CORE_NS, "listingType")
        add_cv_type(lt_el, listing.get("listingTypeCode", "PRIMARY_CARE"),
                    LISTING_TYPE_CODESYSTEM)

        hcf_el = sub(listing_el, CORE_NS, "healthcareFacility")
        add_hcf(hcf_el, fac)

        if listing.get("personnelHsaId"):
            pers = _person_by_id(personnel, listing["personnelHsaId"])
            if pers:
                hcp_el = sub(listing_el, CORE_NS, "healthcarePersonnel")
                add_hcp(hcp_el, pers)

        sub(listing_el, CORE_NS, "isInQueue",
            "true" if listing.get("isInQueue") else "false")

    sub(resp, NS, "resultCode", "OK")
    log.info("GetListing → OK, %d listings for person=%s", len(patient_listings), person_id)
    return soap_response(resp)


def _build_patient_listing_list(patient: dict) -> list[dict]:
    """Convert patients.json row into a flat list of listing dicts."""
    result = []
    for lt in patient.get("listingTypes", []):
        entry = {
            "facilityHsaId": patient.get("facilityHsaId"),
            "listingTypeCode": lt.get("code", "PRIMARY_CARE"),
            "isInQueue": patient.get("isInQueue", False),
        }
        if lt.get("doctorHsaId"):
            entry["personnelHsaId"] = lt["doctorHsaId"]
        elif lt.get("careContactHsaId"):
            entry["personnelHsaId"] = lt["careContactHsaId"]
        result.append(entry)
    return result


def _ok_empty() -> bytes:
    resp = etree.Element(f"{{{NS}}}GetListingResponse", nsmap={"resp": NS, "core": CORE_NS})
    sub(resp, NS, "resultCode", "OK")
    return soap_response(resp)
