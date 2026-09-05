# Evaluating VERITAS Agent Gate v0.1

This package is for independent evaluation of the frozen Agent Gate v0.1 specimen.

## Immutable target

Evaluate this exact commit:

`256daeb85dae7ac004ae9893df858f58c87ec523`

Do not substitute a moving branch for the target under test. If a later commit is evaluated, report it as a different target.

The implementation under evaluation is intentionally non-executing. Every result keeps `execution_authorized = false`.

## Fresh-clone setup and package validation

Prerequisites: Git, Python 3.12 with `venv` and `pip`, and network access to GitHub and PyPI for setup. Agent Gate itself uses the Python standard library (including SQLite); package validation requires `jsonschema`, and the author regression suite requires `pytest`. No API keys or external services are required for these checks.

Keep the evaluator package and frozen specimen in separate sibling checkouts: the frozen commit predates `evaluation/`. The kit can receive documentation/tooling fixes; record its full commit separately from the immutable target. From an empty working directory:

```text
git clone https://github.com/VrtxOmega/veritas.git veritas-evaluation-kit
git -C veritas-evaluation-kit checkout --detach
git -C veritas-evaluation-kit rev-parse HEAD
git clone https://github.com/VrtxOmega/veritas.git veritas-v0.1
git -C veritas-v0.1 checkout --detach 256daeb85dae7ac004ae9893df858f58c87ec523
python -m venv .venv
```

Activate with `source .venv/bin/activate` on POSIX shells, or `.venv\Scripts\Activate.ps1` in PowerShell. If activation is unavailable, invoke `.venv/bin/python` or `.venv\Scripts\python.exe` explicitly in place of `python`.

```text
python -m pip install --disable-pip-version-check jsonschema pytest
python veritas-evaluation-kit/evaluation/validate_evaluation_package.py
```

Expected output: `Agent Gate evaluation package schema and synthetic example are valid.` This checks the Draft 2020-12 schema and bundled fixture, not an evaluator's report or the running specimen. `example-result.json` is synthetic, was not executed, and must never count as external validation, including its illustrative calibration booleans.

Before running any harness, enter the specimen checkout and verify its identity:

```text
cd veritas-v0.1
git rev-parse HEAD
git status --porcelain
python -c "import agent_gate; print(agent_gate.__file__)"
python -m pytest -q tests/test_agent_gate.py tests/test_agent_gate_contracts.py
```

Stop if HEAD is not the full frozen SHA above, tracked files are modified, or the import resolves outside this specimen's `agent_gate` directory. Do not add local modules that shadow specimen modules. Python may generate untracked `__pycache__` directories. Run from this directory so Python imports this specimen, and repeat identity checks after evaluation. An external harness must also record the resolved import location in its own process; starting in this directory alone does not guarantee its import path.

Record Python/dependency versions (`python --version`, `python -m pip freeze`) and import location with the results. The schema pins the reported repository and commit; it cannot prove which code a harness actually imported. The author suite passing is a setup check, not independent evaluation or instrument calibration. To reproduce a kit revision later, check out its recorded full SHA in `veritas-evaluation-kit`; never substitute that SHA for the specimen target.

## Stable evaluator surface

```python
from agent_gate import AgentGate, ControlApproval, ReplayStore, digest_action
```

Use:

- `digest_action(action)` to calculate the canonical action digest used by local approval bindings.
- `AgentGate.evaluate_and_issue(...)` to evaluate a typed action plus presented approvals and, when eligible, issue a single-use ticket.
- `AgentGate.reevaluate_ticket(...)` for the immediate pre-execution shadow recheck.

## Minimum instrument calibration

A useful external instrument must demonstrate that it can observe both sides of the decision boundary.

Before reporting a clean result, show at least:

1. one legitimate acceptance control that produces the expected contract-qualified shadow allow; and
2. one deliberately broken semantic control that the instrument detects as a failure.

A harness that only produces denials is insufficient evidence because a reject-everything implementation can pass negative cases for the wrong reason.

For deliberate-negative calibration, preserve a separate instrument fixture with a known semantic violation (for example, an intentionally fabricated `SHADOW_ALLOW` for duplicate required controls where the oracle expects `DENY`). Run that fixture through the same evaluator comparison/reporting path and require an observable failure, such as a failed assertion or nonzero exit. Record the injected violation, expected and observed failure, command, and logs separately from results on the frozen specimen. Do not modify the specimen for calibration.

Merely observing an expected denial on a hostile input does not demonstrate that the instrument detects a broken result. A calibration failure detected as intended is not a specimen defect. The schema requires both calibration flags to be true for `clean_within_tested_scope`; the flags alone do not prove calibration occurred. If calibration is missing and no other conclusion is established, report `inconclusive`. Preserve a demonstrated defect or instrument issue under its appropriate summary even when calibration is incomplete.

Use `calibration.notes` for calibration procedure and artifact references. For ordinary cases, `instrument_observed_failure` means the observed behavior violated the case's expected semantics: an expected denial that is correctly observed is a baseline pass with this flag false. The deliberately broken calibration fixture should trigger this flag in the instrument's calibration output; keep that output separate from specimen findings. The bundled synthetic example is illustrative and must not supply observed values for a real report.

## Canonical positive control

For `filesystem.write`, construct an action under `workspace/` with `content_sha256` and present exactly these controls:

- `scope`
- `change`

Requirements:

- the two controls are bound to the exact action digest;
- two distinct presented `approver_id` values are used;
- the ticket is rechecked against the exact same action;
- the expected result is a contract-qualified shadow allow with `execution_authorized = false`.

Use an action shaped as `{"type": "filesystem.write", "target": "workspace/example.txt", "parameters": {"content_sha256": "abc123"}}`, matching the author fixture. Construct approvals with `ControlApproval.issue(control_id=..., approver_id=..., action_digest=digest_action(action))`. Unpack `(result, ticket)` from `evaluate_and_issue(action, approvals=approvals)`; require `result.decision.value == "SHADOW_ALLOW"`, `result.execution_authorized is False`, and a non-null ticket. Then call `reevaluate_ticket(action, ticket=ticket)` on the same gate/store and require the same decision and non-execution flag. Use a fresh gate/store per unrelated case; retain the same store for replay and burned-ticket cases. The action describes a shadow operation; no file is written.

## Required hostile baseline

At minimum, exercise the following declared hostile cases and record expected versus observed behavior:

1. Duplicate one required control so cardinality is correct but the distinct control set is wrong.
2. Present the correct required controls using only one approver identifier.
3. Substitute an approval bound to a different action.
4. Mutate the target after ticket issuance and before recheck.
5. Replay a ticket after successful consumption.
6. Retry the original action after a mutated-action recheck has already burned the ticket.
7. Present an unknown operation type.
8. Attempt path traversal outside the allowed namespace.

These are baseline regressions, not a limit on evaluation. Independent hostile cases are strongly encouraged.

## Independent hostile cases

If you identify a new case, report it separately from the declared baseline. Include enough information to reproduce it exactly:

- case identifier;
- evaluator-defined claim being tested;
- input action;
- approvals/control artifacts used;
- ticket lifecycle, if applicable;
- expected behavior;
- observed behavior;
- whether the result is a newly discovered defect, a declared limitation, or an instrument issue;
- minimal reproduction steps.

Do not classify a known non-claim as a newly discovered defect merely because it is exploitable within the stated boundary.

## Explicit v0.1 boundaries

The target does **not** claim to establish:

- authenticated approver identity;
- trusted approval issuers;
- resistance to a caller that can mint arbitrary local `ControlApproval` objects;
- real human or principal separation of duty;
- approval freshness or expiry;
- external policy-engine enforcement;
- factual truth of external evidence;
- production safety or security certification;
- distributed replay safety beyond the configured SQLite replay store;
- execution authority.

Distinct approver IDs mean distinct presented identifiers only.

## Result reporting

Please submit results in both human-readable form and the machine-readable structure defined by:

`evaluation/agent-gate-evaluation-result.schema.json`

From the specimen checkout, use the activated environment to check your report:

```text
python ../veritas-evaluation-kit/evaluation/validate_evaluation_package.py /path/to/result.json
```

Replace `/path/to/result.json` with your report's path (quote paths containing spaces). The command checks the package safeguards first, then the report's schema and frozen-target fields. It exits nonzero on an invalid report or unreadable file. A valid report prints `Report structure is valid for the frozen target; evidence and calibration observations are not verified.` Schema validation does not verify timestamps, artifact contents, evaluator independence, imported code, or whether calibration actually occurred; review those against preserved logs.

For each case, distinguish:

- `expected`
- `observed`
- `instrument_observed_failure`
- `classification`

Recommended classifications are:

- `acceptance_control`
- `declared_baseline_pass`
- `declared_baseline_fail`
- `independent_hostile_case`
- `known_boundary`
- `instrument_issue`
- `inconclusive`

## Evidence discipline

A clean evaluation is evidence about the tested claims, target, and method only. It is not a production security certification.

A failure should preserve the failing fixture before remediation. A remediation should be evaluated as a new commit and should not rewrite the historical result for v0.1.

If the evaluator discovers a harness defect during testing, record that separately rather than silently correcting history.

## Reproduction metadata

Please record:

- repository
- exact target commit
- evaluator name/handle
- evaluator repository or harness version/commit, if applicable
- execution environment
- date/time in UTC
- positive-control result
- deliberate-negative calibration result
- declared baseline results
- independent hostile cases
- raw logs or artifact references when available

The goal is not to maximize pass counts. The goal is to produce a falsifiable record that another party can inspect and reproduce.
