"""Package regressions using synthetic data only; not external evaluation evidence."""

import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent


class EvaluationPackageTests(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads((ROOT / "agent-gate-evaluation-result.schema.json").read_text())
        self.example = json.loads((ROOT / "example-result.json").read_text())
        self.validator = Draft202012Validator(self.schema)

    def test_schema_and_original_synthetic_example(self):
        Draft202012Validator.check_schema(self.schema)
        self.validator.validate(self.example)

    def test_wrong_target_rejected(self):
        for field, wrong in (("commit", "0" * 40), ("repository", "wrong/repository")):
            with self.subTest(field=field):
                report = copy.deepcopy(self.example)
                report["target"][field] = wrong
                self.assertFalse(self.validator.is_valid(report))

    def test_clean_requires_both_calibrations(self):
        report = copy.deepcopy(self.example)
        report["summary"]["result"] = "clean_within_tested_scope"
        for positive in (False, True):
            for negative in (False, True):
                with self.subTest(positive=positive, negative=negative):
                    report["calibration"]["positive_control_observed"] = positive
                    report["calibration"]["deliberate_negative_observed"] = negative
                    self.assertEqual(self.validator.is_valid(report), positive and negative)

    def test_incomplete_calibration_can_report_nonclean_results(self):
        report = copy.deepcopy(self.example)
        report["calibration"]["positive_control_observed"] = False
        report["calibration"]["deliberate_negative_observed"] = False
        for result in ("inconclusive", "defect_found", "instrument_issue"):
            with self.subTest(result=result):
                report["summary"]["result"] = result
                self.validator.validate(report)

    def run_copy(self, mutate, optimized=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("validate_evaluation_package.py", "agent-gate-evaluation-result.schema.json", "example-result.json"):
                shutil.copy2(ROOT / name, root / name)
            schema = copy.deepcopy(self.schema)
            example = copy.deepcopy(self.example)
            mutate(schema, example)
            (root / "agent-gate-evaluation-result.schema.json").write_text(json.dumps(schema))
            (root / "example-result.json").write_text(json.dumps(example))
            command = [sys.executable] + (["-O"] if optimized else [])
            return subprocess.run(command + [str(root / "validate_evaluation_package.py")], cwd=root.parent,
                                  capture_output=True, text=True, timeout=30)

    def test_validator_runs_outside_package_directory(self):
        result = self.run_copy(lambda schema, example: None)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_coordinated_target_drift_fails_even_with_optimization(self):
        for field, wrong in (("commit", "0" * 40), ("repository", "wrong/repository")):
            for optimized in (False, True):
                with self.subTest(field=field, optimized=optimized):
                    def drift(schema, example):
                        schema["properties"]["target"]["properties"][field]["const"] = wrong
                        example["target"][field] = wrong
                    result = self.run_copy(drift, optimized)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(f"target {field} must remain", result.stderr)

    def test_synthetic_marker_cannot_be_removed_under_optimization(self):
        def remove_marker(schema, example):
            example["evaluator"]["name_or_handle"] = "apparently-real"
        result = self.run_copy(remove_marker, optimized=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must remain explicitly synthetic", result.stderr)

    def test_report_cli_from_another_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "report with spaces.json"
            command = [sys.executable, str(ROOT / "validate_evaluation_package.py"), str(report_path)]
            for kind in ("valid", "wrong_target", "uncalibrated_clean", "malformed", "missing"):
                with self.subTest(kind=kind):
                    report = copy.deepcopy(self.example)
                    if kind == "wrong_target":
                        report["target"]["commit"] = "0" * 40
                    if kind == "uncalibrated_clean":
                        report["summary"]["result"] = "clean_within_tested_scope"
                        report["calibration"]["deliberate_negative_observed"] = False
                    report_path.write_text("{" if kind == "malformed" else json.dumps(report))
                    if kind == "missing":
                        report_path.unlink()
                    result = subprocess.run(command, cwd=directory, capture_output=True, text=True, timeout=30)
                    self.assertEqual(result.returncode == 0, kind == "valid", result.stderr)
                    if kind == "valid":
                        self.assertIn("observations are not verified", result.stdout)


if __name__ == "__main__":
    unittest.main()
