#!/bin/bash
echo "=============================================="
echo "  Hy3 MCP Server - 一键安装脚本"
echo "=============================================="
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到 Python，请先安装 Python 3.9+"
    exit 1
fi

echo "[信息] Python 已检测到"

# 检查 API Key
if [ -z "$HY3_API_KEY" ]; then
    echo "[警告] 未设置 HY3_API_KEY 环境变量"
    echo ""
    echo "请先设置 API Key："
    echo "  export HY3_API_KEY=你的API密钥"
    echo ""
fi

# 安装依赖
echo "[信息] 正在安装依赖..."
cd "$(dirname "$0")"
pip3 install -r requirements.txt -q
echo ""

# 验证
echo "[信息] 正在验证安装..."
python3 -c "from fastmcp import FastMCP; print('  [OK] FastMCP')"
python3 -c "from openai import OpenAI; print('  [OK] OpenAI SDK')"
python3 -c "import httpx; print('  [OK] httpx')"
echo ""

echo "[信息] 安装完成！"
echo ""
echo "启动方式（手动测试）："
echo "  cd src"
echo "  export HY3_API_KEY=你的API密钥"
echo "  python3 server.py"
echo ""
