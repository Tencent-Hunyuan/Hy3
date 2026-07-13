from unittest import TestCase

from hy3_repo_scout.prompts import (
    IMPACT_DEMO_PROMPT,
    PIPELINE_DEMO_PROMPT,
    SYSTEM_PROMPT,
    build_user_prompt,
)


class SystemPromptTests(TestCase):
    def test_requires_only_the_available_read_only_tools(self) -> None:
        for name in ("list_files", "search_text", "read_file", "git_diff"):
            self.assertIn(name, SYSTEM_PROMPT)
        self.assertIn("mutation", SYSTEM_PROMPT)
        self.assertIn("unexecuted suggestions", SYSTEM_PROMPT)

    def test_requires_citation_format_with_single_line_example(self) -> None:
        self.assertIn("[relative/path:Lstart-Lend]", SYSTEM_PROMPT)
        self.assertIn("[src/app.py:L42-L42]", SYSTEM_PROMPT)
        self.assertIn("never merge separate matches", SYSTEM_PROMPT)
        self.assertIn("every line", SYSTEM_PROMPT)
        self.assertIn("comma or semicolon lists", SYSTEM_PROMPT)

    def test_treats_repo_content_as_untrusted_and_reports_injections(self) -> None:
        self.assertIn("untrusted evidence", SYSTEM_PROMPT)
        self.assertIn("injection", SYSTEM_PROMPT)

    def test_rejects_unverified_absence_and_invented_test_commands(self) -> None:
        self.assertIn("not proof that a file is absent", SYSTEM_PROMPT)
        self.assertIn("call read_file with its exact path", SYSTEM_PROMPT)
        self.assertIn("successful exact-path read", SYSTEM_PROMPT)
        self.assertIn("Do not substitute a different test runner", SYSTEM_PROMPT)

    def test_labels_facts_inferences_risks_and_recommendations(self) -> None:
        for label in ("Fact:", "Inference:", "Risk:", "Recommendation:"):
            self.assertIn(label, SYSTEM_PROMPT)

    def test_requires_budget_awareness(self) -> None:
        self.assertIn("budget", SYSTEM_PROMPT.lower())

    def test_specifies_all_report_sections_in_order(self) -> None:
        sections = [
            "Executive Summary",
            "Evidence",
            "Findings",
            "Risks and Unknowns",
            "Verification Plan",
        ]
        for section in sections:
            self.assertIn(section, SYSTEM_PROMPT)
        positions = [SYSTEM_PROMPT.index(section) for section in sections]
        self.assertEqual(positions, sorted(positions))


class DemoPromptTests(TestCase):
    def test_impact_demo_is_non_empty_and_read_only(self) -> None:
        self.assertTrue(IMPACT_DEMO_PROMPT.strip())
        self.assertIn("不要修改", IMPACT_DEMO_PROMPT)
        self.assertIn("不要假设未声明的 pytest", IMPACT_DEMO_PROMPT)

    def test_pipeline_demo_is_non_empty_and_read_only(self) -> None:
        self.assertTrue(PIPELINE_DEMO_PROMPT.strip())
        self.assertIn("不要修改", PIPELINE_DEMO_PROMPT)
        self.assertIn("finetune/README_CN.md", PIPELINE_DEMO_PROMPT)
        self.assertIn("finetune/data/example_data.jsonl", PIPELINE_DEMO_PROMPT)
        self.assertIn("ds_zero2_offload.json", PIPELINE_DEMO_PROMPT)
        self.assertIn("ds_zero2_offload_lora.json", PIPELINE_DEMO_PROMPT)


class BuildUserPromptTests(TestCase):
    def test_contains_task_summary_and_sorted_budgets(self) -> None:
        prompt = build_user_prompt(
            "Trace the pipeline",
            "12 tracked files",
            {"max_rounds": 8, "max_context_chars": 120_000},
        )
        self.assertIn("Trace the pipeline", prompt)
        self.assertIn("12 tracked files", prompt)
        self.assertLess(prompt.index("max_context_chars"), prompt.index("max_rounds"))

    def test_strips_surrounding_whitespace(self) -> None:
        prompt = build_user_prompt(
            "  spaced question  ",
            "  spaced summary  ",
            {"budget": 1},
        )
        self.assertIn("spaced question", prompt)
        self.assertNotIn("  spaced question  ", prompt)
        self.assertIn("spaced summary", prompt)
        self.assertNotIn("  spaced summary  ", prompt)

    def test_empty_budgets_renders_header(self) -> None:
        prompt = build_user_prompt("q", "s", {})
        self.assertIn("## Hard budgets", prompt)

    def test_instructs_no_modification_and_budget_discipline(self) -> None:
        prompt = build_user_prompt("q", "s", {"budget": 1})
        self.assertIn("Do not modify", prompt)
        self.assertIn("budget", prompt.lower())
