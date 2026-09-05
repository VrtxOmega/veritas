from __future__ import annotations

import hashlib
import json
import posixpath
import secrets
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


def _stable_digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ControlApproval:
    """Local demonstrator approval bound to one control and one exact action.

    This proves binding/distinctness semantics, not external identity. A caller that
    can mint arbitrary approver IDs can impersonate them; signed identity is outside
    the v0.1 demonstrator boundary.
    """

    control_id: str
    approver_id: str
    action_digest: str
    nonce: str
    binding_digest: str

    @classmethod
    def issue(cls, *, control_id: str, approver_id: str, action_digest: str, nonce: str | None = None) -> "ControlApproval":
        nonce = nonce or secrets.token_hex(16)
        payload = {"control_id": control_id, "approver_id": approver_id, "action_digest": action_digest, "nonce": nonce}
        return cls(binding_digest=_stable_digest(payload), **payload)

    def integrity_valid(self) -> bool:
        expected = _stable_digest({"control_id": self.control_id, "approver_id": self.approver_id, "action_digest": self.action_digest, "nonce": self.nonce})
        return secrets.compare_digest(expected, self.binding_digest)


@dataclass(frozen=True)
class OperationContract:
    operation_type: str
    target_prefix: str
    required_parameters: frozenset[str]
    allowed_parameters: frozenset[str]
    required_controls: frozenset[str]
    min_distinct_approvers: int
    destructive: bool = False


@dataclass(frozen=True)
class ContractResult:
    eligible: bool
    reason: str


class OperationRegistry:
    """Fail-closed registry for the small public Agent Gate demonstrator."""

    def __init__(self, contracts: Sequence[OperationContract] | None = None) -> None:
        contracts = contracts or default_contracts()
        self._contracts = {contract.operation_type: contract for contract in contracts}
        if len(self._contracts) != len(contracts):
            raise ValueError("duplicate operation type")

    def validate(self, action: Mapping[str, Any], *, action_digest: str, approvals: Sequence[ControlApproval]) -> ContractResult:
        operation_type = action.get("type")
        if not isinstance(operation_type, str) or operation_type not in self._contracts:
            return ContractResult(False, "unknown operation type")
        contract = self._contracts[operation_type]

        target = action.get("target")
        if not isinstance(target, str):
            return ContractResult(False, "target must be a string")
        normalized = posixpath.normpath(target)
        if target.startswith("/") or normalized == ".." or normalized.startswith("../"):
            return ContractResult(False, "target escapes allowed relative namespace")
        prefix = contract.target_prefix.rstrip("/")
        if normalized != prefix and not normalized.startswith(prefix + "/"):
            return ContractResult(False, "target outside operation contract")

        parameters = action.get("parameters")
        if not isinstance(parameters, Mapping):
            return ContractResult(False, "parameters must be an object")
        keys = set(parameters.keys())
        if not all(isinstance(key, str) for key in keys):
            return ContractResult(False, "parameter keys must be strings")
        if not contract.required_parameters.issubset(keys):
            return ContractResult(False, "required parameter missing")
        if not keys.issubset(contract.allowed_parameters):
            return ContractResult(False, "unexpected parameter")

        if any(not approval.integrity_valid() for approval in approvals):
            return ContractResult(False, "approval integrity failure")
        if any(approval.action_digest != action_digest for approval in approvals):
            return ContractResult(False, "approval bound to different action")

        control_ids = [approval.control_id for approval in approvals]
        if len(control_ids) != len(set(control_ids)):
            return ContractResult(False, "duplicate control cannot satisfy quorum")
        if set(control_ids) != set(contract.required_controls):
            return ContractResult(False, "required control set mismatch")

        approver_ids = [approval.approver_id for approval in approvals]
        if len(set(approver_ids)) < contract.min_distinct_approvers:
            return ContractResult(False, "insufficient distinct approvers")

        return ContractResult(True, "typed operation and distinct bound controls satisfied")


def default_contracts() -> tuple[OperationContract, ...]:
    return (
        OperationContract("filesystem.read", "workspace", frozenset(), frozenset(), frozenset({"scope"}), 1),
        OperationContract("filesystem.write", "workspace", frozenset({"content_sha256"}), frozenset({"content_sha256"}), frozenset({"scope", "change"}), 2),
        OperationContract("filesystem.delete", "workspace", frozenset(), frozenset(), frozenset({"scope", "destructive"}), 2, True),
        OperationContract("shell.exec", "local", frozenset({"argv"}), frozenset({"argv"}), frozenset({"scope", "execution"}), 2),
        OperationContract("tool.call", "local", frozenset({"name"}), frozenset({"name", "arguments"}), frozenset({"scope", "tool"}), 2),
    )
