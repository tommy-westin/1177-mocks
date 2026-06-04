#!/usr/bin/env python3
"""
Migrera JSON-filer till SQLite.

Kör en gång för att skapa config/data.db från befintliga JSON-filer.
Kan köras om för att återskapa databasen (befintlig data skrivs över).

Användning:
  python create_db.py
"""
import glob
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

import db as _db


def main():
    if os.path.exists(_db.DB_PATH):
        os.remove(_db.DB_PATH)
        print(f"Tog bort befintlig databas: {_db.DB_PATH}")

    _db.create_schema()
    print(f"Skapade schema i: {_db.DB_PATH}\n")

    conn = sqlite3.connect(_db.DB_PATH)
    conn.row_factory = sqlite3.Row

    _migrate_persons(conn)
    _migrate_patients(conn)
    _migrate_facilities(conn)
    _migrate_personnel(conn)

    conn.commit()
    conn.close()
    print(f"\nKlar! Databas: {_db.DB_PATH}")
    print("Öppna med t.ex. DB Browser for SQLite för att redigera data.")


def _scenario_from_filename(base: str, path: str) -> str:
    """'patients_massavflyttning.json' → 'massavflyttning', 'patients.json' → 'default'"""
    stem   = os.path.basename(path).replace(".json", "")
    suffix = stem[len(base):]
    return suffix.lstrip("_") or "default"


def _migrate_persons(conn: sqlite3.Connection):
    pattern = os.path.join(ROOT, "config", "person", "persons*.json")
    for path in sorted(glob.glob(pattern)):
        scenario_name = _scenario_from_filename("persons", path)
        with open(path, encoding="utf-8") as f:
            persons = json.load(f)
        for p in persons:
            conn.execute("""
                INSERT OR REPLACE INTO persons
                  (personId, scenario_name, scenario,
                   givenName, surname,
                   countyCode, municipalityCode,
                   postalAddress1, postalCode, city,
                   protectedPersonIndicator, testIndicator,
                   deregistrationReasonCode, deregistrationDate)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                p["personId"], scenario_name, p.get("scenario"),
                p.get("givenName"), p.get("surname"),
                p.get("countyCode"), p.get("municipalityCode"),
                p.get("postalAddress1"),
                str(p["postalCode"]) if p.get("postalCode") is not None else None,
                p.get("city"),
                1 if p.get("protectedPersonIndicator") else 0,
                1 if p.get("testIndicator", True) else 0,
                p.get("deregistrationReasonCode"),
                p.get("deregistrationDate"),
            ))
        print(f"  persons [{scenario_name:20s}]: {len(persons)} rader  ← {os.path.basename(path)}")


def _migrate_patients(conn: sqlite3.Connection):
    pattern = os.path.join(ROOT, "config", "carelisting", "patients*.json")
    for path in sorted(glob.glob(pattern)):
        scenario_name = _scenario_from_filename("patients", path)
        with open(path, encoding="utf-8") as f:
            patients = json.load(f)
        for p in patients:
            conn.execute("""
                INSERT OR REPLACE INTO patients
                  (personId, scenario_name, scenario,
                   facilityHsaId, isInQueue, isOutOfCounty, homeCountyCode)
                VALUES (?,?,?,?,?,?,?)
            """, (
                p["personId"], scenario_name, p.get("scenario"),
                p.get("facilityHsaId"),
                1 if p.get("isInQueue") else 0,
                1 if p.get("isOutOfCounty") else 0,
                p.get("homeCountyCode"),
            ))
            for lt in p.get("listingTypes", []):
                conn.execute("""
                    INSERT INTO listing_types
                      (personId, scenario_name, code, doctorHsaId, careContactHsaId)
                    VALUES (?,?,?,?,?)
                """, (
                    p["personId"], scenario_name, lt["code"],
                    lt.get("doctorHsaId"), lt.get("careContactHsaId"),
                ))
        print(f"  patients [{scenario_name:20s}]: {len(patients)} rader  ← {os.path.basename(path)}")


def _migrate_facilities(conn: sqlite3.Connection):
    path = os.path.join(ROOT, "config", "carelisting", "facilities.json")
    with open(path, encoding="utf-8") as f:
        facilities = json.load(f)
    for fac in facilities:
        conn.execute("""
            INSERT OR REPLACE INTO facilities
              (hsaId, name, hasQueue, supportsHealthcarePersonnel)
            VALUES (?,?,?,?)
        """, (
            fac["hsaId"], fac["name"],
            1 if fac.get("hasQueue") else 0,
            1 if fac.get("supportsHealthcarePersonnel", True) else 0,
        ))
        for code in fac.get("supportedListingTypes", []):
            conn.execute(
                "INSERT OR REPLACE INTO facility_listing_types (hsaId, code) VALUES (?,?)",
                (fac["hsaId"], code),
            )
    print(f"  facilities:                      {len(facilities)} rader")


def _migrate_personnel(conn: sqlite3.Connection):
    path = os.path.join(ROOT, "config", "carelisting", "personnel.json")
    with open(path, encoding="utf-8") as f:
        personnel = json.load(f)
    for p in personnel:
        conn.execute("""
            INSERT OR REPLACE INTO personnel
              (hsaId, name, title, professionCode, facilityHsaId)
            VALUES (?,?,?,?,?)
        """, (p["hsaId"], p["name"], p.get("title"),
              p.get("professionCode"), p.get("facilityHsaId")))
    print(f"  personnel:                       {len(personnel)} rader")


if __name__ == "__main__":
    main()
