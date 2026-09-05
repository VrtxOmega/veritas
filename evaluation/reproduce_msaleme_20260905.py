"""Project-side replay and NEW calibration; never an external evaluation claim."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch

SNAPSHOT = Path(__file__).resolve().parent / "external/msaleme-20260905/report.md"
REPORT_SHA256 = "2561f3b4c6b71766d56d38ceedcc53ba2d84712837c28ce4040b9498a8e92c61"
PROBE_SHA256 = "717d522609e794ad0074b90b4787ca4eaf0243ef362866a4e1753cf94f6e2c12"
FROZEN = "256daeb85dae7ac004ae9893df858f58c87ec523"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def extract_probe(path: Path = SNAPSHOT) -> str:
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == REPORT_SHA256, "Original report hash mismatch")
    text = raw.decode("utf-8")
    require(text.count("```python\n") == 1, "Expected one original Python block")
    probe = text.split("```python\n", 1)[1].split("```", 1)[0]
    require(hashlib.sha256(probe.encode()).hexdigest() == PROBE_SHA256, "Original probe hash mismatch")
    return probe


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True, timeout=30).strip()


def package_hashes(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((root / "agent_gate").glob("*.py"))}


def replay() -> dict:
    # Caller/main establishes and records the imported specimen before running this.
    from agent_gate import AgentGate, ControlApproval, ContractResult, GateDecision, GateResult, OperationRegistry, ReplayStore, digest_action
    ns = {"__name__": "preserved_msaleme_probe", "__file__": str(SNAPSHOT)}
    capture = io.StringIO()
    with contextlib.redirect_stdout(capture):
        exec(compile(extract_probe(), str(SNAPSHOT), "exec"), ns)
    rows = list(ns["RESULTS"])
    require(len(rows) == 18 and len({row[0] for row in rows}) == 18, "Original case set changed")
    require(sum(row[1] == "MATCH" for row in rows) == 17, "Original observed matches changed")
    exceptional = [row for row in rows if row[1] != "MATCH"]
    require(len(exceptional) == 1 and exceptional[0][0] == "EXT: float in envelope is rejected"
            and exceptional[0][1] == "EXCEPTION" and exceptional[0][2].startswith("ValueError: floats are not permitted"),
            "Original exception observation changed")

    # NEW project-side mutant calibration. Neither was present in the external report.
    with patch.object(OperationRegistry, "validate", return_value=ContractResult(True, "PROJECT MUTANT: ignores controls")):
        ns["check"]("CALIBRATION: incorrect duplicate-control allow", False,
                    lambda: ns["run"](ns["action"](), [("scope", "alice"), ("scope", "bob")]))
    with patch.object(AgentGate, "evaluate_and_issue", return_value=(GateResult(GateDecision.DENY, False, "PROJECT MUTANT: rejects everything", ""), None)):
        ns["check"]("CALIBRATION: incorrect positive-control denial", True,
                    lambda: ns["run"](ns["action"](), ns["GOOD"]))
    calibration = ns["RESULTS"][18:]
    require(len(calibration) == 2 and all(row[1] == "MISMATCH" for row in calibration), "Instrument failed to detect a deliberately incorrect result")

    lifecycle = []
    with tempfile.TemporaryDirectory() as tmp:
        for store_name, store_path in [("memory", ":memory:"), ("file", str(Path(tmp) / "replay.sqlite3"))]:
            store = ReplayStore(store_path)
            try:
                gate = AgentGate(replay_store=store)
                a = ns["action"]()
                approvals = ns["approvals_for"](a, ns["GOOD"])
                issued, ticket = gate.evaluate_and_issue(a, approvals=approvals)
                require(issued.decision is GateDecision.SHADOW_ALLOW and issued.execution_authorized is False and ticket is not None, "Positive issuance failed")
                first = gate.reevaluate_ticket(a, ticket=ticket)
                again = gate.reevaluate_ticket(a, ticket=ticket)
                require(first.decision is GateDecision.SHADOW_ALLOW and again.decision is GateDecision.DENY, "Positive recheck/replay control failed")
                require(first.execution_authorized is False and again.execution_authorized is False, "Execution boundary changed")
                _, ticket = gate.evaluate_and_issue(a, approvals=approvals)
                require(ticket is not None, "Missing ticket for float-at-recheck experiment")
                try:
                    gate.reevaluate_ticket({**a, "weight": 1.5}, ticket=ticket)
                except ValueError as exc:
                    error = str(exc)
                    require("floats are not permitted" in error, "Unexpected recheck exception")
                else:
                    raise RuntimeError("Float-at-recheck did not raise")
                retry = gate.reevaluate_ticket(a, ticket=ticket)
                require(retry.execution_authorized is False, "Retry authorized execution")
                lifecycle.append({"store": store_name, "error": error, "retry": retry.decision.value,
                                  "execution_authorized": retry.execution_authorized})
            finally:
                store._db.close()  # Test cleanup only; no public close API exists in v0.1.
    return {"original_probe_stdout": capture.getvalue(), "original_probe_results": rows,
            "original_summary": {"match": 17, "mismatch": 0, "exception": 1},
            "project_side_mutant_calibration": calibration, "project_side_float_recheck": lifecycle}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--specimen", required=True, type=Path)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--expected-float-retry", required=True, choices=["SHADOW_ALLOW", "DENY"])
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = args.specimen.resolve()
    before_commit = git(root, "rev-parse", "HEAD")
    require(before_commit == args.expected_commit, "Specimen commit mismatch")
    require(not git(root, "status", "--porcelain", "--untracked-files=no"), "Tracked specimen modifications")
    require("agent_gate" not in sys.modules, "Specimen was imported before identity checks")
    before = package_hashes(root)
    require(len(before) == 5, "Unexpected specimen package file set")
    sys.path.insert(0, str(root))
    import agent_gate
    require(Path(agent_gate.__file__).resolve() == root / "agent_gate/__init__.py", "Wrong imported specimen")
    observed = replay()
    for row in observed["project_side_float_recheck"]:
        require(row["retry"] == args.expected_float_retry, "Float-at-recheck outcome differs from the requested experiment")
    require(package_hashes(root) == before and git(root, "rev-parse", "HEAD") == before_commit, "Specimen changed during replay")
    require(not git(root, "status", "--porcelain", "--untracked-files=no"), "Tracked modifications after replay")
    output = {"classification": "project_side_reproduction_and_new_calibration",
              "external_evaluation": False, "count_weight": 0,
              "recorded_at": datetime.now(timezone.utc).isoformat(),
              "target_commit": before_commit, "frozen_target": FROZEN,
              "python": sys.version, "platform": platform.platform(), "sqlite": sqlite3.sqlite_version,
              "import_path": str(Path(agent_gate.__file__).resolve()), "package_sha256": before,
              "original_report_sha256": REPORT_SHA256, "original_probe_sha256": PROBE_SHA256,
              "expected_float_retry": args.expected_float_retry, **observed}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(observed["original_probe_stdout"], end="")
    print("PROJECT-SIDE calibration: both deliberate wrong verdicts detected")
    print("PROJECT-SIDE float-at-recheck:", json.dumps(observed["project_side_float_recheck"]))
    print("Record:", args.output)


if __name__ == "__main__":
    main()
