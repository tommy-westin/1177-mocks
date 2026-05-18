"""
Snabbtest mot VVH Mock Server.
Kör: python test_remote.py
Kräver: pip install requests
"""
import sys
import requests
from xml.dom.minidom import parseString

BASE = "https://1177-mock.jamtwest.se"

PERSON_ID = "194001019999"   # listad patient med kontakter
PERSON_ID_2 = "197505059999" # listad patient utan kontakter

CORE_NS  = "urn:riv:itintegration:registry:1"
ENVELOPE = """\
<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope
    xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:core="{core}">
  <soapenv:Header/>
  <soapenv:Body>
    {body}
  </soapenv:Body>
</soapenv:Envelope>"""


def post(endpoint: str, body: str, action: str) -> requests.Response:
    xml = ENVELOPE.format(core=CORE_NS, body=body)
    return requests.post(
        f"{BASE}/{endpoint}",
        data=xml.encode("utf-8"),
        headers={
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": action,
        },
        timeout=10,
    )


def pretty(xml_bytes: bytes) -> str:
    try:
        return parseString(xml_bytes).toprettyxml(indent="  ")
    except Exception:
        return xml_bytes.decode()


def check(label: str, resp: requests.Response):
    ok = resp.status_code == 200 and b"Fault" not in resp.content
    status = "OK" if ok else "FEL"
    print(f"\n[{status}] {label} (HTTP {resp.status_code})")
    if not ok or "--verbose" in sys.argv:
        print(pretty(resp.content))


# --- GetListingTypes ---
check("GetListingTypes", post(
    "carelisting/GetListingTypes",
    f"""<req:GetListingTypesRequest
            xmlns:req="urn:riv:supportprocess:logistics:carelisting:GetListingTypesResponder:2">
    </req:GetListingTypesRequest>""",
    "urn:riv:supportprocess:logistics:carelisting:GetListingTypesResponder:2:GetListingTypes",
))

# --- GetListing (listad patient) ---
check(f"GetListing – {PERSON_ID} (listad med kontakter)", post(
    "carelisting/GetListing",
    f"""<req:GetListingRequest
            xmlns:req="urn:riv:supportprocess:logistics:carelisting:GetListingResponder:2">
        <req:personId>
            <core:id>{PERSON_ID}</core:id>
            <core:type>1.2.752.129.2.1.3.1</core:type>
        </req:personId>
    </req:GetListingRequest>""",
    "urn:riv:supportprocess:logistics:carelisting:GetListingResponder:2:GetListing",
))

# --- GetListing (ej listad) ---
check("GetListing – 199001019999 (ej listad)", post(
    "carelisting/GetListing",
    """<req:GetListingRequest
            xmlns:req="urn:riv:supportprocess:logistics:carelisting:GetListingResponder:2">
        <req:personId>
            <core:id>199001019999</core:id>
            <core:type>1.2.752.129.2.1.3.1</core:type>
        </req:personId>
    </req:GetListingRequest>""",
    "urn:riv:supportprocess:logistics:carelisting:GetListingResponder:2:GetListing",
))

# --- GetPersonsForProfile ---
check(f"GetPersonsForProfile – {PERSON_ID}", post(
    "person/GetPersonsForProfile",
    f"""<req:GetPersonsForProfileRequest
            xmlns:req="urn:riv:strategicresourcemanagement:persons:person:GetPersonsForProfileResponder:5">
        <req:personId>{PERSON_ID}</req:personId>
    </req:GetPersonsForProfileRequest>""",
    "urn:riv:strategicresourcemanagement:persons:person:GetPersonsForProfileResponder:5:GetPersonsForProfile",
))

print("\nKlart. Kör med --verbose för att se full XML-respons.")
