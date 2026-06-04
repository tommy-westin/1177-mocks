from lxml import etree
from .xml_utils import CORE_NS, RESP_NS, soap_response, sub, add_hcf, parse_body, all_local, local_text
import logging_config  # noqa: F401
import db

log = logging_config.request_logger
NS  = RESP_NS["GetAvailableHealthcareFacilities"]


def handle(raw_xml: bytes) -> bytes:
    body = parse_body(raw_xml)

    requested_ids     = {el.text for el in all_local(body, "healthcareFacilities") if el.text}
    requested_lt_codes = {local_text(el, "code") for el in all_local(body, "listingTypes")} - {None}

    log.info("GetAvailableHealthcareFacilities – id_filter=%s lt_filter=%s",
             requested_ids or "none", requested_lt_codes or "none")

    facilities = db.get_all_facilities()

    if requested_ids:
        facilities = [f for f in facilities if f["hsaId"] in requested_ids]
    if requested_lt_codes:
        facilities = [f for f in facilities
                      if any(lt in requested_lt_codes for lt in f.get("supportedListingTypes", []))]

    resp = etree.Element(f"{{{NS}}}GetAvailableHealthcareFacilitiesResponse",
                         nsmap={"resp": NS, "core": CORE_NS})
    for fac in facilities:
        fac_el = sub(resp, NS, "healthcareFacilities")
        add_hcf(fac_el, fac)

    sub(resp, NS, "resultCode", "OK")
    log.info("GetAvailableHealthcareFacilities → OK, %d facilities", len(facilities))
    return soap_response(resp)
