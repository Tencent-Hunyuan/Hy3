from __future__ import annotations

import unittest

from scenarioforge.examples import EXAMPLES
from scenarioforge.models import (
    ContractError,
    RehearsalRequest,
    validate_analysis,
    validate_decision,
)


class RequestTests(unittest.TestCase):
    def test_accepts_bundled_input(self) -> None:
        source = EXAMPLES["campus-night-market"]
        request = RehearsalRequest.from_json(source)
        self.assertEqual(request.example_id, source["id"])
        self.assertEqual(len(request.constraints), 4)

    def test_normalizes_whitespace(self) -> None:
        request = RehearsalRequest.from_json(
            {
                "title": "  Release   plan  ",
                "goal": "Finish the release without customer impact.",
                "plan": "A sufficiently detailed plan that is longer than thirty characters.",
                "constraints": ["  No   duplicate invoices  "],
            }
        )
        self.assertEqual(request.title, "Release plan")
        self.assertEqual(request.constraints, ("No duplicate invoices",))

    def test_rejects_empty_constraints(self) -> None:
        source = dict(EXAMPLES["saas-release"])
        source["constraints"] = []
        with self.assertRaisesRegex(ContractError, "non-empty"):
            RehearsalRequest.from_json(source)

    def test_rejects_oversized_plan(self) -> None:
        source = dict(EXAMPLES["saas-release"])
        source["plan"] = "x" * 12_001
        with self.assertRaisesRegex(ContractError, "exceeds"):
            RehearsalRequest.from_json(source)


class OutputContractTests(unittest.TestCase):
    def test_accepts_both_bundled_outputs(self) -> None:
        for example in EXAMPLES.values():
            self.assertIn("brief", validate_analysis(example["analysis"]))
            self.assertIn("gates", validate_decision(example["decision"]))

    def test_rejects_unknown_verdict(self) -> None:
        decision = dict(EXAMPLES["saas-release"]["decision"])
        decision["recommendation"] = "MAYBE"
        with self.assertRaisesRegex(ContractError, "recommendation"):
            validate_decision(decision)

    def test_rejects_invalid_severity(self) -> None:
        analysis = dict(EXAMPLES["saas-release"]["analysis"])
        analysis["perspectives"] = [dict(item) for item in analysis["perspectives"]]
        analysis["perspectives"][0]["severity"] = "urgent"
        with self.assertRaisesRegex(ContractError, "severity"):
            validate_analysis(analysis)


if __name__ == "__main__":
    unittest.main()
