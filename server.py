"""
VVH Mock Server – Flask SOAP server for 1177 NTjP contracts.

Start: python server.py

WSDL examples:
  http://localhost:8088/schemas/carelisting/interactions/GetListingInteraction/GetListingInteraction_2.1_RIVTABP21.wsdl
  http://localhost:8088/schemas/person/interactions/GetPersonsForProfileInteraction/GetPersonsForProfileInteraction_5.0_RIVTABP21.wsdl

SOAP endpoints:
  http://localhost:8088/carelisting/<Operation>
  http://localhost:8088/person/<Operation>

Adding a new domain:
  1. Add schemas to the source project under <domain>_1177/schemas/
  2. Create config/<domain>/*.json
  3. Create services/<domain>/*.py
  4. Add SCHEMA_BASE, WSDL_ADDRESS dict, HANDLERS dict, and route below
"""
import os
import sys
import traceback

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from flask import Flask, request, Response, send_from_directory, abort
from lxml import etree
import logging_config  # noqa: F401 – configures handlers
import scenario

# --- carelisting services ---
from services.carelisting import (
    get_listing_types,
    get_facilities,
    get_personnel,
    get_listing,
    create_listing,
    update_listing,
)

# --- person services ---
from services.person import (
    get_persons_for_profile,
    get_persons_for_profile_unrestricted,
)

app = Flask(__name__)

PORT = int(os.environ.get("MOCK_PORT", "8088"))
MOCK_HOST = os.environ.get("MOCK_HOST", f"http://localhost:{PORT}")
SOAP_CONTENT_TYPE = "text/xml; charset=utf-8"

# ---------------------------------------------------------------------------
# Schema bases – prefer schemas bundled in repo, fall back to sibling project
# ---------------------------------------------------------------------------

_parent = os.path.normpath(os.path.join(ROOT, ".."))
if os.path.isdir(os.path.join(ROOT, "carelisting_1177")):
    _PROJECT_ROOT = ROOT                                           # schemas bundled in repo
elif os.path.isdir(os.path.join(_parent, "carelisting_1177")):
    _PROJECT_ROOT = _parent                                        # inside vardvalshanteraren/
else:
    _PROJECT_ROOT = os.path.join(_parent, "vardvalshanteraren")   # beside vardvalshanteraren/

SCHEMA_BASES: dict[str, str] = {
    "carelisting": os.path.join(_PROJECT_ROOT, "carelisting_1177", "schemas"),
    "person":      os.path.join(_PROJECT_ROOT, "person_1177",      "schemas"),
}

# ---------------------------------------------------------------------------
# WSDL filename → SOAP endpoint mapping (one dict per domain)
# ---------------------------------------------------------------------------

_CARELISTING_WSDL = {
    "GetListingTypesInteraction_2.0_RIVTABP21.wsdl":
        f"{MOCK_HOST}/carelisting/GetListingTypes",
    "GetAvailableHealthcareFacilitiesInteraction_2.1_RIVTABP21.wsdl":
        f"{MOCK_HOST}/carelisting/GetAvailableHealthcareFacilities",
    "GetAvailableHealthcarePersonnelInteraction_2.0_RIVTABP21.wsdl":
        f"{MOCK_HOST}/carelisting/GetAvailableHealthcarePersonnel",
    "GetListingInteraction_2.1_RIVTABP21.wsdl":
        f"{MOCK_HOST}/carelisting/GetListing",
    "CreateListingInteraction_2.0_RIVTABP21.wsdl":
        f"{MOCK_HOST}/carelisting/CreateListing",
    "UpdateListingInteraction_2.0_RIVTABP21.wsdl":
        f"{MOCK_HOST}/carelisting/UpdateListing",
}

_PERSON_WSDL = {
    "GetPersonsForProfileInteraction_5.0_RIVTABP21.wsdl":
        f"{MOCK_HOST}/person/GetPersonsForProfile",
    "GetPersonsForProfileUnrestrictedInteraction_5.0_RIVTABP21.wsdl":
        f"{MOCK_HOST}/person/GetPersonsForProfileUnrestricted",
}

_WSDL_ADDRESS: dict[str, str] = {**_CARELISTING_WSDL, **_PERSON_WSDL}

# ---------------------------------------------------------------------------
# Operation → handler mapping
# ---------------------------------------------------------------------------

CARELISTING_HANDLERS = {
    "GetListingTypes":                  get_listing_types.handle,
    "GetAvailableHealthcareFacilities": get_facilities.handle,
    "GetAvailableHealthcarePersonnel":  get_personnel.handle,
    "GetListing":                       get_listing.handle,
    "CreateListing":                    create_listing.handle,
    "UpdateListing":                    update_listing.handle,
}

PERSON_HANDLERS = {
    "GetPersonsForProfile":             get_persons_for_profile.handle,
    "GetPersonsForProfileUnrestricted": get_persons_for_profile_unrestricted.handle,
}

# ---------------------------------------------------------------------------
# Schema / WSDL serving  (generic, reused by all domains)
# ---------------------------------------------------------------------------

def _serve_schema_file(domain: str, filename: str) -> Response:
    base = SCHEMA_BASES.get(domain)
    if base is None:
        abort(404)

    abs_path = os.path.normpath(os.path.join(base, filename))
    if not abs_path.startswith(base):
        abort(403)

    if filename.endswith(".wsdl"):
        return _serve_wsdl(abs_path)

    directory = os.path.dirname(abs_path)
    return send_from_directory(directory, os.path.basename(abs_path),
                               mimetype="text/xml")


def _serve_wsdl(wsdl_path: str) -> Response:
    if not os.path.isfile(wsdl_path):
        abort(404)

    tree = etree.parse(wsdl_path)
    soap_ns = "http://schemas.xmlsoap.org/wsdl/soap/"
    wsdl_name = os.path.basename(wsdl_path)
    endpoint = _WSDL_ADDRESS.get(wsdl_name,
                                  f"http://localhost:{PORT}/unknown")

    for el in tree.getroot().iter(f"{{{soap_ns}}}address"):
        el.set("location", endpoint)

    xml_bytes = etree.tostring(tree, xml_declaration=True, encoding="UTF-8",
                               pretty_print=True)
    return Response(xml_bytes, content_type=SOAP_CONTENT_TYPE)


@app.route("/schemas/carelisting/<path:filename>")
def serve_carelisting_schema(filename: str):
    return _serve_schema_file("carelisting", filename)


@app.route("/schemas/person/<path:filename>")
def serve_person_schema(filename: str):
    return _serve_schema_file("person", filename)


# ---------------------------------------------------------------------------
# SOAP dispatch  (generic helper, one route per domain)
# ---------------------------------------------------------------------------

def _dispatch(handlers: dict, raw_xml: bytes, operation: str) -> Response:
    handler = handlers.get(operation)
    if handler is None:
        return Response(_soap_fault(f"Unknown operation: {operation}"),
                        status=500, content_type=SOAP_CONTENT_TYPE)
    try:
        return Response(handler(raw_xml), content_type=SOAP_CONTENT_TYPE)
    except Exception as exc:
        traceback.print_exc()
        return Response(_soap_fault(str(exc)), status=500,
                        content_type=SOAP_CONTENT_TYPE)


@app.route("/carelisting/<operation>", methods=["GET", "POST"])
def carelisting(operation: str):
    if request.method == "GET" and "wsdl" in request.args:
        return _wsdl_redirect("carelisting", operation)
    if request.method != "POST":
        abort(405)
    return _dispatch(CARELISTING_HANDLERS, request.data, operation)


@app.route("/person/<operation>", methods=["GET", "POST"])
def person(operation: str):
    if request.method == "GET" and "wsdl" in request.args:
        return _wsdl_redirect("person", operation)
    if request.method != "POST":
        abort(405)
    return _dispatch(PERSON_HANDLERS, request.data, operation)


def _wsdl_redirect(domain: str, operation: str) -> Response:
    _maps = {
        "carelisting": {
            "GetListingTypes":                  "interactions/GetListingTypesInteraction/GetListingTypesInteraction_2.0_RIVTABP21.wsdl",
            "GetAvailableHealthcareFacilities": "interactions/GetAvailableHealthcareFacilitiesInteraction/GetAvailableHealthcareFacilitiesInteraction_2.1_RIVTABP21.wsdl",
            "GetAvailableHealthcarePersonnel":  "interactions/GetAvailableHealthcarePersonnelInteraction/GetAvailableHealthcarePersonnelInteraction_2.0_RIVTABP21.wsdl",
            "GetListing":                       "interactions/GetListingInteraction/GetListingInteraction_2.1_RIVTABP21.wsdl",
            "CreateListing":                    "interactions/CreateListingInteraction/CreateListingInteraction_2.0_RIVTABP21.wsdl",
            "UpdateListing":                    "interactions/UpdateListingInteraction/UpdateListingInteraction_2.0_RIVTABP21.wsdl",
        },
        "person": {
            "GetPersonsForProfile":             "interactions/GetPersonsForProfileInteraction/GetPersonsForProfileInteraction_5.0_RIVTABP21.wsdl",
            "GetPersonsForProfileUnrestricted": "interactions/GetPersonsForProfileUnrestrictedInteraction/GetPersonsForProfileUnrestrictedInteraction_5.0_RIVTABP21.wsdl",
        },
    }
    path = _maps.get(domain, {}).get(operation)
    if path is None:
        abort(404)
    url = f"{MOCK_HOST}/schemas/{domain}/{path}"
    return Response(status=302, headers={"Location": url})


def _soap_fault(message: str) -> bytes:
    SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
    env = etree.Element(f"{{{SOAP_NS}}}Envelope")
    body = etree.SubElement(env, f"{{{SOAP_NS}}}Body")
    fault = etree.SubElement(body, f"{{{SOAP_NS}}}Fault")
    etree.SubElement(fault, "faultcode").text = "soapenv:Server"
    etree.SubElement(fault, "faultstring").text = message
    return etree.tostring(env, xml_declaration=True, encoding="UTF-8")


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------

@app.route("/scenario", methods=["GET"])
def get_scenario():
    return {"active": scenario.get()}


@app.route("/scenario/<name>", methods=["POST"])
def set_scenario(name: str):
    scenario.switch(name)
    return {"active": scenario.get()}


@app.route("/")
def index():
    lines = ["<h1>VVH Mock Server</h1>"]
    for domain, handlers in [("carelisting", CARELISTING_HANDLERS),
                              ("person", PERSON_HANDLERS)]:
        lines.append(f"<h2>{domain}</h2><ul>")
        for op in handlers:
            wsdl = f"{MOCK_HOST}/{domain}/{op}?wsdl"
            soap = f"{MOCK_HOST}/{domain}/{op}"
            lines.append(
                f"<li><b>{op}</b> &nbsp; "
                f"WSDL: <a href='{wsdl}'>{wsdl}</a> &nbsp; SOAP: {soap}</li>"
            )
        lines.append("</ul>")
    return "\n".join(lines)


if __name__ == "__main__":
    print(f"Starting VVH Mock Server on port {PORT}")
    for domain, base in SCHEMA_BASES.items():
        print(f"  Schema [{domain}]: {base}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
