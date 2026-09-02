from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


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
    proposed action still matches the action that passed the shadow approval
    checkpoint.
    """

    def approve_shadow(self, action: Mapping[str, Any]) -> GateResult:
        digest = _digest_action(action)
        return GateResult(
            decision=GateDecision.SHADOW_ALLOW,
            execution_authorized=False,
            reason="exact action captured for shadow approval",
            action_digest=digest,
            approved_digest=digest,
        )

    def reevaluate(
        self,
        action: Mapping[str, Any],
        *,
        approved_digest: str,
    ) -> GateResult:
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
