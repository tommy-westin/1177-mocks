"""
GetPersonsForProfileUnrestricted 5.0 — thin wrapper around the regular handler.

The Unrestricted variant uses a different namespace but identical logic.
In production it bypasses sekretessmarkering filtering; in this mock both
variants return the same data (the protected-person logic lives in the
shared handler).
"""
from .get_persons_for_profile import handle as _handle


def handle(raw_xml: bytes) -> bytes:
    return _handle(raw_xml, operation="GetPersonsForProfileUnrestricted")
