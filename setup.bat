@echo off
chcp 65001 >nul
echo ==============================================
echo   Hy3 MCP Server - 一键安装脚本
echo ==============================================
echo.

REM 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.9+
    pause
    exit /b 1
)

echo [信息] Python 已检测到
echo.

REM 检查 API Key
if "%HY3_API_KEY%"=="" (
    echo [警告] 未设置 HY3_API_KEY 环境变量
    echo.
    echo 请先设置 API Key：
    echo   set HY3_API_KEY=你的API密钥
    echo.
    echo 或创建 .env 文件并添加：
    echo   HY3_API_KEY=你的API密钥
    echo.
)

REM 安装依赖
echo [信息] 正在安装依赖...
cd /d "%~dp0"
pip install -r requirements.txt -q
echo.

REM 验证安装
echo [信息] 正在验证安装...
python -c "from fastmcp import FastMCP; print('  [OK] FastMCP')" 2>nul
python -c "from openai import OpenAI; print('  [OK] OpenAI SDK')" 2>nul
python -c "import httpx; print('  [OK] httpx')" 2>nul
echo.

echo [信息] 安装完成！
echo.
echo 启动方式（在 CodeBuddy 中配置 MCP）：
echo   将 configs/codebuddy-mcp.json 中的配置添加到 CodeBuddy 的 MCP 设置中。
echo.
echo 或手动测试：
echo   cd src
echo   set HY3_API_KEY=你的API密钥
echo   python server.py
echo.
pause
