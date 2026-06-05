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
import db as _db

# Skapa DB från JSON-filer om den inte finns ännu
if not os.path.exists(_db.DB_PATH):
    import create_db
    print("Skapar databas från JSON-filer...")
    create_db.main()

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
    get_files_for_order_id,
    search_persons_for_profile_by_order,
    file_orders,
)

app = Flask(__name__)

from admin_api import admin
app.register_blueprint(admin)

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
    "GetFilesForOrderIdInteraction_4.0_RIVTABP21.wsdl":
        f"{MOCK_HOST}/person/GetFilesForOrderId",
    "SearchPersonsForProfileByOrderInteraction_5.0_RIVTABP21.wsdl":
        f"{MOCK_HOST}/person/SearchPersonsForProfileByOrder",
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
    "GetFilesForOrderId":               get_files_for_order_id.handle,
    "SearchPersonsForProfileByOrder":   search_persons_for_profile_by_order.handle,
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
        return _serve_wsdl(abs_path, domain)

    directory = os.path.dirname(abs_path)
    return send_from_directory(directory, os.path.basename(abs_path),
                               mimetype="text/xml")


def _serve_wsdl(wsdl_path: str, domain: str | None = None) -> Response:
    if not os.path.isfile(wsdl_path):
        abort(404)

    tree = etree.parse(wsdl_path)
    root = tree.getroot()
    soap_ns = "http://schemas.xmlsoap.org/wsdl/soap/"
    xs_ns   = "http://www.w3.org/2001/XMLSchema"
    wsdl_name = os.path.basename(wsdl_path)
    endpoint = _WSDL_ADDRESS.get(wsdl_name, f"{MOCK_HOST}/unknown")

    for el in root.iter(f"{{{soap_ns}}}address"):
        el.set("location", endpoint)

    # Rewrite relative schemaLocation attributes to absolute URLs so that
    # tools like SoapUI resolve XSD files correctly regardless of the URL
    # the WSDL was fetched from.
    if domain and domain in SCHEMA_BASES:
        schema_base = SCHEMA_BASES[domain]
        wsdl_dir    = os.path.dirname(wsdl_path)
        for el in root.iter(f"{{{xs_ns}}}import"):
            loc = el.get("schemaLocation")
            if loc and not loc.startswith("http"):
                abs_xsd = os.path.normpath(os.path.join(wsdl_dir, loc))
                rel     = os.path.relpath(abs_xsd, schema_base)
                el.set("schemaLocation", f"{MOCK_HOST}/schemas/{domain}/{rel}")

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
            "GetFilesForOrderId":               "interactions/GetFilesForOrderIdInteraction/GetFilesForOrderIdInteraction_4.0_RIVTABP21.wsdl",
            "SearchPersonsForProfileByOrder":   "interactions/SearchPersonsForProfileByOrderInteraction/SearchPersonsForProfileByOrderInteraction_5.0_RIVTABP21.wsdl",
        },
    }
    path = _maps.get(domain, {}).get(operation)
    if path is None:
        abort(404)
    wsdl_abs = os.path.join(SCHEMA_BASES[domain], path)
    return _serve_wsdl(wsdl_abs, domain)


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

def _available_scenarios() -> list[str]:
    patterns = [
        os.path.join(ROOT, "config", "carelisting", "patients_*.json"),
        os.path.join(ROOT, "config", "person", "persons_*.json"),
    ]
    names = set()
    for pattern in patterns:
        import glob
        for path in glob.glob(pattern):
            name = os.path.basename(path).split("_", 1)[1].rsplit(".json", 1)[0]
            names.add(name)
    return ["default"] + sorted(names)


# ---------------------------------------------------------------------------
# REST – getPersonsByFile / order/get  (file-based batch person lookup)
# ---------------------------------------------------------------------------

@app.route("/purest/getPersonsByFile", methods=["POST"])
def get_persons_by_file():
    from services.person.get_persons_for_profile import _build_person_record
    from lxml import etree as _etree

    profile  = request.form.get("profile", "P2")
    csv_file = request.files.get("file")
    if not csv_file:
        return {"error": "Parametern 'file' saknas"}, 400

    lines      = csv_file.read().decode("utf-8", errors="replace").strip().splitlines()
    person_ids = [line.split(";")[0].strip() for line in lines if line.strip()]
    if not person_ids:
        return {"error": "CSV-filen är tom eller ogiltigt formaterad"}, 400

    NS             = "urn:riv:strategicresourcemanagement:persons:person:GetPersonsForProfileResponder:5"
    CORE           = "urn:riv:strategicresourcemanagement:persons:person:5"
    PERSON_ID_ROOT = "1.2.752.129.2.1.3.1"

    resp_el = _etree.Element(f"{{{NS}}}GetPersonsForProfileResponse",
                             nsmap={"resp": NS, "core": CORE})
    for pid in person_ids:
        person = _db.get_person(pid, scenario.get())
        rec_el = _etree.SubElement(resp_el, f"{{{NS}}}requestedPersonRecord")
        req_id = _etree.SubElement(rec_el, f"{{{CORE}}}requestedPersonalIdentity")
        _etree.SubElement(req_id, f"{{{CORE}}}root").text      = PERSON_ID_ROOT
        _etree.SubElement(req_id, f"{{{CORE}}}extension").text = pid
        if person and person.get("scenario") != "not_found":
            pr_el = _etree.SubElement(rec_el, f"{{{CORE}}}personRecord")
            _build_person_record(pr_el, person, profile)

    xml_bytes = _etree.tostring(resp_el, xml_declaration=True,
                                encoding="UTF-8", pretty_print=True)
    order_id, _ = file_orders.create(_zip_xml(xml_bytes, "result"))
    return {"orderId": order_id}, 201


def _zip_xml(xml_bytes: bytes, base_name: str) -> bytes:
    import io, zipfile as _zf
    buf = io.BytesIO()
    with _zf.ZipFile(buf, "w", _zf.ZIP_DEFLATED) as zf:
        zf.writestr(f"{base_name}.xml", xml_bytes)
    return buf.getvalue()


@app.route("/purest/order/get/<guid>", methods=["GET"])
def order_get(guid: str):
    zip_bytes = file_orders.get_zip_by_guid(guid)
    if zip_bytes is None:
        abort(404)
    return Response(
        zip_bytes,
        content_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={guid}.zip"},
    )


@app.route("/scenario", methods=["GET"])
def get_scenario():
    active = scenario.get()
    scenarios = _available_scenarios()
    buttons = "\n".join(
        f"""<button onclick="switchTo('{s}')"
            style="margin:6px;padding:10px 20px;font-size:1rem;cursor:pointer;
                   background:{'#2563eb' if s == active else '#e5e7eb'};
                   color:{'white' if s == active else '#111'};
                   border:none;border-radius:6px;font-weight:{'bold' if s == active else 'normal'}">
            {s}
        </button>"""
        for s in scenarios
    )
    return Response(f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>VVH Mock – Scenario</title>
  <style>body{{font-family:sans-serif;max-width:600px;margin:60px auto;padding:0 20px}}</style>
</head>
<body>
  <h1>Scenario</h1>
  <p>Aktivt: <strong id="active">{active}</strong></p>
  <div id="buttons">{buttons}</div>
  <p id="msg" style="color:green;margin-top:16px"></p>
  <script>
    async function switchTo(name) {{
      const r = await fetch('/scenario/' + name, {{method: 'POST'}});
      const d = await r.json();
      document.getElementById('active').textContent = d.active;
      document.getElementById('msg').textContent = 'Bytte till ' + d.active;
      document.querySelectorAll('button').forEach(b => {{
        const isActive = b.textContent.trim() === d.active;
        b.style.background = isActive ? '#2563eb' : '#e5e7eb';
        b.style.color = isActive ? 'white' : '#111';
        b.style.fontWeight = isActive ? 'bold' : 'normal';
      }});
    }}
  </script>
</body>
</html>""", content_type="text/html")


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

    lines.append("<h2>REST (filhantering)</h2><ul>")
    lines.append(
        f"<li><b>POST</b> <code>{MOCK_HOST}/purest/getPersonsByFile</code>"
        " &nbsp; multipart/form-data: <code>file</code> (CSV), <code>profile</code> (P1-P5)"
        " &nbsp;→ <code>{{\"orderId\": \"...\"}}</code></li>"
    )
    lines.append(
        f"<li><b>SOAP GetFilesForOrderId</b> &nbsp; polla med orderId"
        " &nbsp;→ returnerar nedladdningslänk när klar (direkt i mock)</li>"
    )
    lines.append(
        f"<li><b>GET</b> <code>{MOCK_HOST}/purest/order/get/{{guid}}</code>"
        " &nbsp;→ ZIP med XML (GetPersonsForProfileResponse-format)</li>"
    )
    lines.append("</ul>")

    lines.append(
        f"<p><a href='{MOCK_HOST}/scenario'>Scenario-växling</a> &nbsp; "
        f"Aktivt: <b>{scenario.get()}</b></p>"
    )
    return "\n".join(lines)


if __name__ == "__main__":
    print(f"Starting VVH Mock Server on port {PORT}")
    for domain, base in SCHEMA_BASES.items():
        print(f"  Schema [{domain}]: {base}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
