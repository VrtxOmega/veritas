from dataclasses import replace

import pytest

from agent_gate import AgentGate, GateDecision


def test_unchanged_action_shadow_allows_but_never_authorizes_execution():
    gate = AgentGate()
    action = {
        "type": "filesystem.write",
        "target": "workspace/README.md",
        "parameters": {"content_sha256": "abc123"},
    }

    approved = gate.approve_shadow(action)
    result = gate.reevaluate(action, approved_digest=approved.action_digest)

    assert result.decision is GateDecision.SHADOW_ALLOW
    assert result.execution_authorized is False
    assert result.action_digest == approved.action_digest


def test_reordered_json_keys_preserve_exact_semantics():
    gate = AgentGate()
    original = {"type": "tool.call", "parameters": {"b": 2, "a": 1}}
    reordered = {"parameters": {"a": 1, "b": 2}, "type": "tool.call"}

    approved = gate.approve_shadow(original)
    result = gate.reevaluate(reordered, approved_digest=approved.action_digest)

    assert result.decision is GateDecision.SHADOW_ALLOW
    assert result.execution_authorized is False


def test_target_mutation_denies():
    gate = AgentGate()
    approved_action = {
        "type": "filesystem.delete",
        "target": "workspace/tmp.txt",
        "parameters": {},
    }
    mutated_action = {
        "type": "filesystem.delete",
        "target": "workspace/config.json",
        "parameters": {},
    }

    approved = gate.approve_shadow(approved_action)
    result = gate.reevaluate(mutated_action, approved_digest=approved.action_digest)

    assert result.decision is GateDecision.DENY
    assert result.execution_authorized is False
    assert result.reason == "action mutated after approval"


def test_parameter_mutation_denies():
    gate = AgentGate()
    approved_action = {
        "type": "shell.exec",
        "target": "local",
        "parameters": {"argv": ["pytest", "-q"]},
    }
    mutated_action = {
        "type": "shell.exec",
        "target": "local",
        "parameters": {"argv": ["pytest", "-q", "--disable-warnings"]},
    }

    approved = gate.approve_shadow(approved_action)
    result = gate.reevaluate(mutated_action, approved_digest=approved.action_digest)

    assert result.decision is GateDecision.DENY
    assert result.execution_authorized is False


def test_float_input_fails_closed():
    gate = AgentGate()

    with pytest.raises(ValueError, match="floats are not permitted"):
        gate.approve_shadow({"type": "tool.call", "parameters": {"threshold": 0.8}})


def test_ticket_is_single_use():
    gate = AgentGate()
    action = {"type": "shell.exec", "target": "local", "parameters": {"argv": ["pytest", "-q"]}}
    ticket = gate.issue_ticket(action)

    first = gate.reevaluate_ticket(action, ticket=ticket)
    replay = gate.reevaluate_ticket(action, ticket=ticket)

    assert first.decision is GateDecision.SHADOW_ALLOW
    assert first.execution_authorized is False
    assert replay.decision is GateDecision.DENY
    assert replay.reason == "approval ticket replay detected"
    assert replay.execution_authorized is False


def test_mutated_action_consumes_ticket_and_cannot_retry_original():
    gate = AgentGate()
    original = {"type": "filesystem.delete", "target": "workspace/tmp.txt", "parameters": {}}
    mutated = {"type": "filesystem.delete", "target": "workspace/config.json", "parameters": {}}
    ticket = gate.issue_ticket(original)

    mismatch = gate.reevaluate_ticket(mutated, ticket=ticket)
    retry = gate.reevaluate_ticket(original, ticket=ticket)

    assert mismatch.decision is GateDecision.DENY
    assert mismatch.reason == "action mutated after approval"
    assert retry.decision is GateDecision.DENY
    assert retry.reason == "approval ticket replay detected"


def test_ticket_action_digest_tampering_fails_integrity():
    gate = AgentGate()
    action = {"type": "tool.call", "target": "local", "parameters": {"name": "safe"}}
    ticket = gate.issue_ticket(action)
    tampered = replace(ticket, action_digest="0" * 64)

    result = gate.reevaluate_ticket(action, ticket=tampered)

    assert result.decision is GateDecision.DENY
    assert result.reason == "approval ticket integrity failure"
    assert result.execution_authorized is False


def test_ticket_nonce_tampering_fails_integrity():
    gate = AgentGate()
    action = {"type": "tool.call", "target": "local", "parameters": {"name": "safe"}}
    ticket = gate.issue_ticket(action)
    tampered = replace(ticket, nonce="00" * 32)

    result = gate.reevaluate_ticket(action, ticket=tampered)

    assert result.decision is GateDecision.DENY
    assert result.reason == "approval ticket integrity failure"
