import json
import os
from lxml import etree
from .xml_utils import (
    RESP_NS, soap_response, sub, parse_body, local_text, all_local
)
import logging_config  # noqa: F401
import state

log = logging_config.request_logger

_FACILITIES_CFG = os.path.join(os.path.dirname(__file__), "../../config/carelisting/facilities.json")
_PERSONNEL_CFG = os.path.join(os.path.dirname(__file__), "../../config/carelisting/personnel.json")

NS = RESP_NS["CreateListing"]


def _load(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def handle(raw_xml: bytes) -> bytes:
    body = parse_body(raw_xml)

    person_id = local_text(body, "personId", "extension")
    facility_id = local_text(body, "healthcareFacilityHSAId")
    listing_type_code = local_text(body, "listingType", "code")
    personnel_id = local_text(body, "healthcarePersonnel")
    add_to_queue_text = local_text(body, "addToQueue")
    add_to_queue = add_to_queue_text == "true" if add_to_queue_text is not None else False

    log.info(
        "CreateListing – person=%s facility=%s listingType=%s personnel=%s addToQueue=%s",
        person_id, facility_id, listing_type_code, personnel_id, add_to_queue
    )
    # Log full payload for verification
    try:
        log.info("CreateListing payload:\n%s",
                 etree.tostring(body, pretty_print=True).decode() if body is not None else "<none>")
    except Exception:
        pass

    facilities = _load(_FACILITIES_CFG)
    personnel = _load(_PERSONNEL_CFG)

    fac = next((f for f in facilities if f["hsaId"] == facility_id), None)
    if fac is None:
        return _resp("ERROR", f"Unknown healthcareFacilityHSAId: {facility_id}")

    if personnel_id:
        pers = next((p for p in personnel if p["hsaId"] == personnel_id), None)
        if pers is None:
            return _resp("ERROR", f"Unknown healthcarePersonnel: {personnel_id}")
        if pers.get("facilityHsaId") != facility_id:
            return _resp("ERROR",
                         f"Personnel {personnel_id} does not belong to facility {facility_id}")

    new_listing = {
        "facilityHsaId": facility_id,
        "listingTypeCode": listing_type_code or "PRIMARY_CARE",
        "isInQueue": add_to_queue,
        "personnelHsaId": personnel_id,
    }

    existing = state.get_created_listings(person_id) or []
    # Replace listing of same type, keep others
    updated = [l for l in existing if l.get("listingTypeCode") != new_listing["listingTypeCode"]]
    updated.append(new_listing)
    state.store_listing(person_id, updated)

    log.info("CreateListing → OK for person=%s", person_id)
    return _resp("OK")


def _resp(result_code: str, result_text: str | None = None) -> bytes:
    resp = etree.Element(f"{{{NS}}}CreateListingResponse", nsmap={"resp": NS})
    sub(resp, NS, "resultCode", result_code)
    if result_text:
        sub(resp, NS, "resultText", result_text)
    return soap_response(resp)
