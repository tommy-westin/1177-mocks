"""
Smoke tests for vvh-mocks. Run with the server already started on port 8088.

    python server.py
    python tests/smoke_test.py   (i ett separat terminalfönster)

Uses zeep as SOAP client, mirroring how the real VVH application will call the service.

Note on LogicalAddress:
  In RIVTABP21, LogicalAddress is defined as a soap:header part in the WSDL binding,
  not as a body parameter. zeep therefore requires it to be passed via _soapheaders
  as an lxml Element — NOT as a regular kwarg.
"""
import sys
import traceback
import requests
from lxml import etree

try:
    from zeep import Client, Settings
    from zeep.transports import Transport
except ImportError:
    print("zeep is not installed. Run: pip install zeep")
    sys.exit(1)

BASE = "http://localhost:8088"
ITR_NS = "urn:riv:itintegration:registry:1"

# Bypass system proxy so requests reach mock server at localhost directly.
_session = requests.Session()
_session.trust_env = False
_TRANSPORT = Transport(session=_session)

WSDL = {
    "GetListingTypes":
        f"{BASE}/schemas/carelisting/interactions/GetListingTypesInteraction/GetListingTypesInteraction_2.0_RIVTABP21.wsdl",
    "GetAvailableHealthcareFacilities":
        f"{BASE}/schemas/carelisting/interactions/GetAvailableHealthcareFacilitiesInteraction/GetAvailableHealthcareFacilitiesInteraction_2.1_RIVTABP21.wsdl",
    "GetAvailableHealthcarePersonnel":
        f"{BASE}/schemas/carelisting/interactions/GetAvailableHealthcarePersonnelInteraction/GetAvailableHealthcarePersonnelInteraction_2.0_RIVTABP21.wsdl",
    "GetListing":
        f"{BASE}/schemas/carelisting/interactions/GetListingInteraction/GetListingInteraction_2.1_RIVTABP21.wsdl",
    "CreateListing":
        f"{BASE}/schemas/carelisting/interactions/CreateListingInteraction/CreateListingInteraction_2.0_RIVTABP21.wsdl",
    "UpdateListing":
        f"{BASE}/schemas/carelisting/interactions/UpdateListingInteraction/UpdateListingInteraction_2.0_RIVTABP21.wsdl",
}

SETTINGS = Settings(strict=False, xml_huge_tree=True)

LOGICAL_ADDRESS = "SE2321000156"
ACTOR = {
    "actorId": {"root": "1.2.752.129.2.1.4.1", "extension": "SE2321000156-SYSTEM"},
    "actorType": "REGION",
}
PERSON_ID_KNOWN = {"root": "1.2.752.129.2.1.3.1", "extension": "194001019999"}
PERSON_ID_UNKNOWN = {"root": "1.2.752.129.2.1.3.1", "extension": "200101019999"}

results: list[tuple[str, bool, str]] = []


def logical_address(address: str) -> etree._Element:
    """Build the LogicalAddress SOAP header element."""
    el = etree.Element(f"{{{ITR_NS}}}LogicalAddress")
    el.text = address
    return el


LA = [logical_address(LOGICAL_ADDRESS)]


def ok(name: str, detail: str = "") -> None:
    results.append((name, True, detail))
    print(f"  [PASS] {name}" + (f" – {detail}" if detail else ""))


def fail(name: str, detail: str) -> None:
    results.append((name, False, detail))
    print(f"  [FAIL] {name} – {detail}")


def client(op: str) -> Client:
    return Client(WSDL[op], settings=SETTINGS, transport=_TRANSPORT)


# ---------------------------------------------------------------------------
# Test 1: GetListingTypes returns 3 types
# ---------------------------------------------------------------------------
def test_get_listing_types():
    try:
        c = client("GetListingTypes")
        result = c.service.GetListingTypes(_soapheaders=LA)
        types = result.listingTypes or []
        assert len(types) >= 3, f"Expected >=3 types, got {len(types)}"
        codes = [lt.code for lt in types]
        assert "PRIMARY_CARE" in codes
        assert "FAST_DOCTOR_CONTACT" in codes
        assert "FAST_CARE_CONTACT" in codes
        ok("GetListingTypes – 3 listningstyper", f"codes={codes}")
    except Exception:
        fail("GetListingTypes", traceback.format_exc())


# ---------------------------------------------------------------------------
# Test 2: GetAvailableHealthcareFacilities returns ≥ 5 facilities
# ---------------------------------------------------------------------------
def test_get_facilities():
    try:
        c = client("GetAvailableHealthcareFacilities")
        result = c.service.GetAvailableHealthcareFacilities(_soapheaders=LA)
        facs = result.healthcareFacilities or []
        assert len(facs) >= 5, f"Expected >=5 facilities, got {len(facs)}"
        ok("GetAvailableHealthcareFacilities – ≥5 enheter", f"count={len(facs)}")
    except Exception:
        fail("GetAvailableHealthcareFacilities", traceback.format_exc())


# ---------------------------------------------------------------------------
# Test 3: GetAvailableHealthcarePersonnel for a specific facility
# ---------------------------------------------------------------------------
def test_get_personnel():
    try:
        c = client("GetAvailableHealthcarePersonnel")
        result = c.service.GetAvailableHealthcarePersonnel(
            _soapheaders=LA,
            personId=PERSON_ID_KNOWN,
            healthcareFacilityHSAId="SE2321000156-A001",
        )
        personnel = result.healthcarePersonnel or []
        assert len(personnel) >= 1, f"Expected >=1 personnel, got {len(personnel)}"
        ok("GetAvailableHealthcarePersonnel – personal hittad", f"count={len(personnel)}")
    except Exception:
        fail("GetAvailableHealthcarePersonnel", traceback.format_exc())


# ---------------------------------------------------------------------------
# Test 4: GetListing for known patient returns listings
# ---------------------------------------------------------------------------
def test_get_listing_known():
    try:
        c = client("GetListing")
        result = c.service.GetListing(
            _soapheaders=LA,
            actor=ACTOR,
            personId=PERSON_ID_KNOWN,
        )
        listings = result.listings or []
        assert len(listings) >= 1, f"Expected >=1 listings, got {len(listings)}"
        ok("GetListing – känd patient har listningar", f"count={len(listings)}")
    except Exception:
        fail("GetListing (known patient)", traceback.format_exc())


# ---------------------------------------------------------------------------
# Test 5: GetListing for unknown patient returns empty OK
# ---------------------------------------------------------------------------
def test_get_listing_unknown():
    try:
        c = client("GetListing")
        result = c.service.GetListing(
            _soapheaders=LA,
            actor=ACTOR,
            personId=PERSON_ID_UNKNOWN,
        )
        listings = result.listings or []
        assert result.resultCode == "OK"
        assert len(listings) == 0, f"Expected 0 listings, got {len(listings)}"
        ok("GetListing – okänd patient → tomt OK")
    except Exception:
        fail("GetListing (unknown patient)", traceback.format_exc())


# ---------------------------------------------------------------------------
# Test 6: CreateListing + efterföljande GetListing
# ---------------------------------------------------------------------------
def test_create_then_get():
    try:
        cc = client("CreateListing")
        new_person = {"root": "1.2.752.129.2.1.3.1", "extension": "198801019999"}
        result = cc.service.CreateListing(
            _soapheaders=LA,
            actor=ACTOR,
            personId=new_person,
            healthcareFacilityHSAId="SE2321000156-A002",
            listingType={"code": "PRIMARY_CARE", "codeSystem": "1.2.752.129.2.2.4.1"},
        )
        assert result.resultCode == "OK", \
            f"CreateListing failed: {result.resultCode} {result.resultText}"
        ok("CreateListing – giltig request → OK")

        gc = client("GetListing")
        get_result = gc.service.GetListing(
            _soapheaders=LA,
            actor=ACTOR,
            personId=new_person,
        )
        listings = get_result.listings or []
        assert len(listings) >= 1, \
            f"Expected listing after CreateListing, got {len(listings)}"
        ok("CreateListing → GetListing – listning syns i efterföljande GetListing")
    except AssertionError as e:
        fail("CreateListing → GetListing", str(e))
    except Exception:
        fail("CreateListing → GetListing", traceback.format_exc())


# ---------------------------------------------------------------------------
# Test 7: CreateListing with invalid facility → ERROR
# ---------------------------------------------------------------------------
def test_create_invalid_facility():
    try:
        cc = client("CreateListing")
        result = cc.service.CreateListing(
            _soapheaders=LA,
            actor=ACTOR,
            personId={"root": "1.2.752.129.2.1.3.1", "extension": "198901019999"},
            healthcareFacilityHSAId="SE9999999999-XXXX",  # does not exist
            listingType={"code": "PRIMARY_CARE", "codeSystem": "1.2.752.129.2.2.4.1"},
        )
        assert result.resultCode == "ERROR", f"Expected ERROR, got {result.resultCode}"
        ok("CreateListing – ogiltig facility → ERROR", result.resultText or "")
    except AssertionError as e:
        fail("CreateListing (invalid facility)", str(e))
    except Exception:
        fail("CreateListing (invalid facility)", traceback.format_exc())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("VVH Mock Server – Smoke Tests")
    print("=" * 60)
    test_get_listing_types()
    test_get_facilities()
    test_get_personnel()
    test_get_listing_known()
    test_get_listing_unknown()
    test_create_then_get()
    test_create_invalid_facility()

    print()
    passed = sum(1 for _, ok_, _ in results if ok_)
    total = len(results)
    print(f"Result: {passed}/{total} passed")
    if passed < total:
        sys.exit(1)
