from lxml import etree
from .xml_utils import RESP_NS, soap_response, sub, parse_body, local_text
import logging_config  # noqa: F401

log = logging_config.request_logger

NS = RESP_NS["UpdateListing"]


def handle(raw_xml: bytes) -> bytes:
    body = parse_body(raw_xml)

    person_id = local_text(body, "personId", "extension")
    listing_type_code = local_text(body, "listingType", "code")

    log.info("UpdateListing – person=%s listingType=%s", person_id, listing_type_code)
    try:
        log.info("UpdateListing payload:\n%s",
                 etree.tostring(body, pretty_print=True).decode() if body is not None else "<none>")
    except Exception:
        pass

    resp = etree.Element(f"{{{NS}}}UpdateListingResponse", nsmap={"resp": NS})
    sub(resp, NS, "resultCode", "OK")
    log.info("UpdateListing → OK for person=%s", person_id)
    return soap_response(resp)
