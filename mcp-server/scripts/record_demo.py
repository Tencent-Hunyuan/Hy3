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
"""Record a REAL hy3-mcp demo session into a transcript for the GIF renderer.

Launches ``python -m hy3_mcp`` as a subprocess (offline mode: deterministic
fake Hy3 backend, honestly labeled) and drives it over MCP stdio with the
raw JSON-RPC client.  Every displayed output is a genuine server response —
nothing is faked at the recording layer.

To re-record against the real model: export HY3_API_BASE / HY3_API_KEY,
drop HY3_MCP_OFFLINE, and run this script again (then render_gif.py).

Output: assets/demo_transcript.json (frames) + the same text on stdout.
"""

from __future__ import annotations

import json
import os
import sys
import textwrap
from pathlib import Path

MCP_SERVER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MCP_SERVER_DIR / "scripts"))

from raw_stdio_client import RawStdioClient  # noqa: E402  (zero mcp imports)

WIDTH = 76
MAX_BODY_LINES = 24


def _ascii(text: str) -> str:
    """GIF frames must be pure ASCII (recorder host has no CJK fonts)."""
    return text.encode("ascii", "ignore").decode()


def _wrap(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        line = _ascii(line.rstrip())
        if not line:
            out.append("")
            continue
        out.extend(textwrap.wrap(line, WIDTH) or [""])
    if len(out) > MAX_BODY_LINES:
        out = out[: MAX_BODY_LINES - 1] + ["... (truncated for the GIF)"]
    return out


def _frame(title: str, lines: list[str], tag: str = "") -> dict:
    """Build one GIF frame; ``tag`` (mode label) is appended to the title so
    every frame is explicitly labeled with the backend mode."""
    full = f"{title}  [{tag}]" if tag else title
    return {"title": _ascii(full), "lines": _wrap(lines)}


def main() -> int:
    offline = os.environ.get("HY3_API_BASE") is None or os.environ.get(
        "HY3_MCP_OFFLINE"
    )
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "PYTHONPATH": str(MCP_SERVER_DIR / "src"),
        "HY3_MCP_ROOT": str(MCP_SERVER_DIR),
    }
    for key in ("HY3_API_BASE", "HY3_API_KEY", "HY3_MODEL"):
        if os.environ.get(key):
            env[key] = os.environ[key]
    if offline:
        env["HY3_MCP_OFFLINE"] = "1"
    mode_label = (
        "OFFLINE DEMO MODE (fake Hy3 backend)" if offline else "REAL Hy3 backend"
    )
    # Short tag appended to EVERY frame title (README promises per-frame labels).
    tag = "OFFLINE DEMO MODE" if offline else "REAL Hy3 BACKEND"

    frames: list[dict] = [
        _frame(
            "hy3-mcp | Hy3 Research & Code Assistant (MCP server)",
            [
                f"*** {mode_label} ***",
                "",
                "This recording drives a REAL hy3-mcp server subprocess over MCP",
                "stdio, using an independent raw JSON-RPC client. No API key is",
                "configured, so the server uses its deterministic offline backend;",
                "every reply below is a genuine server response, clearly labeled.",
                "",
                "$ HY3_MCP_OFFLINE=1 python -m hy3_mcp     # stdio MCP server",
            ],
            tag=tag,
        )
    ]

    with RawStdioClient(
        [sys.executable, "-m", "hy3_mcp"], env=env, cwd=str(MCP_SERVER_DIR)
    ) as client:
        init = client.initialize()
        frames.append(
            _frame(
                "step 1/5 - initialize (MCP handshake)",
                [
                    '$ {"method": "initialize", ...}',
                    "",
                    f"-> server   : {init['serverInfo']['name']}",
                    f"-> protocol : {init['protocolVersion']}",
                    "-> transport: stdio (newline-delimited JSON-RPC)",
                ],
                tag=tag,
            )
        )

        tools = client.list_tools()["tools"]
        tool_lines = ['$ {"method": "tools/list"}', ""]
        for t in tools:
            # descriptions are bilingual "中文。 English."; show the English part
            english = t["description"].split("。", 1)[-1]
            summary = " ".join(_ascii(english).split())
            tool_lines.append(f"-> {t['name']:<14} {summary[:58]}")
        tool_lines.append("")
        tool_lines.append(f"-> {len(tools)} tools, all with param schemas + outputSchema")
        frames.append(_frame("step 2/5 - tools/list (5 tools)", tool_lines, tag=tag))

        status = client.call_tool("hy3_status")["structuredContent"]
        # Privacy: keep the recorder host's absolute path out of the committed
        # transcript/GIF; the placeholder is self-labeling in the frame.
        status["sandbox_root"] = ".../Hy3/mcp-server (abs path redacted)"
        frames.append(
            _frame(
                "step 3/5 - call hy3_status (diagnostics, no LLM)",
                ['$ tools/call hy3_status {}', ""]
                + json.dumps(status, indent=2).splitlines(),
                tag=tag,
            )
        )

        review = client.call_tool("review_code", {"path": "examples/diffs/demo.diff"})
        rsc = review["structuredContent"]
        stats = rsc["stats"]
        frames.append(
            _frame(
                "step 4/5 - call review_code on examples/diffs/demo.diff",
                [
                    '$ tools/call review_code {"path": "examples/diffs/demo.diff"}',
                    "",
                    f"-> stats: {len(stats['files'])} files, {stats['hunks']} hunks, "
                    f"+{stats['added_lines']}/-{stats['removed_lines']} lines, "
                    f"{len(rsc['heuristic_flags'])} heuristic flags",
                    "",
                ]
                + rsc["markdown"].splitlines(),
                tag=tag,
            )
        )

        docs = client.call_tool(
            "ask_docs",
            {
                "question": "What is the context length of Hy3?",
                "docs_path": "examples/docs",
            },
        )
        dsc = docs["structuredContent"]
        cites = ", ".join(
            f"{c['file'].split('/')[-1]}#{c['chunk_id']}" for c in dsc["citations"]
        )
        frames.append(
            _frame(
                "step 5/5 - call ask_docs (knowledge-base Q&A)",
                [
                    '$ tools/call ask_docs {"question": "What is the context length',
                    '  of Hy3?", "docs_path": "examples/docs"}',
                    "",
                ]
                + dsc["markdown"].splitlines()
                + ["", f"-> citations: {cites}"],
                tag=tag,
            )
        )

    frames.append(
        _frame(
            "switch to the real Hy3 backend (one env var)",
            [
                "$ pip install ./mcp-server      # or: uvx --from ./mcp-server hy3-mcp",
                "",
                "# self-hosted (vLLM / SGLang, upstream README quickstart):",
                "$ export HY3_API_BASE=http://127.0.0.1:8000/v1",
                "",
                "# or Tencent cloud OpenAI-compatible endpoint:",
                "$ export HY3_API_BASE=https://api.hunyuan.cloud.tencent.com/v1",
                "$ export HY3_API_KEY=<your key from the console>",
                "",
                "Same code path, real model. Re-record: scripts/record_demo.py",
                "then scripts/render_gif.py.",
            ],
            tag=tag,
        )
    )

    out_path = MCP_SERVER_DIR / "assets" / "demo_transcript.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(frames, indent=2), encoding="utf-8")

    for frame in frames:  # mirror to stdout = run evidence
        print("=" * 78)
        print(frame["title"])
        print("-" * 78)
        for line in frame["lines"]:
            print(line)
    print("=" * 78)
    print(f"[record_demo] wrote {len(frames)} frames -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
