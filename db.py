"""
SQLite-databas för mockdata.

En enda fil: config/data.db
Tabeller: persons, patients, listing_types, facilities, facility_listing_types, personnel

Alla scenario-beroende tabeller (persons, patients, listing_types) har en
scenario_name-kolumn ('default', 'massavflyttning', etc.).
Queries faller automatiskt tillbaka på 'default' om ingen rad finns i
det begärda scenariot.
"""
import os
import sqlite3
from typing import Optional

ROOT    = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DB_PATH",
          os.path.join(ROOT, "config", "data.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS persons (
    personId                TEXT NOT NULL,
    scenario_name           TEXT NOT NULL DEFAULT 'default',
    scenario                TEXT,
    givenName               TEXT,
    surname                 TEXT,
    countyCode              TEXT,
    municipalityCode        TEXT,
    postalAddress1          TEXT,
    postalCode              TEXT,
    city                    TEXT,
    protectedPersonIndicator INTEGER NOT NULL DEFAULT 0,
    testIndicator           INTEGER NOT NULL DEFAULT 1,
    deregistrationReasonCode TEXT,
    deregistrationDate      TEXT,
    PRIMARY KEY (personId, scenario_name)
);

CREATE TABLE IF NOT EXISTS patients (
    personId      TEXT NOT NULL,
    scenario_name TEXT NOT NULL DEFAULT 'default',
    scenario      TEXT,
    facilityHsaId TEXT,
    isInQueue     INTEGER NOT NULL DEFAULT 0,
    isOutOfCounty INTEGER NOT NULL DEFAULT 0,
    homeCountyCode TEXT,
    PRIMARY KEY (personId, scenario_name)
);

CREATE TABLE IF NOT EXISTS listing_types (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    personId        TEXT NOT NULL,
    scenario_name   TEXT NOT NULL DEFAULT 'default',
    code            TEXT NOT NULL,
    doctorHsaId     TEXT,
    careContactHsaId TEXT
);

CREATE TABLE IF NOT EXISTS facilities (
    hsaId                      TEXT PRIMARY KEY,
    name                       TEXT,
    hasQueue                   INTEGER NOT NULL DEFAULT 0,
    supportsHealthcarePersonnel INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS facility_listing_types (
    hsaId TEXT NOT NULL,
    code  TEXT NOT NULL,
    PRIMARY KEY (hsaId, code)
);

CREATE TABLE IF NOT EXISTS personnel (
    hsaId          TEXT PRIMARY KEY,
    name           TEXT,
    title          TEXT,
    professionCode TEXT,
    facilityHsaId  TEXT
);
"""


def create_schema():
    with _connect() as conn:
        conn.executescript(SCHEMA)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _person_row_to_dict(row) -> dict:
    d = dict(row)
    d["protectedPersonIndicator"] = bool(d.get("protectedPersonIndicator", 0))
    d["testIndicator"]            = bool(d.get("testIndicator", 1))
    return d


def _patient_row_to_dict(conn, row) -> dict:
    d = dict(row)
    d["isInQueue"]     = bool(d.get("isInQueue", 0))
    d["isOutOfCounty"] = bool(d.get("isOutOfCounty", 0))
    lts = conn.execute(
        "SELECT code, doctorHsaId, careContactHsaId FROM listing_types "
        "WHERE personId = ? AND scenario_name = ?",
        (d["personId"], d["scenario_name"]),
    ).fetchall()
    d["listingTypes"] = [_lt_dict(lt) for lt in lts]
    return d


def _lt_dict(row) -> dict:
    d: dict = {"code": row["code"]}
    if row["doctorHsaId"]:
        d["doctorHsaId"]     = row["doctorHsaId"]
    if row["careContactHsaId"]:
        d["careContactHsaId"] = row["careContactHsaId"]
    return d


# ---------------------------------------------------------------------------
# Persons
# ---------------------------------------------------------------------------

def get_person(person_id: str, scenario_name: str = "default") -> Optional[dict]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM persons WHERE personId = ? AND scenario_name = ?",
            (person_id, scenario_name),
        ).fetchone()
        if row is None and scenario_name != "default":
            row = conn.execute(
                "SELECT * FROM persons WHERE personId = ? AND scenario_name = 'default'",
                (person_id,),
            ).fetchone()
        return _person_row_to_dict(row) if row else None


def get_all_persons(scenario_name: str = "default") -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM persons WHERE scenario_name = ? AND scenario != 'not_found'",
            (scenario_name,),
        ).fetchall()
        if not rows and scenario_name != "default":
            rows = conn.execute(
                "SELECT * FROM persons WHERE scenario_name = 'default' "
                "AND scenario != 'not_found'"
            ).fetchall()
        return [_person_row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Patients
# ---------------------------------------------------------------------------

def get_patient(person_id: str, scenario_name: str = "default") -> Optional[dict]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM patients WHERE personId = ? AND scenario_name = ?",
            (person_id, scenario_name),
        ).fetchone()
        if row is None and scenario_name != "default":
            row = conn.execute(
                "SELECT * FROM patients WHERE personId = ? AND scenario_name = 'default'",
                (person_id,),
            ).fetchone()
        return _patient_row_to_dict(conn, row) if row else None


# ---------------------------------------------------------------------------
# Facilities
# ---------------------------------------------------------------------------

def get_facility(hsa_id: str) -> Optional[dict]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM facilities WHERE hsaId = ?", (hsa_id,)
        ).fetchone()
        if row is None:
            return None
        fac = dict(row)
        fac["hasQueue"]                   = bool(fac["hasQueue"])
        fac["supportsHealthcarePersonnel"] = bool(fac["supportsHealthcarePersonnel"])
        codes = conn.execute(
            "SELECT code FROM facility_listing_types WHERE hsaId = ?", (hsa_id,)
        ).fetchall()
        fac["supportedListingTypes"] = [r["code"] for r in codes]
        return fac


def get_all_facilities() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("SELECT hsaId FROM facilities").fetchall()
    return [get_facility(r["hsaId"]) for r in rows]


# ---------------------------------------------------------------------------
# Personnel
# ---------------------------------------------------------------------------

def get_personnel_member(hsa_id: str) -> Optional[dict]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM personnel WHERE hsaId = ?", (hsa_id,)
        ).fetchone()
        return dict(row) if row else None


def get_all_personnel() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM personnel").fetchall()
        return [dict(r) for r in rows]
