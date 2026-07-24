@echo off
chcp 65001 >nul
echo ========================================
echo   Hy3 研究助手 一键启动
echo ========================================
echo.

cd /d "%~dp0"

REM 优先从 .env 文件加载 HY3_API_KEY
if exist ".env" (
    for /f "tokens=1,2 delims==" %%a in (.env) do (
        if "%%a"=="HY3_API_KEY" set HY3_API_KEY=%%b
    )
)

REM 检查 API Key
if "%HY3_API_KEY%"=="" (
    echo [错误] 未检测到 HY3_API_KEY
    echo.
    echo 请按以下方式配置：
    echo   1. 复制 .env.example 为 .env，填写你的 API Key
    echo   2. 或执行: set HY3_API_KEY=你的API密钥
    echo.
    pause
    exit /b 1
)

echo [信息] API Key 已配置
echo [信息] 正在检查依赖...
cd /d "%~dp0backend"

REM 检查并安装依赖
pip install -r requirements.txt -q 2>nul
if errorlevel 1 (
    echo [警告] 依赖安装可能存在问题，尝试继续...
)

echo.
echo [信息] 启动 Hy3 研究助手服务...
echo ========================================
echo   前端页面: http://localhost:8000
echo   API 文档: http://localhost:8000/docs
echo   按 Ctrl+C 停止服务
echo ========================================
echo.
python main.py
pause
