from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "agent-gate-evaluation-result.schema.json"
EXAMPLE_PATH = ROOT / "example-result.json"
EXPECTED_REPOSITORY = "VrtxOmega/veritas"
EXPECTED_COMMIT = "256daeb85dae7ac004ae9893df858f58c87ec523"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    schema = load_json(SCHEMA_PATH)
    example = load_json(EXAMPLE_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(example)

    target = example["target"]
    assert target["repository"] == EXPECTED_REPOSITORY
    assert target["commit"] == EXPECTED_COMMIT

    schema_target = schema["properties"]["target"]["properties"]
    assert schema_target["repository"]["const"] == EXPECTED_REPOSITORY
    assert schema_target["commit"]["const"] == EXPECTED_COMMIT

    assert example["evaluator"]["name_or_handle"] == "EXAMPLE_ONLY_NOT_EVIDENCE"
    assert example["summary"]["result"] == "inconclusive"

    print("Agent Gate evaluation package schema and synthetic example are valid.")


if __name__ == "__main__":
    main()
