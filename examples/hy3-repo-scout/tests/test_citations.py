from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from hy3_repo_scout.citations import (
    CitationError,
    EvidenceLine,
    citation_validation_result,
    evidence_lines_from_trace,
    extract_citations,
    parse_citation,
    validate_citations,
)
from hy3_repo_scout.tools import RepoTools


class CitationTests(TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "module.py").write_text(
            "first = 1\nsecond = 2\nthird = first + second\n",
            encoding="utf-8",
        )
        (self.root / ".env").write_text("TOKEN=hidden\n", encoding="utf-8")
        self.tools = RepoTools(self.root)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_parse_and_extract_canonical_citations(self) -> None:
        citation = parse_citation("[src/module.py:L1-L3]")
        self.assertEqual(citation.path, "src/module.py")
        self.assertEqual(citation.start_line, 1)
        self.assertEqual(citation.end_line, 3)
        self.assertEqual(citation.label, "[src/module.py:L1-L3]")

        extracted = extract_citations(
            "One [src/module.py:L1-L1], then [src/module.py:L2-L3]."
        )
        self.assertEqual([item.label for item in extracted], [
            "[src/module.py:L1-L1]",
            "[src/module.py:L2-L3]",
        ])

    def test_malformed_and_reversed_ranges_are_rejected(self) -> None:
        malformed = (
            "[src/module.py:L1]",
            "[src/module.py:1-2]",
            "[src/module.py:l1-l2]",
            "[src/module.py:line 1]",
            "[src/module.py:L0-L1]",
            "[src/module.py:L3-L2]",
            f"[src/module.py:L{'9' * 5_000}-L1]",
        )
        for label in malformed:
            with self.subTest(label=label), self.assertRaises(CitationError):
                parse_citation(label)

    def test_unpaired_and_multiline_citation_attempts_are_rejected(self) -> None:
        malformed = (
            "Good [src/module.py:L1-L1], broken [src/module.py:L2-L2",
            "Good [src/module.py:L1-L1], broken src/module.py:L2-L2]",
            "Good [src/module.py:L1-L1], broken [src/module.py:L2-L2\n]",
            "Good [src/module.py:L1-L1], broken [[src/module.py:L2-L2]]",
            "Good [src/module.py:L1-L1], broken [[src/module.py:L2-L2]",
            "Good [src/module.py:L1-L1], broken [src/module.py:L2-L2]]",
        )
        for text in malformed:
            with self.subTest(text=text), self.assertRaises(CitationError) as caught:
                extract_citations(text)
            self.assertEqual(caught.exception.code, "malformed")
        with self.assertRaises(CitationError) as caught:
            extract_citations("Claim [src/module.py:L1].")
        self.assertEqual(caught.exception.code, "malformed")

    def test_validate_checks_readability_and_line_bounds(self) -> None:
        citations = validate_citations(
            "The total is computed here [src/module.py:L2-L3].",
            self.tools,
            require=True,
        )
        self.assertEqual([item.label for item in citations], ["[src/module.py:L2-L3]"])

        with self.assertRaises(CitationError) as caught:
            validate_citations("Bad [src/module.py:L3-L4].", self.tools)
        self.assertEqual(caught.exception.code, "invalid_range")
        with self.assertRaises(CitationError) as caught:
            validate_citations("Secret [.env:L1-L1].", self.tools)
        self.assertEqual(caught.exception.code, "sensitive")

    def test_validate_rejects_unsafe_and_noncanonical_paths(self) -> None:
        labels = (
            "[../outside.py:L1-L1]",
            "[/tmp/outside.py:L1-L1]",
            "[C:/outside.py:L1-L1]",
            "[./src/module.py:L1-L1]",
            "[src//module.py:L1-L1]",
            "[src\\module.py:L1-L1]",
        )
        for label in labels:
            with self.subTest(label=label), self.assertRaises(CitationError):
                validate_citations(f"Claim {label}", self.tools)

    def test_requires_evidence_and_limits_span(self) -> None:
        with self.assertRaises(CitationError) as caught:
            validate_citations("No repository evidence.", self.tools, require=True)
        self.assertEqual(caught.exception.code, "missing")
        with self.assertRaises(CitationError) as caught:
            validate_citations("Wide [src/module.py:L1-L3].", self.tools, max_span=2)
        self.assertEqual(caught.exception.code, "range_too_large")

    def test_json_friendly_validation_result(self) -> None:
        valid = citation_validation_result("Fact [src/module.py:L1-L1].", self.root)
        self.assertTrue(valid["valid"])
        self.assertEqual(valid["citations"][0]["path"], "src/module.py")
        invalid = citation_validation_result("Fact [src/module.py:L9-L9].", self.root)
        self.assertFalse(invalid["valid"])
        self.assertEqual(invalid["error"]["code"], "invalid_range")

    def test_citation_must_be_covered_by_returned_evidence(self) -> None:
        snapshot = self.tools.read_file("src/module.py", 1, 1)["_evidence"][0]
        evidence = [EvidenceLine(**snapshot)]
        with self.assertRaises(CitationError) as caught:
            validate_citations(
                "Fact [src/module.py:L2-L2]",
                self.tools,
                evidence_lines=evidence,
            )
        self.assertEqual(caught.exception.code, "unseen_evidence")

    def test_multiline_evidence_must_come_from_one_read_call(self) -> None:
        snapshots = self.tools.read_file("src/module.py", 1, 2)["_evidence"]
        separate_reads = [
            EvidenceLine(**snapshots[0], source_id="read-1", source_tool="read_file"),
            EvidenceLine(**snapshots[1], source_id="read-2", source_tool="read_file"),
        ]
        search_matches = [
            EvidenceLine(**snapshot, source_id="search-1", source_tool="search_text")
            for snapshot in snapshots
        ]
        one_read = [
            EvidenceLine(**snapshot, source_id="read-1", source_tool="read_file")
            for snapshot in snapshots
        ]

        for evidence in (separate_reads, search_matches):
            with self.subTest(evidence=evidence), self.assertRaises(CitationError) as caught:
                validate_citations(
                    "Fact [src/module.py:L1-L2]",
                    self.tools,
                    evidence_lines=evidence,
                )
            self.assertEqual(caught.exception.code, "unseen_evidence")

        validated = validate_citations(
            "Fact [src/module.py:L1-L2]",
            self.tools,
            evidence_lines=one_read,
        )
        self.assertEqual(len(validated), 1)

    def test_citation_limits_and_duplicate_reads_are_bounded(self) -> None:
        duplicate = " ".join(["[src/module.py:L1-L1]"] * 10)
        with patch.object(
            self.tools,
            "citation_snapshot",
            wraps=self.tools.citation_snapshot,
        ) as snapshot:
            validated = validate_citations(duplicate, self.tools)

        self.assertEqual(len(validated), 10)
        snapshot.assert_called_once()

        too_many = " ".join(["[src/module.py:L1-L1]"] * 501)
        with self.assertRaises(CitationError) as caught:
            validate_citations(too_many, self.tools)
        self.assertEqual(caught.exception.code, "too_many_citations")

    def test_detects_content_changed_after_model_saw_evidence(self) -> None:
        snapshot = self.tools.read_file("src/module.py", 1, 1)["_evidence"][0]
        evidence = [EvidenceLine(**snapshot)]
        (self.root / "src" / "module.py").write_text(
            "changed = True\nsecond = 2\nthird = first + second\n",
            encoding="utf-8",
        )

        with self.assertRaises(CitationError) as caught:
            validate_citations(
                "Fact [src/module.py:L1-L1]",
                self.tools,
                evidence_lines=evidence,
            )

        self.assertEqual(caught.exception.code, "stale_evidence")

    def test_extracts_private_evidence_only_from_read_and_search_trace(self) -> None:
        trace_type = type("Trace", (), {})
        items = []
        for name, evidence in (
            ("read_file", (EvidenceLine("src/module.py", 1, "a" * 64),)),
            ("search_text", (EvidenceLine("README.md", 1, "b" * 64),)),
            ("git_diff", (EvidenceLine("src/app.py", 3, "c" * 64),)),
        ):
            item = trace_type()
            item.name = name
            item.error = None
            item.evidence = evidence
            items.append(item)

        lines = evidence_lines_from_trace(items)

        self.assertEqual(
            [(item.path, item.line) for item in lines],
            [("src/module.py", 1), ("README.md", 1)],
        )
        self.assertEqual([item.source_tool for item in lines], ["read_file", "search_text"])
