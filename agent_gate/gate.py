from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from .approval import ApprovalTicket
from .contracts import ControlApproval, OperationRegistry
from .replay import ReplayStore


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
    """Deterministically serialize an action, rejecting ambiguous values."""
    def reject_unsafe(node: Any) -> None:
        if isinstance(node, float):
            raise ValueError("floats are not permitted in Agent Gate action envelopes")
        if isinstance(node, int) and not isinstance(node, bool) and abs(node) > 9007199254740991:
            raise ValueError("integers outside the interoperable JSON safe range are not permitted")
        if isinstance(node, dict):
            for key, item in node.items():
                if not isinstance(key, str):
                    raise ValueError("action envelope keys must be strings")
                reject_unsafe(item)
        elif isinstance(node, (list, tuple)):
            for item in node:
                reject_unsafe(item)
        elif node is not None and not isinstance(node, (str, int, bool)):
            raise ValueError(f"unsupported action envelope value: {type(node).__name__}")

    reject_unsafe(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest_action(action: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(action)).hexdigest()


_digest_action = digest_action


class AgentGate:
    """Non-executing VERITAS gate for exact-action, approval and contract checks.

    This class has no execution capability. ``SHADOW_ALLOW`` means only that the
    demonstrator's checks passed; every result fixes ``execution_authorized`` to
    False.
    """

    def __init__(self, registry: OperationRegistry | None = None, replay_store: ReplayStore | None = None) -> None:
        self.registry = registry or OperationRegistry()
        self.replay_store = replay_store or ReplayStore()

    def approve_shadow(self, action: Mapping[str, Any]) -> GateResult:
        """Legacy digest-only checkpoint; not a contract-qualified approval."""
        digest = digest_action(action)
        return GateResult(GateDecision.SHADOW_ALLOW, False, "exact action captured for shadow approval", digest, digest)

    def issue_ticket(self, action: Mapping[str, Any]) -> ApprovalTicket:
        """Legacy ticket minting retained for compatibility; prefer evaluate_and_issue."""
        return ApprovalTicket.issue(digest_action(action))

    def evaluate_and_issue(self, action: Mapping[str, Any], *, approvals: Sequence[ControlApproval]) -> tuple[GateResult, ApprovalTicket | None]:
        """Validate a typed operation and exact distinct controls before ticketing."""
        digest = digest_action(action)
        contract = self.registry.validate(action, action_digest=digest, approvals=approvals)
        if not contract.eligible:
            return GateResult(GateDecision.DENY, False, contract.reason, digest), None
        ticket = ApprovalTicket.issue(digest)
        return GateResult(GateDecision.SHADOW_ALLOW, False, contract.reason, digest, digest, ticket.ticket_id), ticket

    def reevaluate(self, action: Mapping[str, Any], *, approved_digest: str) -> GateResult:
        current_digest = digest_action(action)
        if current_digest != approved_digest:
            return GateResult(GateDecision.DENY, False, "action mutated after approval", current_digest, approved_digest)
        return GateResult(GateDecision.SHADOW_ALLOW, False, "action unchanged since approval", current_digest, approved_digest)

    def reevaluate_ticket(self, action: Mapping[str, Any], *, ticket: ApprovalTicket) -> GateResult:
        """Atomically consume a valid ticket once and fail closed on mismatch."""
        current_digest = digest_action(action)
        if not ticket.integrity_valid():
            return GateResult(GateDecision.DENY, False, "approval ticket integrity failure", current_digest, ticket.action_digest, ticket.ticket_id)

        # Consume before checking action equality. A mutation probe burns the ticket,
        # so it cannot be retried later against the originally approved action.
        if not self.replay_store.consume_once(ticket.ticket_id):
            return GateResult(GateDecision.DENY, False, "approval ticket replay detected", current_digest, ticket.action_digest, ticket.ticket_id)
        if current_digest != ticket.action_digest:
            return GateResult(GateDecision.DENY, False, "action mutated after approval", current_digest, ticket.action_digest, ticket.ticket_id)
        return GateResult(GateDecision.SHADOW_ALLOW, False, "single-use approval ticket matched exact action", current_digest, ticket.action_digest, ticket.ticket_id)
