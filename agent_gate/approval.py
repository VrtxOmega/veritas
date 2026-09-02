from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping


def _ticket_digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ApprovalTicket:
    """Opaque, single-use shadow approval bound to one exact action.

    v0.1 tickets are local integrity objects, not cryptographic identity
    attestations. Signed approver identity/quorum is a later hardening layer.
    """

    ticket_id: str
    nonce: str
    action_digest: str
    issued_at: str
    binding_digest: str

    @classmethod
    def issue(cls, action_digest: str) -> "ApprovalTicket":
        ticket_id = secrets.token_hex(16)
        nonce = secrets.token_hex(32)
        issued_at = datetime.now(timezone.utc).isoformat()
        binding_digest = _ticket_digest(
            {
                "ticket_id": ticket_id,
                "nonce": nonce,
                "action_digest": action_digest,
                "issued_at": issued_at,
            }
        )
        return cls(
            ticket_id=ticket_id,
            nonce=nonce,
            action_digest=action_digest,
            issued_at=issued_at,
            binding_digest=binding_digest,
        )

    def integrity_valid(self) -> bool:
        expected = _ticket_digest(
            {
                "ticket_id": self.ticket_id,
                "nonce": self.nonce,
                "action_digest": self.action_digest,
                "issued_at": self.issued_at,
            }
        )
        return secrets.compare_digest(expected, self.binding_digest)
