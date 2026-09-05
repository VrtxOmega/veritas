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


def validate_package() -> Draft202012Validator:
    schema = load_json(SCHEMA_PATH)
    example = load_json(EXAMPLE_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(example)

    target = example["target"]
    schema_target = schema["properties"]["target"]["properties"]
    for field, expected in (("repository", EXPECTED_REPOSITORY), ("commit", EXPECTED_COMMIT)):
        if target[field] != expected or schema_target[field].get("const") != expected:
            raise ValueError(f"Evaluation package target {field} must remain {expected}")

    if example["evaluator"]["name_or_handle"] != "EXAMPLE_ONLY_NOT_EVIDENCE":
        raise ValueError("Bundled example must remain explicitly synthetic")
    if example["summary"]["result"] != "inconclusive":
        raise ValueError("Bundled synthetic example must remain inconclusive")

    return Draft202012Validator(schema)


def main() -> None:
    validate_package()
    print("Agent Gate evaluation package schema and synthetic example are valid.")


if __name__ == "__main__":
    main()
