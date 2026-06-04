"""In-memory store for async file orders (getPersonsByFile / GetFilesForOrderId)."""
import random
import threading
import uuid
from datetime import datetime, timezone

_store: dict[str, dict] = {}   # orderId  → {guid, zip_bytes}
_guids: dict[str, str]  = {}   # guid     → orderId
_lock = threading.Lock()


def create(zip_bytes: bytes) -> tuple[str, str]:
    order_id = _new_order_id()
    guid     = str(uuid.uuid4())
    with _lock:
        _store[order_id] = {"guid": guid, "zip_bytes": zip_bytes}
        _guids[guid]     = order_id
    return order_id, guid


def get_by_order_id(order_id: str) -> dict | None:
    return _store.get(order_id)


def get_zip_by_guid(guid: str) -> bytes | None:
    order_id = _guids.get(guid)
    if not order_id:
        return None
    order = _store.get(order_id)
    return order["zip_bytes"] if order else None


def _new_order_id() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.strftime('%m%d')}-TO{random.randint(10, 99)}-{random.randint(10_000_000, 99_999_999)}"
