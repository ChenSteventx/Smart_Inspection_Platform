@echo off
chcp 65001 >nul
echo ========================================
echo Smart Inspection Platform 环境配置
echo ========================================
echo.

echo [1/7] 检查Python环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Python，请安装Python 3.12+
    pause
    exit /b 1
)
python --version
echo.

echo [2/7] 检查Node.js环境...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 警告: 未找到Node.js，浏览器功能将不可用
) else (
    node --version
)
echo.

echo [3/7] 创建Python虚拟环境...
if exist "sip_env" (
    echo 虚拟环境已存在
) else (
    echo 正在创建虚拟环境...
    python -m venv sip_env
    if %errorlevel% neq 0 (
        echo 错误: 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo 虚拟环境创建成功
)
echo.

echo [4/7] 激活虚拟环境...
if not exist "sip_env\Scripts\activate.bat" (
    echo 错误: 虚拟环境激活脚本不存在
    pause
    exit /b 1
)
call sip_env\Scripts\activate.bat
echo 虚拟环境已激活
echo.

echo [5/7] 安装Python依赖...
if not exist "requirements.txt" (
    echo 错误: 未找到requirements.txt文件
    pause
    exit /b 1
)
echo.
echo 是否使用清华源加速下载？ (推荐中国大陆用户使用)
echo [Y] 是 - 使用清华源 (默认)
echo [N] 否 - 使用官方源
set /p use_tsinghua="请选择 (Y/N, 默认Y): "
if "%use_tsinghua%"=="" set use_tsinghua=Y
if /i "%use_tsinghua%"=="Y" (
    echo 使用清华源安装依赖...
    echo 升级pip...
    pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
    echo 安装项目依赖...
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
) else (
    echo 使用官方源安装依赖...
    echo 升级pip...
    pip install --upgrade pip
    echo 安装项目依赖...
    pip install -r requirements.txt
)
if %errorlevel% neq 0 (
    echo 错误: Python依赖安装失败
    pause
    exit /b 1
)
echo Python依赖安装完成
echo.

echo [6/7] 安装Node.js依赖...
if exist "package.json" (
    echo.
    echo 是否使用淘宝镜像加速Node.js包下载？ (推荐中国大陆用户使用)
    echo [Y] 是 - 使用淘宝镜像 (默认)
    echo [N] 否 - 使用官方源
    set /p use_taobao="请选择 (Y/N, 默认Y): "
    if "!use_taobao!"=="" set use_taobao=Y
    if /i "!use_taobao!"=="Y" (
        echo 使用淘宝镜像安装Node.js依赖...
        npm install --registry=https://registry.npmmirror.com
    ) else (
        echo 使用官方源安装Node.js依赖...
        npm install
    )
    if %errorlevel% neq 0 (
        echo 错误: Node.js依赖安装失败
        pause
        exit /b 1
    )
    echo Node.js依赖安装完成
) else (
    echo 未找到package.json，跳过Node.js依赖安装
)
echo.

echo [7/7] 环境配置完成！
echo.
echo ========================================
echo 环境配置成功完成！
echo ========================================
echo.
echo 虚拟环境名称: sip_env (Smart Inspection Platform Environment)
echo.
echo 启动项目:
echo   1. 激活虚拟环境: sip_env\Scripts\activate.bat
echo   2. 运行应用: python app.py  
echo   3. 访问地址: http://localhost:5001
echo.
echo 快速启动: 运行 start_sip.bat
echo.
pause