import json
import os
from lxml import etree
from .xml_utils import (
    CORE_NS, RESP_NS, soap_response, sub, add_hcf, parse_body,
    all_local, local_text
)
import logging_config  # noqa: F401

log = logging_config.request_logger

_CONFIG = os.path.join(os.path.dirname(__file__), "../../config/carelisting/facilities.json")

NS = RESP_NS["GetAvailableHealthcareFacilities"]


def _load_facilities() -> list[dict]:
    with open(_CONFIG, encoding="utf-8") as f:
        return json.load(f)


def handle(raw_xml: bytes) -> bytes:
    body = parse_body(raw_xml)

    # Optional HSA-id filter
    requested_ids = {el.text for el in all_local(body, "healthcareFacilities") if el.text}
    # Optional listingType filter
    requested_lt_codes = {local_text(el, "code") for el in all_local(body, "listingTypes")} - {None}

    log.info("GetAvailableHealthcareFacilities called – id_filter=%s lt_filter=%s",
             requested_ids or "none", requested_lt_codes or "none")

    facilities = _load_facilities()

    if requested_ids:
        facilities = [f for f in facilities if f["hsaId"] in requested_ids]
    if requested_lt_codes:
        facilities = [
            f for f in facilities
            if any(lt in requested_lt_codes for lt in f.get("supportedListingTypes", []))
        ]

    resp = etree.Element(f"{{{NS}}}GetAvailableHealthcareFacilitiesResponse", nsmap={
        "resp": NS, "core": CORE_NS
    })
    for fac in facilities:
        fac_el = sub(resp, NS, "healthcareFacilities")
        add_hcf(fac_el, fac)

    sub(resp, NS, "resultCode", "OK")
    log.info("GetAvailableHealthcareFacilities → OK, %d facilities", len(facilities))
    return soap_response(resp)
