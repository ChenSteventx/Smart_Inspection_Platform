# Smart Inspection Platform PowerShell 配置脚本
# 虚拟环境: sip_env (Smart Inspection Platform Environment)

param(
    [switch]$Help
)

if ($Help) {
    Write-Host "Smart Inspection Platform 环境配置脚本" -ForegroundColor Cyan
    Write-Host "用法: .\setup_sip.ps1 [选项]" -ForegroundColor Green
    Write-Host "选项:" -ForegroundColor Yellow
    Write-Host "  -Help    显示此帮助信息" -ForegroundColor White
    Write-Host ""
    Write-Host "功能:" -ForegroundColor Yellow
    Write-Host "  - 创建 sip_env 虚拟环境" -ForegroundColor White
    Write-Host "  - 安装 Python 和 Node.js 依赖" -ForegroundColor White
    Write-Host "  - 支持镜像源加速下载" -ForegroundColor White
    exit 0
}

Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "Smart Inspection Platform 环境配置"  -ForegroundColor Cyan
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host ""

# 检查Python环境
Write-Host "[1/7] 检查Python环境..." -ForegroundColor Green
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Python版本: $pythonVersion" -ForegroundColor Yellow
    } else {
        Write-Host "错误: 未找到Python，请安装Python 3.12+" -ForegroundColor Red
        Read-Host "按Enter退出"
        exit 1
    }
} catch {
    Write-Host "错误: 未找到Python，请安装Python 3.12+" -ForegroundColor Red
    Read-Host "按Enter退出"
    exit 1
}

Write-Host ""

# 检查Node.js环境
Write-Host "[2/7] 检查Node.js环境..." -ForegroundColor Green
try {
    $nodeVersion = node --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Node.js版本: $nodeVersion" -ForegroundColor Yellow
    } else {
        Write-Host "警告: 未找到Node.js，浏览器功能将不可用" -ForegroundColor Yellow
    }
} catch {
    Write-Host "警告: 未找到Node.js，浏览器功能将不可用" -ForegroundColor Yellow
}

Write-Host ""

# 创建虚拟环境
Write-Host "[3/7] 创建Python虚拟环境..." -ForegroundColor Green
if (Test-Path "sip_env") {
    Write-Host "虚拟环境 sip_env 已存在" -ForegroundColor Yellow
} else {
    Write-Host "正在创建虚拟环境 sip_env..." -ForegroundColor Cyan
    python -m venv sip_env
    if ($LASTEXITCODE -eq 0) {
        Write-Host "虚拟环境创建成功" -ForegroundColor Green
    } else {
        Write-Host "错误: 创建虚拟环境失败" -ForegroundColor Red
        Read-Host "按Enter退出"
        exit 1
    }
}

Write-Host ""

# 激活虚拟环境
Write-Host "[4/7] 激活虚拟环境..." -ForegroundColor Green
if (Test-Path "sip_env\Scripts\Activate.ps1") {
    & "sip_env\Scripts\Activate.ps1"
    Write-Host "虚拟环境已激活" -ForegroundColor Green
} else {
    Write-Host "错误: 虚拟环境激活脚本不存在" -ForegroundColor Red
    Read-Host "按Enter退出"
    exit 1
}

Write-Host ""

# 安装Python依赖
Write-Host "[5/7] 安装Python依赖..." -ForegroundColor Green
if (Test-Path "requirements.txt") {
    Write-Host ""
    Write-Host "是否使用清华源加速下载？ (推荐中国大陆用户使用)" -ForegroundColor Yellow
    Write-Host "[Y] 是 - 使用清华源 (默认)" -ForegroundColor Cyan
    Write-Host "[N] 否 - 使用官方源" -ForegroundColor Cyan
    $useTsinghua = Read-Host "请选择 (Y/N, 默认Y)"
    
    if ([string]::IsNullOrEmpty($useTsinghua) -or $useTsinghua.ToUpper() -eq "Y") {
        Write-Host "使用清华源安装依赖..." -ForegroundColor Cyan
        Write-Host "升级pip..." -ForegroundColor Yellow
        pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
        Write-Host "安装项目依赖..." -ForegroundColor Yellow
        pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    } else {
        Write-Host "使用官方源安装依赖..." -ForegroundColor Cyan
        Write-Host "升级pip..." -ForegroundColor Yellow
        pip install --upgrade pip
        Write-Host "安装项目依赖..." -ForegroundColor Yellow
        pip install -r requirements.txt
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Python依赖安装完成" -ForegroundColor Green
    } else {
        Write-Host "错误: Python依赖安装失败" -ForegroundColor Red
        Read-Host "按Enter退出"
        exit 1
    }
} else {
    Write-Host "错误: 未找到requirements.txt文件" -ForegroundColor Red
    Read-Host "按Enter退出"
    exit 1
}

Write-Host ""

# 安装Node.js依赖
Write-Host "[6/7] 安装Node.js依赖..." -ForegroundColor Green
if (Test-Path "package.json") {
    Write-Host ""
    Write-Host "是否使用淘宝镜像加速Node.js包下载？ (推荐中国大陆用户使用)" -ForegroundColor Yellow
    Write-Host "[Y] 是 - 使用淘宝镜像 (默认)" -ForegroundColor Cyan
    Write-Host "[N] 否 - 使用官方源" -ForegroundColor Cyan
    $useTaobao = Read-Host "请选择 (Y/N, 默认Y)"
    
    if ([string]::IsNullOrEmpty($useTaobao) -or $useTaobao.ToUpper() -eq "Y") {
        Write-Host "使用淘宝镜像安装Node.js依赖..." -ForegroundColor Cyan
        npm install --registry=https://registry.npmmirror.com
    } else {
        Write-Host "使用官方源安装Node.js依赖..." -ForegroundColor Cyan
        npm install
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Node.js依赖安装完成" -ForegroundColor Green
    } else {
        Write-Host "错误: Node.js依赖安装失败" -ForegroundColor Red
        Read-Host "按Enter退出"
        exit 1
    }
} else {
    Write-Host "未找到package.json，跳过Node.js依赖安装" -ForegroundColor Yellow
}

Write-Host ""

# 配置完成
Write-Host "[7/7] 环境配置完成！" -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "环境配置成功完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "虚拟环境名称: " -NoNewline -ForegroundColor White
Write-Host "sip_env" -ForegroundColor Yellow
Write-Host "环境说明: " -NoNewline -ForegroundColor White
Write-Host "Smart Inspection Platform Environment" -ForegroundColor Yellow
Write-Host ""
Write-Host "启动项目:" -ForegroundColor Cyan
Write-Host "  1. 激活虚拟环境: " -NoNewline -ForegroundColor White
Write-Host "sip_env\Scripts\Activate.ps1" -ForegroundColor Yellow
Write-Host "  2. 运行应用: " -NoNewline -ForegroundColor White
Write-Host "python app.py" -ForegroundColor Yellow
Write-Host "  3. 访问地址: " -NoNewline -ForegroundColor White
Write-Host "http://localhost:5001" -ForegroundColor Yellow
Write-Host ""
Write-Host "快速启动: " -NoNewline -ForegroundColor White
Write-Host "运行 start_sip.bat" -ForegroundColor Yellow
Write-Host ""

Read-Host "按Enter退出"