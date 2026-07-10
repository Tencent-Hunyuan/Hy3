#!/bin/bash
# Hy3 API Mock Test Runner
# 运行全部 mock 测试并保存日志

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/test_output"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$OUTPUT_DIR"

echo "========================================"
echo "  Hy3 API Mock Test Suite"
echo "  Started at: $(date)"
echo "========================================"

# 使用 script 记录终端输出（"截图"）
script -q -c "python3 \"$SCRIPT_DIR/test_all_examples.py\"" "$OUTPUT_DIR/terminal_session_$TIMESTAMP.log"

echo ""
echo "所有测试完成！"
echo "日志目录: $OUTPUT_DIR/"
echo ""
echo "文件清单:"
ls -lh "$OUTPUT_DIR/"
