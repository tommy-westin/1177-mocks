import json
import os
from lxml import etree
from .xml_utils import (
    CORE_NS, RESP_NS, soap_response, sub, add_cv_type, parse_body
)
import logging_config  # noqa: F401 – triggers handler setup

log = logging_config.request_logger

_CONFIG = os.path.join(os.path.dirname(__file__), "../../config/carelisting/listing_types.json")

NS = RESP_NS["GetListingTypes"]


def _load_types() -> list[dict]:
    with open(_CONFIG, encoding="utf-8") as f:
        return json.load(f)


def handle(raw_xml: bytes) -> bytes:
    body = parse_body(raw_xml)
    log.info("GetListingTypes called")

    listing_types = _load_types()

    resp = etree.Element(f"{{{NS}}}GetListingTypesResponse", nsmap={
        "resp": NS, "core": CORE_NS
    })
    for lt in listing_types:
        lt_el = sub(resp, NS, "listingTypes")
        add_cv_type(lt_el, lt["code"], lt["codeSystem"], lt.get("displayName"))

    sub(resp, NS, "resultCode", "OK")
    log.info("GetListingTypes → OK, %d types", len(listing_types))
    return soap_response(resp)
