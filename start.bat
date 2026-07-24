@echo off
chcp 65001 >nul
echo ========================================
echo   Hy3 研究助手 一键启动
echo ========================================
echo.

REM 检查 API Key
if "%HY3_API_KEY%"=="" (
    echo [警告] 未设置 HY3_API_KEY 环境变量
    echo 请先执行: set HY3_API_KEY=你的API密钥
    echo.
    pause
    exit /b 1
)

echo [信息] API Key 已配置
echo [信息] 正在安装依赖...
cd /d "%~dp0backend"
pip install -r requirements.txt -q
echo.

echo [信息] 启动服务...
echo 前端页面: http://localhost:8000
echo 按 Ctrl+C 停止服务
echo.
python main.py
pause
