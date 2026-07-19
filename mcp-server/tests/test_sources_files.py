# Copyright 2026 Tencent Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Data source #1: sandbox security, robustness, deterministic retrieval."""

from __future__ import annotations

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from hy3_mcp.sources.files import SafeFileReader, chunk_text, rank_chunks


@pytest.fixture
def sandbox(tmp_path):
    (tmp_path / "ok.txt").write_text("hello sandbox", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "inner.md").write_text("# inner doc\ninner text", encoding="utf-8")
    return SafeFileReader(tmp_path)


def test_reads_inside_sandbox(sandbox):
    assert sandbox.read_text("ok.txt") == "hello sandbox"
    assert sandbox.read_text("sub/inner.md").startswith("# inner doc")


@pytest.mark.parametrize(
    "bad", ["../outside.txt", "../../etc/passwd", "/etc/passwd", "sub/../../escape"]
)
def test_sandbox_blocks_escape(sandbox, bad):
    with pytest.raises(ToolError, match="sandbox|empty path"):
        sandbox.resolve(bad)


def test_sandbox_blocks_symlink_escape(sandbox, tmp_path):
    link = tmp_path / "sneaky"
    link.symlink_to("/etc")
    with pytest.raises(ToolError, match="sandbox"):
        sandbox.resolve("sneaky/passwd")


def test_extra_root_allows_docs_dir_outside_root(tmp_path):
    """An extra root (absolute HY3_MCP_DOCS_DIR) is readable and listable."""
    root = tmp_path / "root"
    docs = tmp_path / "docs"
    root.mkdir()
    docs.mkdir()
    (docs / "kb.md").write_text("# kb\nHy3 doc", encoding="utf-8")
    reader = SafeFileReader(root, extra_roots=(docs,))
    assert reader.read_text(str(docs / "kb.md")) == "# kb\nHy3 doc"
    assert [p.name for p in reader.list_docs(str(docs))] == ["kb.md"]
    assert reader.relative(docs / "kb.md") == "kb.md"


def test_extra_root_still_blocks_escapes(tmp_path):
    """Traversal and symlinks out of the extra root remain rejected."""
    root = tmp_path / "root"
    docs = tmp_path / "docs"
    outside = tmp_path / "outside"
    for d in (root, docs, outside):
        d.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    (docs / "link.txt").symlink_to(outside / "secret.txt")
    reader = SafeFileReader(root, extra_roots=(docs,))
    with pytest.raises(ToolError, match="sandbox"):
        reader.resolve(str(docs) + "/../outside/secret.txt")
    with pytest.raises(ToolError, match="sandbox"):
        reader.resolve(str(docs / "link.txt"))


def test_empty_path_rejected(sandbox):
    with pytest.raises(ToolError, match="empty path"):
        sandbox.resolve("  ")


def test_missing_file_clean_error(sandbox):
    with pytest.raises(ToolError, match="not found"):
        sandbox.read_text("ghost.txt")


def test_size_cap(tmp_path):
    reader = SafeFileReader(tmp_path, max_bytes=64)
    (tmp_path / "big.txt").write_text("x" * 100, encoding="utf-8")
    with pytest.raises(ToolError, match="too large"):
        reader.read_text("big.txt")


def test_non_utf8_does_not_crash(sandbox, tmp_path):
    (tmp_path / "bin.txt").write_bytes(b"caf\xe9 \xff\xfe data")
    text = sandbox.read_text("bin.txt")
    assert "data" in text  # decoded with replacement, no exception


def test_list_docs_filters_and_sorts(sandbox, tmp_path):
    (tmp_path / "z.md").write_text("z", encoding="utf-8")
    (tmp_path / "a.py").write_text("code", encoding="utf-8")
    docs = sandbox.list_docs()
    names = [p.name for p in docs]
    assert "a.py" not in names  # extension filter
    assert docs == sorted(docs)  # deterministic full-path order


def test_chunk_text_splits_and_caps():
    text = "# Title\n\npara one\n\n## Section\n\n" + ("word " * 400)
    chunks = chunk_text(text, source="doc.md", max_chars=300)
    assert len(chunks) >= 2
    assert all(len(c.text) <= 300 for c in chunks)
    assert [c.chunk_id for c in chunks] == list(range(len(chunks)))
    assert all(c.source == "doc.md" for c in chunks)


def test_rank_chunks_deterministic_english():
    chunks = chunk_text(
        "# Intro\n\nThis project uses widgets.\n\n"
        "# Context\n\nHy3 supports a context length of 256K tokens.\n\n"
        "# Other\n\nNothing relevant here at all.",
        source="doc.md",
        max_chars=80,
    )
    first = rank_chunks("What is the context length of Hy3?", chunks, top_k=2)
    second = rank_chunks("What is the context length of Hy3?", chunks, top_k=2)
    assert [s.chunk.chunk_id for s in first] == [s.chunk.chunk_id for s in second]
    assert "256K" in first[0].chunk.text


def test_rank_chunks_chinese_bigrams():
    chunks = chunk_text(
        "# 简介\n\n本项目是一个演示。\n\n# 上下文\n\nHy3 支持 256K 上下文长度。\n\n"
        "# 其他\n\n与问题无关的内容。",
        source="zh.md",
        max_chars=40,
    )
    ranked = rank_chunks("上下文长度是多少", chunks, top_k=1)
    assert ranked and "256K" in ranked[0].chunk.text


def test_rank_chunks_no_hits_returns_empty():
    chunks = chunk_text("alpha beta gamma", source="x.md")
    assert rank_chunks("zzz qqq", chunks, top_k=3) == []
