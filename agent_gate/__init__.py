"""VERITAS Agent Gate shadow-mode package."""

from .approval import ApprovalTicket
from .gate import AgentGate, GateDecision, GateResult

__all__ = ["AgentGate", "ApprovalTicket", "GateDecision", "GateResult"]
