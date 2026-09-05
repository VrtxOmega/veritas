# Valid-ticket recheck errors — later-revision remediation

## Preserved failure before repair

The frozen specimen remains `256daeb85dae7ac004ae9893df858f58c87ec523`. Michael Saleme's [unchanged report](external/msaleme-20260905/report.md) stays at 17 matching outcomes and one exception. His float case did not exercise a previously issued ticket. The separate project-side follow-on did: valid issuance, float introduced at recheck, ValueError before replay consumption, then a successful original-action retry. This conflicted with the frozen document's unqualified burn-on-failed-recheck sentence; a later disclaimer cannot erase that violation.

Full-checkout CPython 3.12.14 reproduction occurred before repair in [run 33987139311](https://github.com/VrtxOmega/veritas/actions/runs/33987139311), job `101362709000`. Memory and filesystem-backed stores exhibited the same behavior. Original author tests passed 17/17 as setup, while the published external probe reproduced 17 matches / zero mismatched verdicts / one exception. Added wrong-verdict calibration is project-side, not retroactively part of Michael's run.

## Narrow repair

When action canonicalization raises an ordinary `Exception`, `reevaluate_ticket` now checks the ticket's existing local integrity binding, atomically consumes an intact ticket through the configured replay store, and re-raises. The exception is not converted to an allow or a logged skip. Floats remain unsupported and their exception surface remains visible; this is a ticket-lifecycle repair, not a new floating-point canonicalization scheme or general integration adapter.

Only the demonstrated valid/intact-ticket input-error path is repaired. An integrity-invalid object must not consume a claimed ticket ID belonging to another attempt. These local bindings are not authentication against someone able to mint/rebind arbitrary ticket objects. An unavailable store, failed commit, process termination, database rollback/deletion or interference cannot be claimed to provide durable consumption; store errors propagate without an allow. This patch is not a closure claim for every interpretation of the old unconditional sentence or for hostile runtime/storage control. Those are residual scope limits, not excuses applied to the preserved frozen counterexample.

## Regression evidence

The new 25-case project suite covers eight malformed-action classes with memory and file stores (floats, nested floats, unsafe integers, sets, Unicode encoding failure, NaN, non-string keys and cyclic containers), injected serializer exceptions, unavailable storage, positive one-use acceptance, an integrity-invalid ticket that must not burn another ID, and a file-backed burn observed by a new Python process.

Before repair on the blob-verified local Python 3.13.5 source, the new suite produced **21 failures and 4 passes**. After repair all **25** passed. The differential CI runs the exact same new regression file against the full frozen checkout and the proposed revision on Python 3.12 and 3.13. It requires the 21 specified semantic failures, no import/errors/skips, and four retained positive/integrity controls on the frozen checkout; arbitrary test failure cannot satisfy this red control. The candidate must pass all 17 original and 25 new tests. Cite the actual completed CI run rather than treating this description as execution evidence.

The original external probe remains unchanged. The project-side replay expects its original 17-plus-exception pattern on both revisions while requiring the separately reported float-at-recheck retry to change from SHADOW_ALLOW on the frozen specimen to DENY on the repair. No event count, outreach allowance, authenticated identity, external policy or execution authority changes. Any external re-evaluation of the repair is a future report, not implied by these project-side tests.
