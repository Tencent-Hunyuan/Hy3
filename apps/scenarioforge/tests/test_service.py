from __future__ import annotations

import unittest

from scenarioforge.examples import EXAMPLES, DemoClient
from scenarioforge.models import RehearsalRequest
from scenarioforge.service import RehearsalService, _merge_usage


class ServiceTests(unittest.TestCase):
    def test_runs_two_stage_vertical_slice(self) -> None:
        source = EXAMPLES["saas-release"]
        request = RehearsalRequest.from_json(source)
        result = RehearsalService(DemoClient(source["id"])).run(request)
        self.assertEqual(result["decision"]["recommendation"], "NO_GO")
        self.assertEqual(result["provider"]["calls"], 2)
        self.assertEqual(len(result["input_digest"]), 12)

    def test_merges_usage_without_coercing_strings(self) -> None:
        merged = _merge_usage(
            {"prompt_tokens": 10, "total_tokens": 12},
            {"prompt_tokens": "bad", "completion_tokens": 4, "total_tokens": 9},
        )
        self.assertEqual(merged, {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 21})


if __name__ == "__main__":
    unittest.main()
