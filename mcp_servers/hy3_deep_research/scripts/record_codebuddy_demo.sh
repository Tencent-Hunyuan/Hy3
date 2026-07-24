#!/usr/bin/env bash
set -euo pipefail

if ! command -v codebuddy >/dev/null 2>&1; then
  echo "codebuddy CLI is required" >&2
  exit 1
fi
if [[ -z "${HY3_API_KEY:-}" ]]; then
  echo "HY3_API_KEY must be set (use EMPTY for an unauthenticated local endpoint)" >&2
  exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
package_dir="$(cd "${script_dir}/.." && pwd)"

codebuddy --mcp-config "${package_dir}/examples/codebuddy.mcp.json" -p +  "必须调用 hy3-deep-research 的 deep_research 工具，研究 Hy3 在长上下文任务中的特点；使用 4 个来源，中文输出，并保留来源引用。"

