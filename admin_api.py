"""
Admin REST API – CRUD för alla tabeller i data.db

Alla endpoints under /admin/

Scenario-medvetna tabeller (persons, patients):
  ?scenario=  väljer scenario_name, standard = aktivt scenario

Endpoints:
  GET/POST/PUT/DELETE  /admin/persons[/<personId>]
  GET/POST/PUT/DELETE  /admin/patients[/<personId>]
  GET/POST/PUT/DELETE  /admin/facilities[/<hsaId>]
  GET/POST/PUT/DELETE  /admin/personnel[/<hsaId>]
  POST                 /admin/rebuild-db   (kör om migrationen från JSON)
"""
import sqlite3
from flask import Blueprint, request, jsonify
import db
import scenario as _scenario
from auth import check_api_key

admin = Blueprint("admin", __name__, url_prefix="/admin")
admin.before_request(check_api_key)


def _scen() -> str:
    return request.args.get("scenario", _scenario.get())


def _connect():
    conn = sqlite3.connect(db.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ok(data, status=200):
    return jsonify(data), status


def _err(msg, status=400):
    return jsonify({"error": msg}), status


# ---------------------------------------------------------------------------
# PERSONS
# ---------------------------------------------------------------------------

@admin.get("/persons")
def list_persons():
    scen = _scen()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM persons WHERE scenario_name = ? ORDER BY personId",
            (scen,)
        ).fetchall()
    return _ok([dict(r) for r in rows])


@admin.get("/persons/<person_id>")
def get_person(person_id):
    scen = _scen()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM persons WHERE personId = ? AND scenario_name = ?",
            (person_id, scen)
        ).fetchone()
    if row is None:
        return _err("Hittades inte", 404)
    return _ok(dict(row))


@admin.post("/persons")
def create_person():
    data = request.get_json(force=True)
    if not data.get("personId"):
        return _err("personId krävs")
    scen = data.get("scenario_name", _scen())
    try:
        with _connect() as conn:
            conn.execute("""
                INSERT INTO persons
                  (personId, scenario_name, scenario,
                   givenName, surname, countyCode, municipalityCode,
                   postalAddress1, postalCode, city,
                   protectedPersonIndicator, testIndicator,
                   deregistrationReasonCode, deregistrationDate)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                data["personId"], scen, data.get("scenario"),
                data.get("givenName"), data.get("surname"),
                data.get("countyCode"), data.get("municipalityCode"),
                data.get("postalAddress1"), data.get("postalCode"),
                data.get("city"),
                1 if data.get("protectedPersonIndicator") else 0,
                1 if data.get("testIndicator", True) else 0,
                data.get("deregistrationReasonCode"),
                data.get("deregistrationDate"),
            ))
        return _ok({"personId": data["personId"], "scenario_name": scen}, 201)
    except sqlite3.IntegrityError:
        return _err(f"Person {data['personId']} finns redan i scenario '{scen}'", 409)


@admin.put("/persons/<person_id>")
def update_person(person_id):
    data = request.get_json(force=True)
    scen = _scen()
    with _connect() as conn:
        cur = conn.execute("""
            UPDATE persons SET
              scenario=?, givenName=?, surname=?,
              countyCode=?, municipalityCode=?,
              postalAddress1=?, postalCode=?, city=?,
              protectedPersonIndicator=?, testIndicator=?,
              deregistrationReasonCode=?, deregistrationDate=?
            WHERE personId = ? AND scenario_name = ?
        """, (
            data.get("scenario"),
            data.get("givenName"), data.get("surname"),
            data.get("countyCode"), data.get("municipalityCode"),
            data.get("postalAddress1"), data.get("postalCode"),
            data.get("city"),
            1 if data.get("protectedPersonIndicator") else 0,
            1 if data.get("testIndicator", True) else 0,
            data.get("deregistrationReasonCode"),
            data.get("deregistrationDate"),
            person_id, scen,
        ))
        if cur.rowcount == 0:
            return _err("Hittades inte", 404)
    return _ok({"updated": person_id, "scenario_name": scen})


@admin.delete("/persons/<person_id>")
def delete_person(person_id):
    scen = _scen()
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM persons WHERE personId = ? AND scenario_name = ?",
            (person_id, scen)
        )
        if cur.rowcount == 0:
            return _err("Hittades inte", 404)
    return _ok({"deleted": person_id, "scenario_name": scen})


# ---------------------------------------------------------------------------
# PATIENTS  (listingTypes ingår i bodyn)
# ---------------------------------------------------------------------------

@admin.get("/patients")
def list_patients():
    scen = _scen()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM patients WHERE scenario_name = ? ORDER BY personId",
            (scen,)
        ).fetchall()
        result = []
        for row in rows:
            p = dict(row)
            p["isInQueue"]     = bool(p["isInQueue"])
            p["isOutOfCounty"] = bool(p.get("isOutOfCounty", 0))
            lts = conn.execute(
                "SELECT code, doctorHsaId, careContactHsaId FROM listing_types "
                "WHERE personId = ? AND scenario_name = ?",
                (p["personId"], scen)
            ).fetchall()
            p["listingTypes"] = [_lt(r) for r in lts]
            result.append(p)
    return _ok(result)


@admin.get("/patients/<person_id>")
def get_patient(person_id):
    p = db.get_patient(person_id, _scen())
    if p is None:
        return _err("Hittades inte", 404)
    return _ok(p)


@admin.post("/patients")
def create_patient():
    data = request.get_json(force=True)
    if not data.get("personId"):
        return _err("personId krävs")
    scen = data.get("scenario_name", _scen())
    try:
        with _connect() as conn:
            conn.execute("""
                INSERT INTO patients
                  (personId, scenario_name, scenario, facilityHsaId,
                   isInQueue, isOutOfCounty, homeCountyCode)
                VALUES (?,?,?,?,?,?,?)
            """, (
                data["personId"], scen, data.get("scenario"),
                data.get("facilityHsaId"),
                1 if data.get("isInQueue") else 0,
                1 if data.get("isOutOfCounty") else 0,
                data.get("homeCountyCode"),
            ))
            _insert_listing_types(conn, data["personId"], scen,
                                  data.get("listingTypes", []))
        return _ok({"personId": data["personId"], "scenario_name": scen}, 201)
    except sqlite3.IntegrityError:
        return _err(f"Patient {data['personId']} finns redan i scenario '{scen}'", 409)


@admin.put("/patients/<person_id>")
def update_patient(person_id):
    data = request.get_json(force=True)
    scen = _scen()
    with _connect() as conn:
        cur = conn.execute("""
            UPDATE patients SET
              scenario=?, facilityHsaId=?,
              isInQueue=?, isOutOfCounty=?, homeCountyCode=?
            WHERE personId = ? AND scenario_name = ?
        """, (
            data.get("scenario"), data.get("facilityHsaId"),
            1 if data.get("isInQueue") else 0,
            1 if data.get("isOutOfCounty") else 0,
            data.get("homeCountyCode"),
            person_id, scen,
        ))
        if cur.rowcount == 0:
            return _err("Hittades inte", 404)
        if "listingTypes" in data:
            conn.execute(
                "DELETE FROM listing_types WHERE personId = ? AND scenario_name = ?",
                (person_id, scen)
            )
            _insert_listing_types(conn, person_id, scen, data["listingTypes"])
    return _ok({"updated": person_id, "scenario_name": scen})


@admin.delete("/patients/<person_id>")
def delete_patient(person_id):
    scen = _scen()
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM patients WHERE personId = ? AND scenario_name = ?",
            (person_id, scen)
        )
        conn.execute(
            "DELETE FROM listing_types WHERE personId = ? AND scenario_name = ?",
            (person_id, scen)
        )
        if cur.rowcount == 0:
            return _err("Hittades inte", 404)
    return _ok({"deleted": person_id, "scenario_name": scen})


# ---------------------------------------------------------------------------
# FACILITIES  (supportedListingTypes ingår i bodyn)
# ---------------------------------------------------------------------------

@admin.get("/facilities")
def list_facilities():
    return _ok(db.get_all_facilities())


@admin.get("/facilities/<hsa_id>")
def get_facility(hsa_id):
    fac = db.get_facility(hsa_id)
    if fac is None:
        return _err("Hittades inte", 404)
    return _ok(fac)


@admin.post("/facilities")
def create_facility():
    data = request.get_json(force=True)
    if not data.get("hsaId"):
        return _err("hsaId krävs")
    try:
        with _connect() as conn:
            conn.execute("""
                INSERT INTO facilities (hsaId, name, hasQueue, supportsHealthcarePersonnel)
                VALUES (?,?,?,?)
            """, (
                data["hsaId"], data.get("name"),
                1 if data.get("hasQueue") else 0,
                1 if data.get("supportsHealthcarePersonnel", True) else 0,
            ))
            for code in data.get("supportedListingTypes", []):
                conn.execute(
                    "INSERT OR IGNORE INTO facility_listing_types (hsaId, code) VALUES (?,?)",
                    (data["hsaId"], code)
                )
        return _ok({"hsaId": data["hsaId"]}, 201)
    except sqlite3.IntegrityError:
        return _err(f"Facility {data['hsaId']} finns redan", 409)


@admin.put("/facilities/<hsa_id>")
def update_facility(hsa_id):
    data = request.get_json(force=True)
    with _connect() as conn:
        cur = conn.execute("""
            UPDATE facilities SET name=?, hasQueue=?, supportsHealthcarePersonnel=?
            WHERE hsaId = ?
        """, (
            data.get("name"),
            1 if data.get("hasQueue") else 0,
            1 if data.get("supportsHealthcarePersonnel", True) else 0,
            hsa_id,
        ))
        if cur.rowcount == 0:
            return _err("Hittades inte", 404)
        if "supportedListingTypes" in data:
            conn.execute(
                "DELETE FROM facility_listing_types WHERE hsaId = ?", (hsa_id,)
            )
            for code in data["supportedListingTypes"]:
                conn.execute(
                    "INSERT INTO facility_listing_types (hsaId, code) VALUES (?,?)",
                    (hsa_id, code)
                )
    return _ok({"updated": hsa_id})


@admin.delete("/facilities/<hsa_id>")
def delete_facility(hsa_id):
    with _connect() as conn:
        conn.execute(
            "DELETE FROM facility_listing_types WHERE hsaId = ?", (hsa_id,)
        )
        cur = conn.execute(
            "DELETE FROM facilities WHERE hsaId = ?", (hsa_id,)
        )
        if cur.rowcount == 0:
            return _err("Hittades inte", 404)
    return _ok({"deleted": hsa_id})


# ---------------------------------------------------------------------------
# PERSONNEL
# ---------------------------------------------------------------------------

@admin.get("/personnel")
def list_personnel():
    return _ok(db.get_all_personnel())


@admin.get("/personnel/<hsa_id>")
def get_personnel_member(hsa_id):
    p = db.get_personnel_member(hsa_id)
    if p is None:
        return _err("Hittades inte", 404)
    return _ok(p)


@admin.post("/personnel")
def create_personnel():
    data = request.get_json(force=True)
    if not data.get("hsaId"):
        return _err("hsaId krävs")
    try:
        with _connect() as conn:
            conn.execute("""
                INSERT INTO personnel (hsaId, name, title, professionCode, facilityHsaId)
                VALUES (?,?,?,?,?)
            """, (
                data["hsaId"], data.get("name"), data.get("title"),
                data.get("professionCode"), data.get("facilityHsaId"),
            ))
        return _ok({"hsaId": data["hsaId"]}, 201)
    except sqlite3.IntegrityError:
        return _err(f"Personal {data['hsaId']} finns redan", 409)


@admin.put("/personnel/<hsa_id>")
def update_personnel(hsa_id):
    data = request.get_json(force=True)
    with _connect() as conn:
        cur = conn.execute("""
            UPDATE personnel SET name=?, title=?, professionCode=?, facilityHsaId=?
            WHERE hsaId = ?
        """, (
            data.get("name"), data.get("title"),
            data.get("professionCode"), data.get("facilityHsaId"),
            hsa_id,
        ))
        if cur.rowcount == 0:
            return _err("Hittades inte", 404)
    return _ok({"updated": hsa_id})


@admin.delete("/personnel/<hsa_id>")
def delete_personnel(hsa_id):
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM personnel WHERE hsaId = ?", (hsa_id,)
        )
        if cur.rowcount == 0:
            return _err("Hittades inte", 404)
    return _ok({"deleted": hsa_id})


# ---------------------------------------------------------------------------
# REBUILD DB
# ---------------------------------------------------------------------------

@admin.post("/rebuild-db")
def rebuild_db():
    import create_db
    try:
        create_db.main()
        return _ok({"status": "Databas återskapad från JSON-filer"})
    except Exception as e:
        return _err(str(e), 500)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _lt(row) -> dict:
    d: dict = {"code": row["code"]}
    if row["doctorHsaId"]:
        d["doctorHsaId"]      = row["doctorHsaId"]
    if row["careContactHsaId"]:
        d["careContactHsaId"] = row["careContactHsaId"]
    return d


def _insert_listing_types(conn, person_id: str, scen: str, listing_types: list):
    for lt in listing_types:
        conn.execute("""
            INSERT INTO listing_types (personId, scenario_name, code, doctorHsaId, careContactHsaId)
            VALUES (?,?,?,?,?)
        """, (
            person_id, scen, lt["code"],
            lt.get("doctorHsaId"), lt.get("careContactHsaId"),
        ))
