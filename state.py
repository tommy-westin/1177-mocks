"""In-memory state for mock server. Survives only until restart."""

# Maps personId (extension string) -> list of listing dicts created via CreateListing.
# Each dict mirrors the patients.json structure for one listing type.
_created_listings: dict[str, list[dict]] = {}


def get_created_listings(person_id: str) -> list[dict] | None:
    """Return created listings for person, or None if never CreateListing'd."""
    return _created_listings.get(person_id)


def store_listing(person_id: str, listing: dict) -> None:
    """Store or replace the full listing state for a person."""
    _created_listings[person_id] = listing


def clear() -> None:
    _created_listings.clear()
