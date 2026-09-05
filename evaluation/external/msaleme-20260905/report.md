Agent Gate v0.1 evaluated. Clean run — I found nothing that fails your contract, and one
observation about verdict surface rather than enforcement.

**Target identity, checked before and after.** `256daeb85dae7ac004ae9893df858f58c87ec523`,
no tracked modifications, `agent_gate` imported from inside the specimen checkout
(`.../veritas/agent_gate/__init__.py`). Your author suite passes 17/17 as a setup check,
which I am recording as setup and not as evidence. Python 3.12, stdlib only for the
specimen itself.

**Method.** I re-implemented the hostile set from `AGENT_GATE_DEMONSTRATOR.md` rather
than adapting `tests/test_agent_gate_contracts.py`, so the cases exercise the contract
as documented rather than as you wrote it down in code. Eighteen cases: the positive
control, your eight pinned denials, and nine extension probes you had not pinned.

**Result: 17/18 matched the recorded expectation; the eighteenth is the observation below.**
The positive control allows. Every pinned denial denies. The eighteenth case does not return a
verdict at all — it raises — which is why the script reports it as "to inspect" rather than as a
match, and why I am reporting it as an observation rather than folding it into a clean count.

The allow/deny expectation for each case was encoded in the probe before execution. I inspected
the reason strings afterward; each matched the documented behavior.

Of the extension probes, the ones I thought most likely to find something:

- sibling-prefix confusion (`workspace-evil/x`) — denied, `target outside operation contract`;
- case variation (`Workspace/notes.txt`) — denied, same;
- dot-segment inside the namespace (`workspace/./notes.txt`) — allowed after normalization,
  consistent with the documented namespace rule;
- extra control beyond the required set — denied, `required control set mismatch`;
- absolute path, missing required parameter, unexpected parameter — all denied with the
  specific reason.

**The one I want to report positively.** Your canonical digest covers the whole envelope,
including a top-level key the contract never reads. I issued a ticket for an action
carrying `urgency: "low"`, mutated only that key, and the recheck denied with
`action mutated after approval` — not a replay artifact. That is broader binding than I
implement: my own equivalent names three fields explicitly, so an uncontracted field
would not have been covered. Yours is the better default.

**One observation, explicitly not a finding.** A float anywhere in the envelope raises
`ValueError("floats are not permitted...")` rather than returning a DENY verdict. No ticket
is issued, so the gate fails closed at this boundary. The integration surface is different,
though: the caller receives an exception rather than a DENY verdict, and a caller that
converts broad exceptions into logged skips could turn this boundary failure into a bypass.
A float can also arrive through ordinary serialization rather than hostile input. Nothing in
your contract promises otherwise and I am not calling it a defect — it is the kind of thing
worth knowing before an integrator makes that mistake for you.

**A correction on my side, since it bears on how much the run is worth.** My first pass
reported the digest-coverage case as denied for the wrong reason — my probe called
`reevaluate_ticket` twice, once for the boolean and once for the reason string, and burned
the ticket itself. The gate was right and my instrument was wrong. I re-ran it as a single
call before writing any of the above. Mentioning it because a clean result from an
instrument I had not checked would not have been worth sending you.

**On the eligibility question, since it is where I would otherwise have gone first.**
`contracts.py` states that this proves binding and distinctness semantics and not external
identity, and that a caller minting arbitrary approver IDs can impersonate them. I read
that as a declared boundary and did not probe it as a defect. Worth saying why I am being
careful: I shipped a quorum fix yesterday that checked distinct approver identities and
never checked whether either was *authorized*, so two arbitrary strings formed a quorum
(msaleme/red-team-blue-team-agent-fabric#512). Your v0.1 does not claim the property I got
wrong — it declines to claim it, in writing, which is the difference.

The probe is below so the clean result is inspectable rather than asserted. It checks
against the documented contract rather than your test file, so it should keep working as an
outside check on later revisions. Happy to open it as a PR against the evaluation kit if
that is more useful than a comment.

```python
"""Independent probe of VERITAS Agent Gate v0.1 @ 256daeb8.

Re-implemented from AGENT_GATE_DEMONSTRATOR.md rather than adapted from the
author's tests: the point is to exercise the claimed contract from outside it.
Reports observed vs expected per case. Non-executing target; nothing is run.
"""
from agent_gate import AgentGate, ControlApproval, digest_action

RESULTS = []
def check(name, expect_allow, fn):
    try:
        allowed, reason = fn()
    except Exception as e:
        RESULTS.append((name, "EXCEPTION", f"{type(e).__name__}: {e}", expect_allow, None)); return
    ok = (allowed == expect_allow)
    RESULTS.append((name, "MATCH" if ok else "MISMATCH", reason, expect_allow, allowed))

def action(target="workspace/notes.txt", typ="filesystem.write", params=None, **extra):
    a = {"type": typ, "target": target, "parameters": params if params is not None else {"content_sha256": "a"*64}}
    a.update(extra); return a

def approvals_for(a, pairs):
    d = digest_action(a)
    return [ControlApproval.issue(control_id=c, approver_id=p, action_digest=d) for c, p in pairs]

def run(a, pairs):
    g = AgentGate()
    res, ticket = g.evaluate_and_issue(a, approvals=approvals_for(a, pairs))
    return (res.decision.name == "SHADOW_ALLOW", res.reason)

GOOD = [("scope", "alice"), ("change", "bob")]

# --- positive control (must ALLOW) -----------------------------------------
check("POSITIVE CONTROL: two distinct approvers, exact controls, bound", True,
      lambda: run(action(), GOOD))

# --- their pinned hostile set (must DENY) ----------------------------------
check("two copies of one control, count still two", False,
      lambda: run(action(), [("scope", "alice"), ("scope", "bob")]))
check("correct two controls, same approver identity", False,
      lambda: run(action(), [("scope", "alice"), ("change", "alice")]))
check("unknown operation type", False,
      lambda: run(action(typ="filesystem.chmod"), GOOD))
check("path traversal outside namespace", False,
      lambda: run(action(target="workspace/../../etc/passwd"), GOOD))

def bound_to_different_action():
    a, other = action(), action(target="workspace/other.txt")
    d = digest_action(other)
    ap = [ControlApproval.issue(control_id=c, approver_id=p, action_digest=d) for c, p in GOOD]
    res, _ = AgentGate().evaluate_and_issue(a, approvals=ap)
    return (res.decision.name == "SHADOW_ALLOW", res.reason)
check("approval bound to a different action", False, bound_to_different_action)

def mutate_after_ticket():
    g, a = AgentGate(), action()
    res, t = g.evaluate_and_issue(a, approvals=approvals_for(a, GOOD))
    r = g.reevaluate_ticket(action(target="workspace/evil.txt"), ticket=t)
    return (r.decision.name == "SHADOW_ALLOW", r.reason)
check("target mutation after ticket issuance", False, mutate_after_ticket)

def replay_after_success():
    g, a = AgentGate(), action()
    res, t = g.evaluate_and_issue(a, approvals=approvals_for(a, GOOD))
    g.reevaluate_ticket(a, ticket=t)
    r = g.reevaluate_ticket(a, ticket=t)
    return (r.decision.name == "SHADOW_ALLOW", r.reason)
check("ticket replay after a successful use", False, replay_after_success)

def retry_original_after_burn():
    g, a = AgentGate(), action()
    res, t = g.evaluate_and_issue(a, approvals=approvals_for(a, GOOD))
    g.reevaluate_ticket(action(target="workspace/evil.txt"), ticket=t)   # burns
    r = g.reevaluate_ticket(a, ticket=t)
    return (r.decision.name == "SHADOW_ALLOW", r.reason)
check("retry of original action after a mutation attempt burned the ticket", False,
      retry_original_after_burn)

# --- cases NOT in their pinned set (extension probes) -----------------------
check("EXT: extra control beyond the required set", False,
      lambda: run(action(), GOOD + [("audit", "carol")]))
check("EXT: missing required parameter", False,
      lambda: run(action(params={}), GOOD))
check("EXT: unexpected parameter", False,
      lambda: run(action(params={"content_sha256": "a"*64, "mode": "0777"}), GOOD))
check("EXT: absolute target path", False, lambda: run(action(target="/etc/passwd"), GOOD))
check("EXT: dot-segment inside namespace normalizes and is allowed", True,
      lambda: run(action(target="workspace/./notes.txt"), GOOD))
check("EXT: sibling-prefix confusion (workspace-evil)", False,
      lambda: run(action(target="workspace-evil/x"), GOOD))
check("EXT: case variation of the namespace", False,
      lambda: run(action(target="Workspace/notes.txt"), GOOD))
def uncontracted_key_is_digest_covered():
    g, a = AgentGate(), action(urgency="low")
    res, t = g.evaluate_and_issue(a, approvals=approvals_for(a, GOOD))
    r = g.reevaluate_ticket(action(urgency="high"), ticket=t)   # single call: do not burn twice
    return (r.decision.name == "SHADOW_ALLOW", r.reason)
check("EXT: uncontracted top-level key is digest-covered (mutation denied)", False,
      uncontracted_key_is_digest_covered)
check("EXT: float in envelope is rejected", False,
      lambda: run(action(params={"content_sha256": "a"*64}, weight=1.5), GOOD))

w = max(len(r[0]) for r in RESULTS)
print(f"{'CASE'.ljust(w)}  {'RESULT':9}  EXPECT  GOT   REASON")
for name, verdict, reason, exp, got in RESULTS:
    e = "ALLOW" if exp else "DENY "
    g = "-" if got is None else ("ALLOW" if got else "DENY ")
    print(f"{name.ljust(w)}  {verdict:9}  {e}   {g}  {reason[:64]}")
mis = [r for r in RESULTS if r[1] != "MATCH"]
print(f"\n{len(RESULTS)-len(mis)}/{len(RESULTS)} matched expectation; {len(mis)} to inspect")
```
