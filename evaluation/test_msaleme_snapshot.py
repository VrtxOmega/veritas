"""Project-side artifact guards, not independent evidence."""
from pathlib import Path
import tempfile
import unittest

from reproduce_msaleme_20260905 import SNAPSHOT, extract_probe, require


class SnapshotTests(unittest.TestCase):
    def test_original_report_and_probe_hashes(self):
        compile(extract_probe(), "original-msaleme-probe", "exec")

    def test_guard_rejects_modified_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "report.md"
            p.write_bytes(SNAPSHOT.read_bytes() + b"changed\n")
            with self.assertRaisesRegex(RuntimeError, "report hash mismatch"):
                extract_probe(p)

    def test_require_cannot_silently_accept_a_violation(self):
        require(True, "valid control")
        with self.assertRaisesRegex(RuntimeError, "deliberate violation"):
            require(False, "deliberate violation")
