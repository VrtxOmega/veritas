"""VERITAS Agent Gate shadow-mode package."""

from .approval import ApprovalTicket
from .contracts import ControlApproval, ContractResult, OperationContract, OperationRegistry
from .gate import AgentGate, GateDecision, GateResult, digest_action
from .replay import ReplayStore

__all__ = [
    "AgentGate",
    "ApprovalTicket",
    "ControlApproval",
    "ContractResult",
    "GateDecision",
    "GateResult",
    "OperationContract",
    "OperationRegistry",
    "ReplayStore",
    "digest_action",
]
