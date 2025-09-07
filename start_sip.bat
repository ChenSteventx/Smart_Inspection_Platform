@echo off
chcp 65001 >nul
echo ========================================
echo Smart Inspection Platform 快速启动
echo ========================================
echo.

echo [1/3] 检查虚拟环境...
if not exist "sip_env" (
    echo 错误: 虚拟环境未创建，请先运行 setup_sip.bat
    pause
    exit /b 1
)

echo [2/3] 激活虚拟环境...
call sip_env\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo 错误: 激活虚拟环境失败
    pause
    exit /b 1
)

echo [3/3] 启动应用...
echo 正在启动 Smart Inspection Platform...
echo 访问地址: http://localhost:5001
echo 健康检查: http://localhost:5001/api/health
echo.
echo 虚拟环境: sip_env (已激活)
echo 按 Ctrl+C 停止服务
echo.

python app.py