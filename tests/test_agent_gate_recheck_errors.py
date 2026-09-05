"""Project-side regressions for exceptions before replay consumption."""
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from unittest.mock import patch

import pytest

from agent_gate import AgentGate, ControlApproval, GateDecision, ReplayStore, digest_action
import agent_gate


def action():
    return {"type": "filesystem.write", "target": "workspace/notes.txt",
            "parameters": {"content_sha256": "a" * 64}}


def issue(gate, value):
    approvals = [ControlApproval.issue(control_id=c, approver_id=p, action_digest=digest_action(value))
                 for c, p in [("scope", "alice"), ("change", "bob")]]
    result, ticket = gate.evaluate_and_issue(value, approvals=approvals)
    assert result.decision is GateDecision.SHADOW_ALLOW
    assert result.execution_authorized is False
    assert ticket is not None
    return ticket


@pytest.fixture(params=["memory", "file"])
def gate(request, tmp_path):
    store = ReplayStore(":memory:" if request.param == "memory" else str(tmp_path / "replay.sqlite3"))
    try:
        yield AgentGate(replay_store=store)
    finally:
        store._db.close()


def malformed(value, kind):
    result = dict(value)
    values = {"float": 1.5, "nested_float": [1, {"weight": 1.5}],
              "unsafe_integer": 2 ** 53, "unsupported_set": {1},
              "unicode_surrogate": "\ud800", "nan": float("nan")}
    if kind == "non_string_key":
        result[1] = "not a string key"
    elif kind == "cycle":
        result["cycle"] = result
    else:
        result["extra"] = values[kind]
    return result


@pytest.mark.parametrize("kind", ["float", "nested_float", "unsafe_integer", "unsupported_set",
                                  "unicode_surrogate", "nan", "non_string_key", "cycle"])
def test_malformed_recheck_burns_valid_ticket(gate, kind):
    value = action()
    ticket = issue(gate, value)
    with pytest.raises((ValueError, RecursionError)):
        gate.reevaluate_ticket(malformed(value, kind), ticket=ticket)
    retry = gate.reevaluate_ticket(value, ticket=ticket)
    assert retry.decision is GateDecision.DENY
    assert retry.reason == "approval ticket replay detected"
    assert retry.execution_authorized is False


def test_positive_recheck_still_allows_once(gate):
    value = action()
    ticket = issue(gate, value)
    first = gate.reevaluate_ticket(value, ticket=ticket)
    second = gate.reevaluate_ticket(value, ticket=ticket)
    assert first.decision is GateDecision.SHADOW_ALLOW
    assert second.decision is GateDecision.DENY
    assert first.execution_authorized is False and second.execution_authorized is False


def test_invalid_ticket_cannot_burn_another_ticket_id(gate):
    value = action()
    ticket = issue(gate, value)
    invalid = replace(ticket, nonce="invalid nonce without rebinding")
    with pytest.raises(ValueError, match="floats are not permitted"):
        gate.reevaluate_ticket(malformed(value, "float"), ticket=invalid)
    result = gate.reevaluate_ticket(value, ticket=ticket)
    assert result.decision is GateDecision.SHADOW_ALLOW
    assert result.execution_authorized is False


def test_unexpected_digest_exception_is_not_swallowed_or_reusable(gate):
    value = action()
    ticket = issue(gate, value)
    with patch("agent_gate.gate.digest_action", side_effect=RuntimeError("injected serializer failure")):
        with pytest.raises(RuntimeError, match="injected serializer failure"):
            gate.reevaluate_ticket(value, ticket=ticket)
    assert gate.reevaluate_ticket(value, ticket=ticket).decision is GateDecision.DENY


def test_storage_failure_does_not_turn_invalid_input_into_allow(gate):
    value = action()
    ticket = issue(gate, value)
    with patch.object(gate.replay_store, "consume_once", side_effect=sqlite3.OperationalError("injected unavailable store")) as consume:
        with pytest.raises(sqlite3.OperationalError, match="injected unavailable store"):
            gate.reevaluate_ticket(malformed(value, "float"), ticket=ticket)
        consume.assert_called_once_with(ticket.ticket_id)
    # A failed store commit is not evidence of durable consumption.


def test_burn_survives_a_new_process(tmp_path):
    database = str(tmp_path / "persistent.sqlite3")
    store = ReplayStore(database)
    gate = AgentGate(replay_store=store)
    value = action()
    ticket = issue(gate, value)
    try:
        with pytest.raises(ValueError):
            gate.reevaluate_ticket(malformed(value, "float"), ticket=ticket)
    finally:
        store._db.close()
    child = """import json, sys
from agent_gate import AgentGate, ApprovalTicket, ReplayStore
store = ReplayStore(sys.argv[1])
try:
    result = AgentGate(replay_store=store).reevaluate_ticket(json.loads(sys.argv[2]), ticket=ApprovalTicket(**json.loads(sys.argv[3])))
    print(json.dumps([result.decision.value, result.execution_authorized, result.reason]))
finally:
    store._db.close()
"""
    env = dict(os.environ, PYTHONPATH=str(Path(agent_gate.__file__).resolve().parent.parent))
    result = subprocess.run([sys.executable, "-B", "-c", child, database, json.dumps(value), json.dumps(asdict(ticket))],
                            env=env, capture_output=True, text=True, timeout=30, check=True)
    assert json.loads(result.stdout) == ["DENY", False, "approval ticket replay detected"]
