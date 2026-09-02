from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from .approval import ApprovalTicket


class GateDecision(str, Enum):
    SHADOW_ALLOW = "SHADOW_ALLOW"
    DENY = "DENY"


@dataclass(frozen=True)
class GateResult:
    decision: GateDecision
    execution_authorized: bool
    reason: str
    action_digest: str
    approved_digest: str | None = None
    ticket_id: str | None = None


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    """Deterministically serialize a proposed action for exact-action binding.

    v0.1 intentionally accepts JSON-compatible mappings only. It rejects floats
    because their cross-runtime canonical representation is easy to get subtly
    wrong and VERITAS should fail closed rather than normalize ambiguously.
    """

    def reject_floats(node: Any) -> None:
        if isinstance(node, float):
            raise ValueError("floats are not permitted in Agent Gate action envelopes")
        if isinstance(node, dict):
            for key, item in node.items():
                if not isinstance(key, str):
                    raise ValueError("action envelope keys must be strings")
                reject_floats(item)
        elif isinstance(node, (list, tuple)):
            for item in node:
                reject_floats(item)
        elif node is not None and not isinstance(node, (str, int, bool)):
            raise ValueError(f"unsupported action envelope value: {type(node).__name__}")

    reject_floats(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _digest_action(action: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(action)).hexdigest()


class AgentGate:
    """Non-executing VERITAS gate for binding approval to an exact agent action.

    This class has *no execution capability*. Every result fixes
    ``execution_authorized`` to False. ``SHADOW_ALLOW`` means only that the
    proposed action still matches the action captured at the shadow approval
    checkpoint and that its single-use ticket has not previously been consumed.
    """

    def __init__(self) -> None:
        self._consumed_ticket_ids: set[str] = set()

    def approve_shadow(self, action: Mapping[str, Any]) -> GateResult:
        """Legacy digest-only checkpoint retained for the initial v0.1 API."""
        digest = _digest_action(action)
        return GateResult(
            decision=GateDecision.SHADOW_ALLOW,
            execution_authorized=False,
            reason="exact action captured for shadow approval",
            action_digest=digest,
            approved_digest=digest,
        )

    def issue_ticket(self, action: Mapping[str, Any]) -> ApprovalTicket:
        """Create a fresh single-use ticket bound to the exact canonical action."""
        return ApprovalTicket.issue(_digest_action(action))

    def reevaluate(
        self,
        action: Mapping[str, Any],
        *,
        approved_digest: str,
    ) -> GateResult:
        """Legacy digest comparison. Prefer ``reevaluate_ticket`` for new callers."""
        current_digest = _digest_action(action)
        if current_digest != approved_digest:
            return GateResult(
                decision=GateDecision.DENY,
                execution_authorized=False,
                reason="action mutated after approval",
                action_digest=current_digest,
                approved_digest=approved_digest,
            )

        return GateResult(
            decision=GateDecision.SHADOW_ALLOW,
            execution_authorized=False,
            reason="action unchanged since approval",
            action_digest=current_digest,
            approved_digest=approved_digest,
        )

    def reevaluate_ticket(
        self,
        action: Mapping[str, Any],
        *,
        ticket: ApprovalTicket,
    ) -> GateResult:
        """Consume a valid ticket exactly once and fail closed on any mismatch."""
        current_digest = _digest_action(action)

        if not ticket.integrity_valid():
            return GateResult(
                decision=GateDecision.DENY,
                execution_authorized=False,
                reason="approval ticket integrity failure",
                action_digest=current_digest,
                approved_digest=ticket.action_digest,
                ticket_id=ticket.ticket_id,
            )

        if ticket.ticket_id in self._consumed_ticket_ids:
            return GateResult(
                decision=GateDecision.DENY,
                execution_authorized=False,
                reason="approval ticket replay detected",
                action_digest=current_digest,
                approved_digest=ticket.action_digest,
                ticket_id=ticket.ticket_id,
            )

        # Consume before returning either mismatch or success. A ticket is an
        # attempt-specific capability and must not become reusable after a deny.
        self._consumed_ticket_ids.add(ticket.ticket_id)

        if current_digest != ticket.action_digest:
            return GateResult(
                decision=GateDecision.DENY,
                execution_authorized=False,
                reason="action mutated after approval",
                action_digest=current_digest,
                approved_digest=ticket.action_digest,
                ticket_id=ticket.ticket_id,
            )

        return GateResult(
            decision=GateDecision.SHADOW_ALLOW,
            execution_authorized=False,
            reason="single-use approval ticket matched exact action",
            action_digest=current_digest,
            approved_digest=ticket.action_digest,
            ticket_id=ticket.ticket_id,
        )
