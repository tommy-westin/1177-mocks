"""
Snabbtest mot VVH Mock Server.
Kör: python test_remote.py
Kräver: pip install requests
"""
import os
import sys
import requests
from xml.dom.minidom import parseString

BASE = "https://1177-mock.jamtwest.se"
DUMP = "--dump" in sys.argv
DUMP_DIR = "test_responses"

PERSON_ID   = "194001019999"  # listad med kontakter
PERSON_ID_2 = "197505059999"  # listad utan kontakter
PERSON_ID_3 = "199001019999"  # ej listad

PERSON_ID_ROOT = "1.2.752.129.2.1.3.1"
ACTOR_ID_ROOT  = "1.2.752.129.2.1.4.1"
ACTOR_ID_EXT   = "SE2321000156-A001"

ENVELOPE = """\
<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
  <soapenv:Header/>
  <soapenv:Body>
    {body}
  </soapenv:Body>
</soapenv:Envelope>"""


def post(endpoint: str, body: str, action: str) -> requests.Response:
    return requests.post(
        f"{BASE}/{endpoint}",
        data=ENVELOPE.format(body=body).encode("utf-8"),
        headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": action},
        timeout=10,
    )


def pretty(xml_bytes: bytes) -> str:
    try:
        return parseString(xml_bytes).toprettyxml(indent="  ")
    except Exception:
        return xml_bytes.decode()


_dump_counter = 0

def check(label: str, resp: requests.Response):
    global _dump_counter
    ok = resp.status_code == 200 and b"Fault" not in resp.content
    print(f"\n[{'OK' if ok else 'FEL'}] {label} (HTTP {resp.status_code})")
    if not ok or "--verbose" in sys.argv:
        print(pretty(resp.content))
    if DUMP:
        os.makedirs(DUMP_DIR, exist_ok=True)
        _dump_counter += 1
        slug = label.split("–")[0].strip().replace(" ", "_").replace("/", "_")
        filename = os.path.join(DUMP_DIR, f"{_dump_counter:02d}_{slug}.xml")
        with open(filename, "wb") as f:
            f.write(pretty(resp.content).encode("utf-8"))
        print(f"  → sparad: {filename}")


def person_id_xml(pid: str, ns: str) -> str:
    return f"""<{ns}:personId>
            <{ns}:root>{PERSON_ID_ROOT}</{ns}:root>
            <{ns}:extension>{pid}</{ns}:extension>
        </{ns}:personId>"""


def actor_xml(ns: str) -> str:
    return f"""<{ns}:actor>
            <{ns}:actorId>
                <{ns}:root>{ACTOR_ID_ROOT}</{ns}:root>
                <{ns}:extension>{ACTOR_ID_EXT}</{ns}:extension>
            </{ns}:actorId>
            <{ns}:actorType>healthcare_professional</{ns}:actorType>
        </{ns}:actor>"""


# --- GetListingTypes ---
check("GetListingTypes", post(
    "carelisting/GetListingTypes",
    """<req:GetListingTypesRequest
            xmlns:req="urn:riv:supportprocess:logistics:carelisting:GetListingTypesResponder:2">
    </req:GetListingTypesRequest>""",
    "urn:riv:supportprocess:logistics:carelisting:GetListingTypesResponder:2:GetListingTypes",
))

# --- GetListing (listad patient med kontakter) ---
NS_CL = "urn:riv:supportprocess:logistics:carelisting:GetListingResponder:2"
check(f"GetListing – {PERSON_ID} (listad med kontakter)", post(
    "carelisting/GetListing",
    f"""<req:GetListingRequest xmlns:req="{NS_CL}">
        {actor_xml("req")}
        {person_id_xml(PERSON_ID, "req")}
    </req:GetListingRequest>""",
    f"{NS_CL}:GetListing",
))

# --- GetListing (ej listad) ---
check(f"GetListing – {PERSON_ID_3} (ej listad)", post(
    "carelisting/GetListing",
    f"""<req:GetListingRequest xmlns:req="{NS_CL}">
        {actor_xml("req")}
        {person_id_xml(PERSON_ID_3, "req")}
    </req:GetListingRequest>""",
    f"{NS_CL}:GetListing",
))

# --- GetPersonsForProfile ---
NS_PP = "urn:riv:strategicresourcemanagement:persons:person:GetPersonsForProfileResponder:5"
check(f"GetPersonsForProfile – {PERSON_ID} + {PERSON_ID_2}", post(
    "person/GetPersonsForProfile",
    f"""<req:GetPersonsForProfileRequest xmlns:req="{NS_PP}">
        {person_id_xml(PERSON_ID, "req")}
        {person_id_xml(PERSON_ID_2, "req")}
        <req:profile>P2</req:profile>
    </req:GetPersonsForProfileRequest>""",
    f"{NS_PP}:GetPersonsForProfile",
))

print("\nKlart. Flaggor: --verbose (skriv ut XML), --dump (spara till test_responses/)")
