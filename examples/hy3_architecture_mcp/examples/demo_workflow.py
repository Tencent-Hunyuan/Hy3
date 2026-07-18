#!/usr/bin/env python
"""End-to-end demo: drive the Hy3 Architecture MCP pipeline via the MCP client SDK.

Example requirement (from the development plan):
  "为一个 30 人研发团队构建内部知识库，支持 Markdown 和 PDF，回答必须附带来源引用，
   文档每天更新，部署成本有限。"

Two run modes:

* ``--mock``  : spin up a built-in mock OpenAI-compatible endpoint returning canned
                structured outputs, so the whole pipeline is demonstrable WITHOUT a
                Hy3 deployment. Ideal for a quick "it works" / screen recording.
* (default)  : connect to a real Hy3 deployment. Requires HY3_BASE_URL / HY3_API_KEY /
               HY3_WORKSPACE_ROOT in the environment.

The script prints each step's structured result and never prints the API key.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

REQUIREMENT = (
    "为一个 30 人研发团队构建内部知识库，支持 Markdown 和 PDF，"
    "回答必须附带来源引用，文档每天更新，部署成本有限。"
)

# --- Canned mock responses (one per sequential Hy3 call) ----------------------
CLARIFY = {
    "understood_goals": ["为 30 人研发团队提供可检索、带来源引用的内部知识库"],
    "ambiguities": ["PDF 解析方案未定", "检索引擎选型未定", "部署预算上限未量化"],
    "missing_information": ["日均文档增量", "是否需要权限分级", "可接受硬件预算"],
    "clarifying_questions": [
        "预计日均新增文档量级（百/千/万）？",
        "是否需要按团队/项目做权限隔离？",
        "部署预算上限是多少（影响自建 vs 云托管）？",
    ],
    "acceptance_criteria": ["检索结果必须附原文位置引用", "Markdown 与 PDF 均可入库"],
    "assumptions": ["单租户内部使用", "文档每日批量更新可接受"],
}
PROPOSAL = {
    "title": "内部知识库检索系统技术方案",
    "executive_overview": "基于向量检索 + 关键词召回的混合方案，支持 Markdown/PDF 入库与来源引用。",
    "architecture": {
        "components": [
            "ingest-worker",
            "pdf-parser",
            "embedder",
            "vector-store",
            "hybrid-retriever",
            "api-gateway",
        ],
        "data_flow": [
            "文档上传 -> 解析分块 -> 向量化 -> 入库",
            "查询 -> 混合召回 -> 引用拼接 -> 返回",
        ],
        "interfaces": ["REST /search", "REST /documents", "内部 gRPC 解析队列"],
    },
    "technology_choices": [
        {"name": "BGE-M3", "rationale": "中英双语嵌入，召回质量好"},
        {"name": "Milvus", "rationale": "开源向量库，支持标量过滤与来源定位"},
        {"name": "Unstructured", "rationale": "统一 Markdown/PDF 解析并保留页码"},
    ],
    "alternatives": [
        {
            "name": "Elasticsearch kNN",
            "description": "用 ES 做向量检索",
            "tradeoffs": "省一个组件但召回略弱",
        },
    ],
    "non_functional_design": {
        "performance": ["p99 检索 < 500ms"],
        "reliability": ["ingest 失败重试 + 死信队列"],
        "observability": ["结构化日志 + 检索命中率指标"],
        "maintainability": ["解析/嵌入/检索解耦，可独立替换"],
    },
    "risks": [
        {
            "description": "PDF 表格解析准确率不稳",
            "severity": "medium",
            "mitigation": "加人工校验回流",
        },
    ],
    "open_questions": ["是否需要多语言检索", "冷启动向量库规模"],
}
REVIEW = {
    "verdict": "approve_with_changes",
    "score": 78,
    "strengths": ["混合召回兼顾语义与关键词", "组件解耦便于演进"],
    "findings": [
        {
            "id": "F-1",
            "severity": "medium",
            "dimension": "scalability",
            "evidence": "未说明 Milvus 分片与扩容策略",
            "impact": "文档量增长后召回延迟可能上升",
            "recommendation": "补充分片键与预分片方案",
        },
        {
            "id": "F-2",
            "severity": "high",
            "dimension": "reliability",
            "evidence": "ingest 死信队列未定义重投策略",
            "impact": "失败文档可能丢失",
            "recommendation": "定义重投次数上限与告警",
        },
    ],
    "missing_decisions": ["向量库备份与恢复策略", "引用定位的精度（字符/段落）"],
    "priority_actions": ["定义死信重投策略", "补充 Milvus 扩容方案"],
}
PLAN = {
    "milestones": [
        {
            "name": "M1 基础管线",
            "goal": "打通 Markdown 入库到检索的端到端流程",
            "tasks": [
                {
                    "id": "T1",
                    "title": "搭建 ingest-worker 与解析",
                    "description": "Markdown 分块 + 向量化 + 入库",
                    "dependencies": [],
                    "suggested_role": "后端工程师",
                    "estimated_effort": "5 人日",
                    "deliverables": ["ingest 服务", "分块策略文档"],
                    "acceptance_criteria": ["Markdown 可入库并被检索"],
                }
            ],
        },
        {
            "name": "M2 PDF 支持 + 评审修复",
            "goal": "接入 PDF 解析并完成评审高优修复",
            "tasks": [
                {
                    "id": "T2",
                    "title": "死信重投策略",
                    "description": "实现 F-2 的重投与告警",
                    "dependencies": ["T1"],
                    "suggested_role": "后端工程师",
                    "estimated_effort": "3 人日",
                    "deliverables": ["死信重投模块", "告警配置"],
                    "acceptance_criteria": ["失败文档自动重投并告警"],
                }
            ],
        },
    ],
    "critical_path": ["T1", "T2"],
    "parallelizable_work": ["前端检索界面", "可观测性接入"],
    "delivery_risks": ["PDF 解析准确率", "向量库扩容规划未定"],
    "definition_of_done": ["Markdown+PDF 均可入库检索", "检索结果附来源引用", "死信重投上线"],
}
MOCK_RESPONSES = [CLARIFY, PROPOSAL, REVIEW, PLAN]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _MockHandler(BaseHTTPRequestHandler):
    """Serve canned structured outputs in call order."""

    # Mutable container held on the class so increments persist across handler
    # instances (each HTTP request gets a fresh instance, so a plain int class
    # attribute would be shadowed by a per-instance copy and never advance).
    _counter: list[int] = [0]
    _lock = threading.Lock()

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("content-length", "0"))
        self.rfile.read(length)
        with self._lock:
            idx = min(self._counter[0], len(MOCK_RESPONSES) - 1)
            self._counter[0] += 1
            payload = MOCK_RESPONSES[idx]
        content = json.dumps(payload)
        body = json.dumps(
            {
                "id": "chatcmpl-mock",
                "object": "chat.completion",
                "model": "hy3",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            }
        ).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # silence stderr
        pass


def start_mock_hy3() -> tuple[str, threading.Thread, ThreadingHTTPServer]:
    port = _free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), _MockHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return f"http://127.0.0.1:{port}/v1", thread, httpd


def _result_text(result) -> str:
    return "".join(block.text for block in result.content if getattr(block, "type", "") == "text")


def _print_step(title: str, result) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")
    try:
        data = json.loads(_result_text(result))
        print(json.dumps(data, ensure_ascii=False, indent=2))
    except json.JSONDecodeError:
        print(_result_text(result)[:2000])


async def run_pipeline(base_url: str, api_key: str, workspace_root: str) -> int:
    env = {
        **os.environ,
        "HY3_BASE_URL": base_url,
        "HY3_API_KEY": api_key,
        "HY3_MODEL": os.environ.get("HY3_MODEL", "hy3"),
        "HY3_REASONING_EFFORT": os.environ.get("HY3_REASONING_EFFORT", "high"),
        "HY3_TIMEOUT_SECONDS": os.environ.get("HY3_TIMEOUT_SECONDS", "60"),
        "HY3_MAX_RETRIES": os.environ.get("HY3_MAX_RETRIES", "2"),
        "HY3_WORKSPACE_ROOT": workspace_root,
    }
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "hy3_architecture_mcp"],
        env=env,
    )
    print("Starting Hy3 Architecture MCP Server (stdio) ...")
    print(f"  HY3_BASE_URL      = {base_url}")
    print(f"  HY3_API_KEY       = {'***' if api_key and api_key != 'EMPTY' else 'EMPTY'}")
    print(f"  HY3_WORKSPACE_ROOT= {workspace_root}")

    async with (
        stdio_client(params) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        tools = await session.list_tools()
        print(f"\nDiscovered {len(tools.tools)} tools: {[t.name for t in tools.tools]}")

        # Step 1: clarify
        r1 = await session.call_tool(
            "clarify_requirements",
            {"requirement": REQUIREMENT, "max_questions": 5, "output_language": "zh-CN"},
        )
        _print_step("STEP 1  clarify_requirements", r1)
        if r1.isError:
            print("clarify_requirements failed; aborting pipeline.")
            return 1

        # Step 2: generate proposal (using the clarified requirement text)
        r2 = await session.call_tool(
            "generate_technical_proposal",
            {
                "requirements": REQUIREMENT + "（已澄清：30 人团队、需权限隔离、自建部署）",
                "constraints": ["部署成本有限", "支持 Markdown 与 PDF", "回答附来源引用"],
                "proposal_depth": "standard",
                "output_language": "zh-CN",
            },
        )
        _print_step("STEP 2  generate_technical_proposal", r2)
        if r2.isError:
            print("generate_technical_proposal failed; aborting pipeline.")
            return 1

        # Step 3: review the proposal
        proposal_text = _result_text(r2)
        r3 = await session.call_tool(
            "review_technical_proposal",
            {"proposal": proposal_text, "requirements": REQUIREMENT, "output_language": "zh-CN"},
        )
        _print_step("STEP 3  review_technical_proposal", r3)
        if r3.isError:
            print("review_technical_proposal failed; aborting pipeline.")
            return 1

        # Step 4: implementation plan
        r4 = await session.call_tool(
            "create_implementation_plan",
            {
                "proposal": proposal_text,
                "team_size": 30,
                "target_days": 60,
                "output_language": "zh-CN",
            },
        )
        _print_step("STEP 4  create_implementation_plan", r4)
        if r4.isError:
            print("create_implementation_plan failed.")
            return 1

    print("\nPipeline complete.")
    return 0


def main() -> int:
    import asyncio

    parser = argparse.ArgumentParser(description="Hy3 Architecture MCP end-to-end demo.")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use a built-in mock Hy3 endpoint (no Hy3 deployment needed).",
    )
    args = parser.parse_args()

    if args.mock:
        base_url, thread, httpd = start_mock_hy3()
        api_key = "mock-not-a-real-key"
        workspace_root = os.getcwd()
        print(f"[mock] Hy3 endpoint at {base_url}")
        try:
            return asyncio.run(run_pipeline(base_url, api_key, workspace_root))
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=5)
    else:
        base_url = os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
        api_key = os.environ.get("HY3_API_KEY", "EMPTY")
        workspace_root = os.environ.get("HY3_WORKSPACE_ROOT", "")
        if not workspace_root:
            print("ERROR: set HY3_WORKSPACE_ROOT (required by analyze_project_context / sandbox).")
            return 2
        return asyncio.run(run_pipeline(base_url, api_key, workspace_root))


if __name__ == "__main__":
    sys.exit(main())
