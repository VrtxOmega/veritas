# Michael Saleme's Agent Gate v0.1 report — preserved submission

Original author: Michael Saleme / GitHub `msaleme`.
Source: https://github.com/msaleme/red-team-blue-team-agent-fabric/issues/304#issuecomment-5554102070
Source creation and last-update time at readback: `2026-09-05T19:03:21Z`.

`report.md` preserves the original UTF-8 comment body, including its unchanged Python block. The report was supplied publicly by the evaluator; this is an attributed archival copy, not a claim that the campaign author wrote or independently calibrated it. No additional license grant is inferred from the comment. The evaluator has offered a PR; this archive does not impersonate that contribution.

Report SHA-256: `2561f3b4c6b71766d56d38ceedcc53ba2d84712837c28ce4040b9498a8e92c61`.
Extracted Python-block SHA-256: `717d522609e794ad0074b90b4787ca4eaf0243ef362866a4e1753cf94f6e2c12`.
The extraction includes the block's final newline. A GitHub comment ID is a source identifier, not immutable content; the frozen Git copy and these hashes identify the captured bytes.

## Original scope

Target: `256daeb85dae7ac004ae9893df858f58c87ec523`. The reporter describes Python 3.12, local specimen imports and no tracked changes before/after. His 17 author-suite passes are setup only. His separately authored probe records **17 expected outcomes and one float exception**, not 18 passing verdicts. He calls the tested contract clean, explicitly treats the float as an observation, and discloses correcting a double-recheck error in his instrument. Preserve his interpretation alongside the project's assessment.

The posted float case raises during `approvals_for -> digest_action`, before entering `evaluate_and_issue`. The script does not demonstrate deliberate wrong-result calibration, assert the first successful ticket recheck, assert `execution_authorized=False`, or use a failing process exit for unexpected observations. Reason inspection is reported as manual. These limits do not invalidate intake of the report; do not silently promote it into a fully calibrated clean-run claim.

## Separate project-side reproduction and calibration

From a separate checkout of the frozen specimen:

```sh
python -B evaluation/reproduce_msaleme_20260905.py --specimen /path/to/specimen --expected-commit 256daeb85dae7ac004ae9893df858f58c87ec523 --expected-float-retry SHADOW_ALLOW --output results/frozen-reproduction.json
```

Run that command from the kit checkout. It verifies the clean specimen Git revision and import location, checks original report/probe hashes, executes the unmodified code block, and records environment, package hashes, observations and separate project-side supplements. It never authorizes or executes an agent action. It writes only its result and temporary replay-test database.

The new project-side calibration injects an always-eligible registry and an always-deny issuer separately; the original comparison path must detect both wrong outcomes. Positive issuance, successful recheck, replay denial and non-execution are checked separately. None of these added observations is attributed to Michael or counted as external calibration.

The float-at-recheck supplement starts with a valid issued ticket, adds a float only during recheck, then retries the original action. The frozen implementation raises before consumption and permits the original retry. That is a separate project-side lifecycle gap relative to the original document's unconditional burn-on-failed-recheck sentence. The mutated action does not allow, there are not two successful consumptions, and no action executes. A successful reproduction job means the known gap was reproduced, not that this property passed. The command explicitly expects `SHADOW_ALLOW` on that historical specimen; a later repair is evaluated separately with `DENY`.

Local Python 3.13.5 reproduction used blob-verified reconstructed package files, not a complete clone. The dedicated workflow performs a full pinned checkout and Python 3.12 reproduction; cite its actual run/commit rather than treating this document as proof of execution. New failures must remain visible, not be absorbed into the archived report.

Protocol v2's existing individual cap is already reached for this actor. Archive and linked reproduction carry **zero additional qualifying weight**. This is useful external technical evidence, not certification, authenticated-principal assurance, adoption, payment, or whole-project security validation.
