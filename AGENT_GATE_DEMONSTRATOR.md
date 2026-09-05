# VERITAS Agent Gate v0.1 — Shadow-Mode Demonstrator

Agent Gate is a **non-executing** demonstrator for pre-action assurance. It does not authorize or execute tools, shell commands, filesystem changes, network calls, or other agent actions. Every result fixes `execution_authorized` to `false`.

## Falsifiable contract

A contract-qualified `SHADOW_ALLOW` requires all of the following:

1. the operation type exists in the typed registry;
2. the target stays inside that operation's allowed relative namespace;
3. required parameters are present and unexpected parameters are absent;
4. every presented control approval has intact local binding data;
5. every approval is bound to the exact canonical action digest being evaluated;
6. the presented control IDs are the **exact distinct required-control set**, not merely the correct count;
7. the required number of **distinct approver IDs** is present;
8. the single-use ticket is intact, unused, and still bound to the exact action at pre-execution recheck.

A failed ticket recheck burns the ticket. With a filesystem-backed `ReplayStore`, replay state survives a new `AgentGate` instance/process.

## Acceptance controls

The demonstrator deliberately includes both positive and negative controls. A useful evaluator must be capable of observing a legitimate allow as well as the intended denials.

For `filesystem.write`, the positive control is:

- action: `filesystem.write` under `workspace/` with `content_sha256`;
- controls: exactly `scope` and `change`;
- approvers: two distinct IDs;
- both approvals bound to the exact action.

The hostile regression set requires denial for:

- two copies of one control even when the count is two;
- the correct two controls supplied by the same approver identity;
- an approval bound to a different action;
- target mutation after ticket issuance;
- ticket replay after a successful use;
- retry of the original action after a mutated-action attempt burns the ticket;
- unknown operation type;
- path traversal outside the allowed namespace.

These cases are pinned in `tests/test_agent_gate_contracts.py`.

## External harness surface

The stable Python surface for v0.1 is:

```python
from agent_gate import AgentGate, ControlApproval, ReplayStore, digest_action
```

Use `digest_action(action)` to bind approvals, `AgentGate.evaluate_and_issue(...)` for typed-control evaluation and ticket issuance, and `AgentGate.reevaluate_ticket(...)` for the immediate pre-execution shadow recheck.

An external harness is encouraged to replace or mutate any field, duplicate identities/controls, cross-bind approvals, replay tickets, supply unknown operations, and attempt namespace traversal. **A clean run is meaningful only if the harness also demonstrates that it can make at least one acceptance control pass and at least one deliberately broken semantic control fail.**

## Explicit non-claims

v0.1 does **not** establish:

- authenticated approver identity or signatures;
- resistance to an attacker who can mint arbitrary local `ControlApproval` objects;
- external policy-engine enforcement;
- factual truth of evidence;
- production safety or security certification;
- network/distributed replay safety beyond the configured SQLite store;
- execution authority.

`ControlApproval` uses a local digest to make binding semantics falsifiable; it is not an identity attestation. Signed identities, issuer trust, separation of duty, freshness, and external policy/evidence binding are later hardening layers.
