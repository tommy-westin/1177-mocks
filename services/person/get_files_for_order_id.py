import os
from lxml import etree
from .xml_utils import parse_body, local_text, soap_response, sub
from . import file_orders

NS = "urn:riv:strategicresourcemanagement:persons:person:GetFilesForOrderIdResponder:4"
MOCK_HOST = os.environ.get("MOCK_HOST", "http://localhost:8088")


def handle(raw_xml: bytes) -> bytes:
    body     = parse_body(raw_xml)
    order_id = local_text(body, "orderId")

    resp = etree.Element(f"{{{NS}}}GetFilesForOrderIdResponse", nsmap={"resp": NS})

    order = file_orders.get_by_order_id(order_id) if order_id else None
    if order:
        mm = sub(resp, NS, "multimedia")
        sub(mm, NS, "mediaType", "application/zip")
        sub(mm, NS, "reference",
            f"{MOCK_HOST}/purest/order/get/{order['guid']}")

    return soap_response(resp)
