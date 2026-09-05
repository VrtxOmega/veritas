from agent_gate import AgentGate, ControlApproval, GateDecision, ReplayStore, digest_action


def approvals_for(action, pairs):
    digest = digest_action(action)
    return [ControlApproval.issue(control_id=control, approver_id=approver, action_digest=digest) for control, approver in pairs]


def write_action(target="workspace/README.md"):
    return {"type": "filesystem.write", "target": target, "parameters": {"content_sha256": "abc123"}}


def test_positive_control_two_distinct_bound_approvals_satisfy_contract():
    gate = AgentGate()
    action = write_action()
    approvals = approvals_for(action, [("scope", "alice"), ("change", "bob")])
    result, ticket = gate.evaluate_and_issue(action, approvals=approvals)
    assert result.decision is GateDecision.SHADOW_ALLOW
    assert result.execution_authorized is False
    assert ticket is not None


def test_same_approver_twice_does_not_satisfy_quorum():
    gate = AgentGate()
    action = write_action()
    approvals = approvals_for(action, [("scope", "alice"), ("change", "alice")])
    result, ticket = gate.evaluate_and_issue(action, approvals=approvals)
    assert result.decision is GateDecision.DENY
    assert result.reason == "insufficient distinct approvers"
    assert ticket is None


def test_duplicate_control_cannot_satisfy_required_control_count():
    gate = AgentGate()
    action = write_action()
    approvals = approvals_for(action, [("scope", "alice"), ("scope", "bob")])
    result, ticket = gate.evaluate_and_issue(action, approvals=approvals)
    assert result.decision is GateDecision.DENY
    assert result.reason == "duplicate control cannot satisfy quorum"
    assert ticket is None


def test_approval_bound_to_different_action_does_not_count():
    gate = AgentGate()
    action = write_action()
    other = write_action("workspace/OTHER.md")
    approvals = [
        ControlApproval.issue(control_id="scope", approver_id="alice", action_digest=digest_action(action)),
        ControlApproval.issue(control_id="change", approver_id="bob", action_digest=digest_action(other)),
    ]
    result, ticket = gate.evaluate_and_issue(action, approvals=approvals)
    assert result.decision is GateDecision.DENY
    assert result.reason == "approval bound to different action"
    assert ticket is None


def test_unknown_operation_fails_closed():
    gate = AgentGate()
    action = {"type": "filesystem.teleport", "target": "workspace/a", "parameters": {}}
    result, ticket = gate.evaluate_and_issue(action, approvals=[])
    assert result.decision is GateDecision.DENY
    assert ticket is None


def test_path_traversal_fails_closed():
    gate = AgentGate()
    action = write_action("workspace/../secrets.txt")
    approvals = approvals_for(action, [("scope", "alice"), ("change", "bob")])
    result, ticket = gate.evaluate_and_issue(action, approvals=approvals)
    assert result.decision is GateDecision.DENY
    assert ticket is None


def test_ticket_persists_replay_state_across_gate_instances(tmp_path):
    db = str(tmp_path / "replay.sqlite3")
    action = write_action()
    approvals = approvals_for(action, [("scope", "alice"), ("change", "bob")])
    first_gate = AgentGate(replay_store=ReplayStore(db))
    _, ticket = first_gate.evaluate_and_issue(action, approvals=approvals)
    assert ticket is not None
    first = first_gate.reevaluate_ticket(action, ticket=ticket)
    second_gate = AgentGate(replay_store=ReplayStore(db))
    replay = second_gate.reevaluate_ticket(action, ticket=ticket)
    assert first.decision is GateDecision.SHADOW_ALLOW
    assert replay.decision is GateDecision.DENY
    assert replay.reason == "approval ticket replay detected"


def test_mutating_approved_action_burns_ticket():
    gate = AgentGate()
    action = write_action()
    approvals = approvals_for(action, [("scope", "alice"), ("change", "bob")])
    _, ticket = gate.evaluate_and_issue(action, approvals=approvals)
    assert ticket is not None
    mutated = write_action("workspace/OTHER.md")
    mismatch = gate.reevaluate_ticket(mutated, ticket=ticket)
    retry = gate.reevaluate_ticket(action, ticket=ticket)
    assert mismatch.decision is GateDecision.DENY
    assert mismatch.reason == "action mutated after approval"
    assert retry.decision is GateDecision.DENY
    assert retry.reason == "approval ticket replay detected"
