"""The suppression list: who asked us to stop. Only salted hashes are stored, never the address itself.

Checked at approval and again at send (an organisation may object in between). Entries are kept
indefinitely, because an objection has to be honoured next time too.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel

from bluewatch.outreach.addresses import domain_of
from bluewatch.store import Store

KIND = "outreach_suppression"
_SALT = "bluewatch-suppression-v1:"

SuppressionReason = Literal["opt_out", "bounce", "manual"]


class SuppressionEntry(BaseModel):
    hash: str
    scope: Literal["address", "domain", "company"]
    reason: SuppressionReason
    created_at: datetime


def _hash(scope: str, value: str) -> str:
    return hashlib.sha256(f"{_SALT}{scope}:{value.strip().lower()}".encode("utf-8")).hexdigest()


def _keys(address: str | None, domain: str | None, company_id: str | None) -> list[tuple[str, str]]:
    keys = []
    if address:
        keys.append(("address", _hash("address", address)))
    domain = domain_of(domain or address)
    if domain:
        keys.append(("domain", _hash("domain", domain)))
    if company_id:
        keys.append(("company", _hash("company", company_id)))
    return keys


class Suppression:
    """Backed by the store, so a stop request survives restarts."""

    def __init__(self, store: Store) -> None:
        self.store = store

    def add(
        self,
        *,
        reason: SuppressionReason,
        address: str | None = None,
        domain: str | None = None,
        company_id: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        for scope, digest in _keys(address, domain, company_id):
            self.store.put(KIND, digest, SuppressionEntry(hash=digest, scope=scope, reason=reason, created_at=now))

    def matches(
        self, *, address: str | None = None, domain: str | None = None, company_id: str | None = None
    ) -> list[str]:
        """The scopes that are suppressed ('address', 'domain', 'company'); empty when none."""
        return [
            scope
            for scope, digest in _keys(address, domain, company_id)
            if self.store.get(KIND, digest, SuppressionEntry) is not None
        ]
