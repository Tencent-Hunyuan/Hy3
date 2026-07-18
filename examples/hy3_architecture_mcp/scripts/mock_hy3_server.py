#!/usr/bin/env python
"""Standalone mock Hy3 endpoint for MCP client verification without a real deployment.

Usage:
    python scripts/mock_hy3_server.py [--port 8765]

The server listens on http://127.0.0.1:<port>/v1/chat/completions and returns
canned structured responses matching the Hy3 Architecture MCP tool schemas.
It detects which tool is being called by inspecting the system prompt in the
request, so tools can be called in any order.

Point your .mcp.json HY3_BASE_URL at http://127.0.0.1:<port>/v1 and
HY3_API_KEY at EMPTY, then open the project in CodeBuddy / WorkBuddy / Cursor.
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CLARIFY = {
    "understood_goals": ["为研发团队提供可检索、带来源引用的内部知识库"],
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
        "components": ["ingest-worker", "pdf-parser", "embedder", "vector-store", "hybrid-retriever", "api-gateway"],
        "data_flow": ["文档上传 -> 解析分块 -> 向量化 -> 入库", "查询 -> 混合召回 -> 引用拼接 -> 返回"],
        "interfaces": ["REST /search", "REST /documents", "内部 gRPC 解析队列"],
    },
    "technology_choices": [
        {"name": "BGE-M3", "rationale": "中英双语嵌入，召回质量好"},
        {"name": "Milvus", "rationale": "开源向量库，支持标量过滤与来源定位"},
        {"name": "Unstructured", "rationale": "统一 Markdown/PDF 解析并保留页码"},
    ],
    "alternatives": [{"name": "Elasticsearch kNN", "description": "用 ES 做向量检索", "tradeoffs": "省一个组件但召回略弱"}],
    "non_functional_design": {
        "performance": ["p99 检索 < 500ms"],
        "reliability": ["ingest 失败重试 + 死信队列"],
        "observability": ["结构化日志 + 检索命中率指标"],
        "maintainability": ["解析/嵌入/检索解耦，可独立替换"],
    },
    "risks": [{"description": "PDF 表格解析准确率不稳", "severity": "medium", "mitigation": "加人工校验回流"}],
    "open_questions": ["是否需要多语言检索", "冷启动向量库规模"],
}
REVIEW = {
    "verdict": "approve_with_changes",
    "score": 78,
    "strengths": ["混合召回兼顾语义与关键词", "组件解耦便于演进"],
    "findings": [
        {"id": "F-1", "severity": "medium", "dimension": "scalability", "evidence": "未说明分片与扩容策略", "impact": "文档量增长后召回延迟可能上升", "recommendation": "补充分片键与预分片方案"},
        {"id": "F-2", "severity": "high", "dimension": "reliability", "evidence": "死信队列未定义重投策略", "impact": "失败文档可能丢失", "recommendation": "定义重投次数上限与告警"},
    ],
    "missing_decisions": ["向量库备份与恢复策略", "引用定位的精度（字符/段落）"],
    "priority_actions": ["定义死信重投策略", "补充扩容方案"],
}
PLAN = {
    "milestones": [
        {"name": "M1 基础管线", "goal": "打通入库到检索的端到端流程", "tasks": [
            {"id": "T1", "title": "搭建 ingest-worker 与解析", "description": "分块 + 向量化 + 入库", "dependencies": [], "suggested_role": "后端工程师", "estimated_effort": "5 人日", "deliverables": ["ingest 服务", "分块策略文档"], "acceptance_criteria": ["可入库并被检索"]}
        ]},
        {"name": "M2 评审修复", "goal": "完成评审高优修复", "tasks": [
            {"id": "T2", "title": "死信重投策略", "description": "实现重投与告警", "dependencies": ["T1"], "suggested_role": "后端工程师", "estimated_effort": "3 人日", "deliverables": ["死信重投模块", "告警配置"], "acceptance_criteria": ["失败文档自动重投并告警"]}
        ]},
    ],
    "critical_path": ["T1", "T2"],
    "parallelizable_work": ["前端检索界面", "可观测性接入"],
    "delivery_risks": ["解析准确率", "扩容规划未定"],
    "definition_of_done": ["均可入库检索", "检索结果附来源引用", "死信重投上线"],
}
ANALYZE = {
    "summary": "项目包含一个基于 MCP 协议的架构分析服务器，核心模块包括 Hy3 客户端、配置管理、5 个工具和文件沙箱。",
    "key_components": [
        {"name": "hy3_client.py", "responsibility": "封装 Hy3 API 调用，含重试与结构化校验"},
        {"name": "server.py", "responsibility": "FastMCP 服务器，注册 5 个 Tool"},
        {"name": "tools/project_context.py", "responsibility": "文件沙箱读取与分析"},
    ],
    "tech_stack": ["Python 3.10+", "MCP SDK 1.27+", "Pydantic 2.7+", "httpx"],
    "observations": ["架构清晰，职责分离良好", "安全边界完整", "测试覆盖全面"],
    "suggested_actions": ["考虑添加流式输出支持", "可增加缓存层减少重复 API 调用"],
}


def _pick_response(system_prompt: str) -> dict:
    """Pick a canned response based on keywords in the system prompt."""
    sp = system_prompt.lower()
    if "clarif" in sp or "ambiguit" in sp:
        return CLARIFY
    if "proposal" in sp or "technical_proposal" in sp:
        return PROPOSAL
    if "review" in sp:
        return REVIEW
    if "plan" in sp or "implementation" in sp or "milestone" in sp:
        return PLAN
    if "analyz" in sp or "context" in sp or "project" in sp:
        return ANALYZE
    return CLARIFY  # fallback


class MockHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("content-length", "0"))
        raw = self.rfile.read(length)
        try:
            req = json.loads(raw)
            system_prompt = ""
            for msg in req.get("messages", []):
                if msg.get("role") == "system":
                    system_prompt = msg.get("content", "")
                    break
        except Exception:
            system_prompt = ""

        payload = _pick_response(system_prompt)
        content = json.dumps(payload, ensure_ascii=False)
        body = json.dumps(
            {
                "id": "chatcmpl-mock",
                "object": "chat.completion",
                "model": req.get("model", "hy3"),
                "choices": [
                    {"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            }
        ).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # silence stderr noise
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Standalone mock Hy3 endpoint for MCP verification.")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on (default: 8765)")
    args = parser.parse_args()

    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), MockHandler)
    print(f"[mock] Hy3 endpoint listening on http://127.0.0.1:{args.port}/v1")
    print(f"[mock] Set HY3_BASE_URL=http://127.0.0.1:{args.port}/v1 in .mcp.json")
    print(f"[mock] Set HY3_API_KEY=EMPTY in .mcp.json")
    print(f"[mock] Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[mock] Shutting down.")
        httpd.shutdown()
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
