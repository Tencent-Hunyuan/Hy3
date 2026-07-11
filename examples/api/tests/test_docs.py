from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
API_DIR = ROOT / "examples" / "api"

REQUIRED_DOCS = (
    ROOT / "README.md",
    ROOT / "README_CN.md",
    ROOT / "quickstart.md",
    ROOT / "quickstart_CN.md",
    API_DIR / "README.md",
    API_DIR / "README_CN.md",
    API_DIR / "01_basic_chat.md",
    API_DIR / "01_basic_chat_CN.md",
    API_DIR / "02_streaming.md",
    API_DIR / "02_streaming_CN.md",
    API_DIR / "03_streaming_vs_non_streaming.md",
    API_DIR / "03_streaming_vs_non_streaming_CN.md",
    API_DIR / "04_tool_calling.md",
    API_DIR / "04_tool_calling_CN.md",
    API_DIR / "05_reasoning_mode.md",
    API_DIR / "05_reasoning_mode_CN.md",
    API_DIR / "06_error_handling_retry.md",
    API_DIR / "06_error_handling_retry_CN.md",
)

MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
SECRET_PATTERNS = (
    re.compile(r"sk-or-v1-[A-Za-z0-9_-]{20,}"),
    re.compile(
        r"(?i)authorization:\s*bearer\s+(?!EMPTY\b|\$\{HY3_API_KEY\})"
        r"[A-Za-z0-9._-]{16,}"
    ),
)


class DocumentationContractTests(unittest.TestCase):
    def test_all_required_documents_exist(self) -> None:
        missing = [
            path.relative_to(ROOT).as_posix()
            for path in REQUIRED_DOCS
            if not path.is_file()
        ]

        self.assertEqual(missing, [])

    def test_guides_have_required_headings(self) -> None:
        for path in REQUIRED_DOCS[6:]:
            if not path.is_file():
                continue
            if path.stem.endswith("_CN"):
                headings = ("完整请求", "响应解析", "示例输出")
            else:
                headings = ("Complete request", "Response parsing", "Example output")
            text = path.read_text(encoding="utf-8")

            for heading in headings:
                with self.subTest(path=path.relative_to(ROOT), heading=heading):
                    self.assertIn(f"## {heading}", text)

    def test_live_evidence_is_marked_as_sanitized_summary(self) -> None:
        for path in REQUIRED_DOCS[6:]:
            text = path.read_text(encoding="utf-8")
            if path.stem.endswith("_CN"):
                marker = "已验证在线证据摘要（已脱敏，并非逐字标准输出）"
            else:
                marker = (
                    "Verified live evidence summary "
                    "(sanitized; not literal stdout)"
                )

            with self.subTest(path=path.relative_to(ROOT)):
                self.assertIn(marker, text)

    def test_basic_chat_keeps_deterministic_offline_example(self) -> None:
        expected = {
            API_DIR / "01_basic_chat.md": "Deterministic offline example",
            API_DIR / "01_basic_chat_CN.md": "确定性离线示例",
        }
        for path, marker in expected.items():
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertIn(marker, path.read_text(encoding="utf-8"))

    def test_reasoning_tokens_use_nested_usage_path(self) -> None:
        for path in (
            API_DIR / "05_reasoning_mode.md",
            API_DIR / "05_reasoning_mode_CN.md",
        ):
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertNotIn("usage.reasoning_tokens", text)
                self.assertIn(
                    "usage.completion_tokens_details.reasoning_tokens",
                    text,
                )

    def test_tool_call_live_summary_does_not_claim_unprinted_call_ids(self) -> None:
        for path in (
            API_DIR / "04_tool_calling.md",
            API_DIR / "04_tool_calling_CN.md",
        ):
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertNotIn("completed live tool loop", text)
                self.assertNotIn("完成的实时工具循环", text)
                self.assertNotIn("循环已完成", text)
                self.assertIn("CLI", text)
                self.assertIn("call ID", text)

    def test_quickstarts_use_supported_reasoning_configuration(self) -> None:
        for path in REQUIRED_DOCS[2:4]:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")

            for required_text in (
                "chat_template_kwargs",
                "extra_body",
                "tencent/hy3:free",
                "Invoke-RestMethod",
                "$env:HY3_API_KEY",
                "-Body $body",
                '-ContentType "application/json"',
            ):
                with self.subTest(
                    path=path.relative_to(ROOT),
                    required_text=required_text,
                ):
                    self.assertIn(required_text, text)
            self.assertEqual(text.count("Invoke-RestMethod"), 2)
            self.assertNotIn("curl.exe", text)
            self.assertNotIn('"extra_body": {', text)

    def test_markdown_relative_links_resolve(self) -> None:
        for path in REQUIRED_DOCS:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")

            for target in MARKDOWN_LINK.findall(text):
                target = target.strip().strip("<>")
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                target = target.split("#", 1)[0]
                if not target:
                    continue
                linked_path = path.parent / target
                with self.subTest(path=path.relative_to(ROOT), target=target):
                    self.assertTrue(linked_path.exists())

    def test_required_text_files_are_utf8_without_bom(self) -> None:
        paths = (
            ROOT / ".gitignore",
            API_DIR / ".env.example",
            API_DIR / "requirements.txt",
            *REQUIRED_DOCS,
            *sorted(API_DIR.rglob("*.py")),
        )
        for path in paths:
            if not path.is_file():
                continue
            data = path.read_bytes()
            relative_path = path.relative_to(ROOT)

            with self.subTest(path=relative_path):
                self.assertFalse(data.startswith(b"\xef\xbb\xbf"))
                try:
                    data.decode("utf-8")
                except UnicodeDecodeError as error:
                    self.fail(f"{relative_path} is not UTF-8: {error}")

    def test_docs_and_examples_do_not_contain_secrets(self) -> None:
        paths = (
            *REQUIRED_DOCS,
            *sorted(API_DIR.rglob("*.py")),
            API_DIR / ".env.example",
        )
        for path in paths:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")

            for pattern in SECRET_PATTERNS:
                with self.subTest(
                    path=path.relative_to(ROOT),
                    pattern=pattern.pattern,
                ):
                    self.assertIsNone(pattern.search(text))


if __name__ == "__main__":
    unittest.main()
