from lxml import etree
from .xml_utils import (
    CORE_NS, RESP_NS, soap_response, sub, add_cv_type, add_hcf, add_hcp,
    parse_body, local_text, LISTING_TYPE_CODESYSTEM
)
import logging_config  # noqa: F401
import state
import scenario
import db

log = logging_config.request_logger
NS  = RESP_NS["GetListing"]


def handle(raw_xml: bytes) -> bytes:
    body      = parse_body(raw_xml)
    person_id = local_text(body, "personId", "extension")
    log.info("GetListing – person=%s", person_id)

    # In-memory state from CreateListing takes priority
    created = state.get_created_listings(person_id) if person_id else None
    if created is not None:
        patient_listings = created
    else:
        patient = db.get_patient(person_id, scenario.get()) if person_id else None
        if patient is None or patient.get("scenario") == "not_listed":
            return _ok_empty()
        patient_listings = _build_listing_list(patient)

    resp = etree.Element(f"{{{NS}}}GetListingResponse", nsmap={"resp": NS, "core": CORE_NS})

    for listing in patient_listings:
        fac = db.get_facility(listing.get("facilityHsaId", ""))
        if fac is None:
            continue

        listing_el = sub(resp, NS, "listings")
        lt_el      = sub(listing_el, CORE_NS, "listingType")
        add_cv_type(lt_el, listing.get("listingTypeCode", "PRIMARY_CARE"), LISTING_TYPE_CODESYSTEM)

        hcf_el = sub(listing_el, CORE_NS, "healthcareFacility")
        add_hcf(hcf_el, fac)

        if listing.get("personnelHsaId"):
            pers = db.get_personnel_member(listing["personnelHsaId"])
            if pers:
                hcp_el = sub(listing_el, CORE_NS, "healthcarePersonnel")
                add_hcp(hcp_el, pers)

        sub(listing_el, CORE_NS, "isInQueue",
            "true" if listing.get("isInQueue") else "false")

    sub(resp, NS, "resultCode", "OK")
    log.info("GetListing → OK, %d listings for person=%s", len(patient_listings), person_id)
    return soap_response(resp)


def _build_listing_list(patient: dict) -> list[dict]:
    result = []
    for lt in patient.get("listingTypes", []):
        entry = {
            "facilityHsaId":  patient.get("facilityHsaId"),
            "listingTypeCode": lt.get("code", "PRIMARY_CARE"),
            "isInQueue":       patient.get("isInQueue", False),
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
