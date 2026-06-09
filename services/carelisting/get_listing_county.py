from lxml import etree
from .xml_utils import CORE_NS, soap_response, sub, parse_body, local_text
import logging_config  # noqa: F401
import scenario
import db

log = logging_config.request_logger

NS         = "urn:riv:supportprocess:logistics:carelisting:GetListingCountyResponder:2"
HSA_ID_OID = "1.2.752.129.2.1.4.1"


def handle(raw_xml: bytes) -> bytes:
    body      = parse_body(raw_xml)
    person_id = local_text(body, "personId", "extension")
    log.info("GetListingCounty – person=%s", person_id)

    resp = etree.Element(f"{{{NS}}}GetListingCountyResponse",
                         nsmap={"resp": NS, "core": CORE_NS})

    patient = db.get_patient(person_id, scenario.get()) if person_id else None

    if patient and patient.get("scenario") not in (None, "not_listed") \
               and patient.get("facilityHsaId"):
        # Härleda regionens HSA-id från hälsocentralens HSA-id
        # SE2321000156-A001 → SE2321000156
        facility_hsa = patient["facilityHsaId"]
        region_hsa   = facility_hsa.split("-")[0] if "-" in facility_hsa else facility_hsa

        county_el = sub(resp, NS, "listingCounties")
        sub(county_el, CORE_NS, "root",      HSA_ID_OID)
        sub(county_el, CORE_NS, "extension", region_hsa)
        log.info("GetListingCounty → OK, county=%s for person=%s", region_hsa, person_id)
    else:
        log.info("GetListingCounty → OK, no listing for person=%s", person_id)

    sub(resp, NS, "resultCode", "OK")
    return soap_response(resp)
