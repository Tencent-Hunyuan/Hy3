from __future__ import annotations

import os
import subprocess
import tempfile
import time
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from hy3_repo_scout.tools import _BINARY_SAMPLE_BYTES, RepoTools, ToolError


class RepoToolsTests(TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "app.py").write_text(
            "alpha = 1\nBeta = alpha + 1\nprint(Beta)\n",
            encoding="utf-8",
        )
        (self.root / "README.md").write_text("Alpha project\n", encoding="utf-8")
        self.tools = RepoTools(self.root, max_file_bytes=128)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_schemas_and_dispatch_are_structured(self) -> None:
        names = {schema["function"]["name"] for schema in self.tools.schemas}
        self.assertEqual(names, {"list_files", "search_text", "read_file", "git_diff"})
        self.assertTrue(
            all(
                schema["function"]["parameters"]["additionalProperties"] is False
                for schema in self.tools.schemas
            )
        )

        result = self.tools.execute("list_files", {"pattern": "**/*.py"})
        self.assertEqual(result["files"], ["src/app.py"])
        unknown = self.tools.execute("write_file", {"path": "src/app.py"})
        self.assertEqual(unknown["error"]["code"], "unknown_tool")
        invalid = self.tools.execute("read_file", {"path": "src/app.py", "extra": True})
        self.assertEqual(invalid["error"]["code"], "invalid_arguments")

    def test_repo_summary_does_not_expose_the_absolute_path(self) -> None:
        self.assertIn(self.root.name, self.tools.repo_summary)
        self.assertNotIn(str(self.root.parent), self.tools.repo_summary)

    def test_generated_directories_are_skipped_but_env_templates_are_readable(self) -> None:
        generated = self.root / ".venv"
        generated.mkdir()
        (generated / "ignored.py").write_text("needle\n", encoding="utf-8")
        package_metadata = self.root / "package.egg-info"
        package_metadata.mkdir()
        (package_metadata / "PKG-INFO").write_text("needle\n", encoding="utf-8")
        artifacts = self.root / "examples" / "hy3-repo-scout" / "demos" / "artifacts"
        artifacts.mkdir(parents=True)
        (artifacts / "old-report.md").write_text("needle\n", encoding="utf-8")
        (self.root / ".env.example").write_text("TOKEN=replace-me\n", encoding="utf-8")

        listing = self.tools.list_files()

        self.assertIn(".env.example", listing["files"])
        self.assertNotIn(".venv/ignored.py", listing["files"])
        self.assertNotIn("package.egg-info/PKG-INFO", listing["files"])
        self.assertFalse(any("demos/artifacts" in path for path in listing["files"]))
        self.assertEqual(self.tools.search_text("needle")["matches"], [])
        for path in (
            ".venv/ignored.py",
            "package.egg-info/PKG-INFO",
            "examples/hy3-repo-scout/demos/artifacts/old-report.md",
        ):
            with self.subTest(path=path), self.assertRaises(ToolError) as caught:
                self.tools.read_file(path)
            self.assertEqual(caught.exception.code, "sensitive")

    def test_git_metadata_is_blocked_for_directories_and_worktree_files(self) -> None:
        self._git("init", "-q")
        with self.assertRaises(ToolError) as caught:
            self.tools.read_file(".git/config")
        self.assertEqual(caught.exception.code, "sensitive")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".git").write_text(
                "gitdir: /private/host/path/.git/worktrees/example\n",
                encoding="utf-8",
            )
            worktree_tools = RepoTools(root)
            with self.assertRaises(ToolError) as caught:
                worktree_tools.read_file(".git")
            self.assertEqual(caught.exception.code, "sensitive")
            self.assertNotIn(".git", worktree_tools.list_files()["files"])

    def test_read_file_returns_numbered_bounded_lines_and_stats(self) -> None:
        result = self.tools.read_file("src/app.py", start_line=2, end_line=3)

        self.assertEqual(result["path"], "src/app.py")
        self.assertEqual(result["start_line"], 2)
        self.assertEqual(result["end_line"], 3)
        self.assertEqual(result["total_lines"], 3)
        self.assertEqual(result["content"], "L2: Beta = alpha + 1\nL3: print(Beta)")
        self.assertFalse(result["truncated"])
        self.assertEqual(self.tools.files_read, ["src/app.py"])
        self.assertEqual(self.tools.stats["read_calls"], 1)

    def test_utf8_sample_ending_mid_character_is_not_binary(self) -> None:
        path = self.root / "unicode-boundary.txt"
        path.write_text("a" * (_BINARY_SAMPLE_BYTES - 1) + "中\n", encoding="utf-8")

        result = RepoTools(self.root).read_file("unicode-boundary.txt")

        self.assertEqual(result["total_lines"], 1)
        self.assertIn("中", result["content"])

    def test_rejects_traversal_absolute_paths_and_invalid_ranges(self) -> None:
        outside = self.root.parent / "outside.txt"
        outside.write_text("not repository data", encoding="utf-8")
        self.addCleanup(outside.unlink)

        for path in ("../outside.txt", str(outside), "src\\app.py"):
            with self.subTest(path=path), self.assertRaises(ToolError) as caught:
                self.tools.read_file(path)
            self.assertEqual(caught.exception.code, "unsafe_path")
        with self.assertRaises(ToolError) as caught:
            self.tools.read_file("src/app.py", start_line=3, end_line=2)
        self.assertEqual(caught.exception.code, "invalid_range")

    def test_blocks_external_and_sensitive_symlink_targets(self) -> None:
        external_directory = tempfile.TemporaryDirectory()
        self.addCleanup(external_directory.cleanup)
        external = Path(external_directory.name) / "external.txt"
        external.write_text("outside secret", encoding="utf-8")
        (self.root / "external-link.txt").symlink_to(external)
        (self.root / ".env").write_text("TOKEN=do-not-read\n", encoding="utf-8")
        (self.root / "innocent.txt").symlink_to(self.root / ".env")

        for path in ("external-link.txt", "innocent.txt"):
            with self.subTest(path=path), self.assertRaises(ToolError) as caught:
                self.tools.read_file(path)
            self.assertIn(caught.exception.code, {"unsafe_path", "sensitive"})

        listing = self.tools.list_files()
        self.assertNotIn("external-link.txt", listing["files"])
        self.assertNotIn("innocent.txt", listing["files"])
        search = self.tools.search_text("secret")
        self.assertEqual(search["matches"], [])

    def test_sensitive_binary_and_large_files_are_filtered_everywhere(self) -> None:
        (self.root / "secrets.yaml").write_text("password: visible\n", encoding="utf-8")
        (self.root / "image.bin").write_bytes(b"prefix\x00payload")
        (self.root / "huge.txt").write_text("needle " * 30, encoding="utf-8")

        expected_codes = {
            "secrets.yaml": "sensitive",
            "image.bin": "binary",
            "huge.txt": "too_large",
        }
        for path, expected_code in expected_codes.items():
            with self.subTest(path=path), self.assertRaises(ToolError) as caught:
                self.tools.read_file(path)
            self.assertEqual(caught.exception.code, expected_code)

        listing = self.tools.list_files()
        self.assertTrue(expected_codes.keys().isdisjoint(listing["files"]))
        self.assertEqual(listing["blocked"], {"binary": 1, "sensitive": 1, "too_large": 1})
        search = self.tools.search_text("needle")
        self.assertEqual(search["matches"], [])
        self.assertEqual(search["blocked"], {"binary": 1, "sensitive": 1, "too_large": 1})

    def test_fifo_is_rejected_without_blocking(self) -> None:
        if not hasattr(os, "mkfifo"):
            self.skipTest("FIFOs are not available on this platform")
        fifo = self.root / "blocked.fifo"
        os.mkfifo(fifo)

        started = time.monotonic()
        with self.assertRaises(ToolError) as caught:
            self.tools.read_file("blocked.fifo")

        self.assertEqual(caught.exception.code, "unsafe_path")
        self.assertLess(time.monotonic() - started, 1.0)
        self.assertNotIn("blocked.fifo", self.tools.list_files()["files"])

    def test_search_is_literal_bounded_and_returns_citations(self) -> None:
        insensitive = self.tools.search_text("alpha", pattern="**/*.py")
        self.assertEqual([match["line"] for match in insensitive["matches"]], [1, 2])
        self.assertEqual(insensitive["matches"][0]["citation"], "[src/app.py:L1-L1]")

        sensitive = self.tools.search_text(
            "alpha",
            pattern="**/*.py",
            case_sensitive=True,
            limit=1,
        )
        self.assertEqual(sensitive["count"], 1)
        self.assertTrue(sensitive["truncated"])
        with self.assertRaises(ToolError):
            self.tools.search_text("alpha\nbeta")

    def test_git_diff_omits_sensitive_binary_and_large_changes(self) -> None:
        (self.root / ".env").write_text("TOKEN=old\n", encoding="utf-8")
        (self.root / ":(top).env").write_text("literal path = old\n", encoding="utf-8")
        (self.root / "blob.bin").write_bytes(b"old\x00binary")
        (self.root / "huge.txt").write_text("a" * 129, encoding="utf-8")
        self._git("init", "-q")
        self._git("config", "user.email", "tests@example.invalid")
        self._git("config", "user.name", "Repo Tools Tests")
        self._git("add", ".")
        self._git("commit", "-qm", "baseline")

        (self.root / "src" / "app.py").write_text("alpha = 2\n", encoding="utf-8")
        (self.root / ".env").write_text("TOKEN=new\n", encoding="utf-8")
        (self.root / ":(top).env").write_text("literal path = new\n", encoding="utf-8")
        (self.root / "blob.bin").write_bytes(b"new\x00binary")
        (self.root / "huge.txt").write_text("b" * 129, encoding="utf-8")

        result = self.tools.git_diff()

        self.assertEqual(result["files"], [":(top).env", "src/app.py"])
        self.assertIn("+literal path = new", result["diff"])
        self.assertIn("+alpha = 2", result["diff"])
        self.assertNotIn("TOKEN", result["diff"])
        self.assertNotIn("new\\x00binary", result["diff"])
        self.assertEqual(result["blocked"], {"binary": 1, "sensitive": 1, "too_large": 1})

    def test_git_diff_rejects_option_like_revisions_and_non_git_roots(self) -> None:
        with self.assertRaises(ToolError) as caught:
            self.tools.git_diff(base="--output=/tmp/leak")
        self.assertEqual(caught.exception.code, "invalid_revision")
        with self.assertRaises(ToolError) as caught:
            self.tools.git_diff()
        self.assertEqual(caught.exception.code, "git_error")

    def test_git_diff_ignores_external_index_environment(self) -> None:
        self._git("init", "-q")
        self._git("config", "user.email", "tests@example.invalid")
        self._git("config", "user.name", "Repo Scout Tests")
        self._git("add", ".")
        self._git("commit", "-qm", "baseline")
        alternate_index = self.root.parent / f"{self.root.name}-alternate-index"
        self.addCleanup(alternate_index.unlink, missing_ok=True)
        environment = {**os.environ, "GIT_INDEX_FILE": str(alternate_index)}
        subprocess.run(
            ["git", "read-tree", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            env=environment,
        )
        secret = b"OUTSIDE INDEX SECRET\n"
        object_id = subprocess.run(
            ["git", "hash-object", "-w", "--stdin"],
            cwd=self.root,
            input=secret,
            check=True,
            capture_output=True,
        ).stdout.decode().strip()
        subprocess.run(
            ["git", "update-index", "--add", "--cacheinfo", "100644", object_id, "outside.txt"],
            cwd=self.root,
            check=True,
            capture_output=True,
            env=environment,
        )

        with patch.dict(os.environ, {"GIT_INDEX_FILE": str(alternate_index)}):
            result = self.tools.git_diff(staged=True)

        self.assertNotIn("OUTSIDE INDEX SECRET", result["diff"])
        self.assertEqual(result["files"], [])

    def test_git_diff_refuses_configured_filters_without_executing_them(self) -> None:
        (self.root / ".gitattributes").write_text("src/app.py filter=evil\n", encoding="utf-8")
        self._git("init", "-q")
        self._git("config", "user.email", "tests@example.invalid")
        self._git("config", "user.name", "Repo Scout Tests")
        self._git("add", ".")
        self._git("commit", "-qm", "baseline")
        self._git("config", "filter.evil.clean", "sh -c 'touch FILTER-RAN; cat'")
        (self.root / "src" / "app.py").write_text("alpha = 2\n", encoding="utf-8")

        with self.assertRaises(ToolError) as caught:
            self.tools.git_diff()

        self.assertEqual(caught.exception.code, "git_filter")
        self.assertFalse((self.root / "FILTER-RAN").exists())

    def test_git_diff_refuses_external_metadata_and_object_alternates(self) -> None:
        with tempfile.TemporaryDirectory() as external_directory:
            external = Path(external_directory)
            (external / "outside.txt").write_text("TOP SECRET OUTSIDE ROOT\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q"], cwd=external, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.email=test@example.invalid",
                    "-c",
                    "user.name=Test",
                    "add",
                    ".",
                ],
                cwd=external,
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.email=test@example.invalid",
                    "-c",
                    "user.name=Test",
                    "commit",
                    "-qm",
                    "outside",
                ],
                cwd=external,
                check=True,
            )
            with tempfile.TemporaryDirectory() as worktree_parent:
                linked = Path(worktree_parent) / "linked"
                subprocess.run(
                    ["git", "worktree", "add", "-q", "-b", "linked-test", str(linked)],
                    cwd=external,
                    check=True,
                )
                (linked / "outside.txt").write_text("linked change\n", encoding="utf-8")

                linked_result = RepoTools(linked).git_diff()

                self.assertEqual(linked_result["files"], ["outside.txt"])
                self.assertIn("+linked change", linked_result["diff"])

                admin_dir = Path(
                    subprocess.run(
                        ["git", "rev-parse", "--absolute-git-dir"],
                        cwd=linked,
                        check=True,
                        capture_output=True,
                        text=True,
                    ).stdout.strip()
                )
                index = admin_dir / "index"
                outside_index = Path(worktree_parent) / "outside-index"
                outside_index.write_bytes(index.read_bytes())
                index.unlink()
                index.symlink_to(outside_index)
                try:
                    with self.assertRaises(ToolError) as caught:
                        RepoTools(linked).git_diff()
                    self.assertEqual(caught.exception.code, "git_error")
                finally:
                    index.unlink()
                    outside_index.replace(index)

                objects = external / ".git" / "objects"
                outside_objects = Path(worktree_parent) / "outside-objects"
                objects.rename(outside_objects)
                objects.symlink_to(outside_objects, target_is_directory=True)
                try:
                    with self.assertRaises(ToolError) as caught:
                        RepoTools(linked).git_diff()
                    self.assertEqual(caught.exception.code, "git_error")
                finally:
                    objects.unlink()
                    outside_objects.rename(objects)

            with tempfile.TemporaryDirectory() as selected_directory:
                selected = Path(selected_directory)
                (selected / ".git").write_text(
                    f"gitdir: {external / '.git'}\n",
                    encoding="utf-8",
                )
                tools = RepoTools(selected)
                with self.assertRaises(ToolError) as caught:
                    tools.git_diff()
                self.assertEqual(caught.exception.code, "git_error")
                self.assertNotIn("TOP SECRET OUTSIDE ROOT", str(caught.exception))

        self._git("init", "-q")
        self._git("config", "user.email", "tests@example.invalid")
        self._git("config", "user.name", "Repo Scout Tests")
        self._git("add", ".")
        self._git("commit", "-qm", "baseline")
        info = self.root / ".git" / "objects" / "info"
        info.mkdir(exist_ok=True)
        (info / "alternates").write_text(f"{self.root.parent}\n", encoding="utf-8")

        with self.assertRaises(ToolError) as caught:
            self.tools.git_diff()
        self.assertEqual(caught.exception.code, "git_error")

    def test_git_diff_caps_changed_path_processing(self) -> None:
        self._git("init", "-q")
        self._git("config", "user.email", "tests@example.invalid")
        self._git("config", "user.name", "Repo Scout Tests")
        self._git("add", ".")
        self._git("commit", "-qm", "baseline")
        for index in range(4):
            (self.root / f"file-{index}.txt").write_text("changed\n", encoding="utf-8")
        self._git("add", ".")

        with patch("hy3_repo_scout.tools.MAX_DIFF_PATHS", 2):
            result = self.tools.git_diff(staged=True)

        self.assertTrue(result["truncated"])
        self.assertLessEqual(len(result["files"]), 2)

    def test_git_runner_enforces_output_and_deadline_limits(self) -> None:
        with self.assertRaises(ToolError) as caught:
            self.tools._git(["--version"], max_output_bytes=1)
        self.assertEqual(caught.exception.code, "too_large")

        with self.assertRaises(ToolError) as caught:
            self.tools._git(["--version"], deadline=time.monotonic() - 1)
        self.assertEqual(caught.exception.code, "git_timeout")

    def test_git_runner_ignores_all_caller_path_entries(self) -> None:
        marker = self.root / "FAKE-GIT-RAN"
        fake_git = self.root / "git"
        fake_git.write_text(f"#!/bin/sh\n/bin/touch '{marker}'\n", encoding="utf-8")
        fake_git.chmod(0o755)
        evil_directory = tempfile.TemporaryDirectory(dir=self.root.parent)
        self.addCleanup(evil_directory.cleanup)
        sibling_git = Path(evil_directory.name) / "git"
        sibling_git.write_text(f"#!/bin/sh\n/bin/touch '{marker}'\n", encoding="utf-8")
        sibling_git.chmod(0o755)
        hostile_path = os.pathsep.join(
            (evil_directory.name, str(self.root), ".", os.environ.get("PATH", ""))
        )

        with patch.dict(os.environ, {"PATH": hostile_path}):
            tools = RepoTools(self.root)
            version = tools._git(["--version"])

        self.assertIn(b"git version", version)
        self.assertFalse(marker.exists())
        self.assertFalse(str(tools._git_executable).startswith(str(self.root)))

    def test_git_runner_closes_pipe_streams(self) -> None:
        original_popen = subprocess.Popen
        processes: list[subprocess.Popen[bytes]] = []

        def start_process(*args: object, **kwargs: object) -> subprocess.Popen[bytes]:
            process = original_popen(*args, **kwargs)
            processes.append(process)
            return process

        with patch("hy3_repo_scout.tools.subprocess.Popen", side_effect=start_process):
            self.tools._git(["--version"])

        self.assertEqual(len(processes), 1)
        self.assertTrue(processes[0].stdout.closed)
        self.assertTrue(processes[0].stderr.closed)

    def test_git_runner_kills_lingering_process_group_on_timeout(self) -> None:
        if os.name != "posix":
            self.skipTest("POSIX process groups are required for this test")
        started = time.monotonic()

        with self.assertRaises(ToolError) as caught:
            self.tools._git(
                ["-c", "alias.linger=!sh -c 'sleep 5 & wait'", "linger"],
                deadline=time.monotonic() + 0.2,
            )

        self.assertEqual(caught.exception.code, "git_timeout")
        self.assertLess(time.monotonic() - started, 2.0)

    def _git(self, *arguments: str) -> None:
        subprocess.run(
            ["git", *arguments],
            cwd=self.root,
            check=True,
            capture_output=True,
        )
