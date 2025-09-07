#!/usr/bin/env python3
"""
BrowserGap优化配置文件
包含Node.js、npm路径配置和性能优化设置
放置在config目录下，符合项目架构规范
"""
import os
from pathlib import Path

# 基础路径配置
BASE_DIR = Path(__file__).parent.parent

# Node.js和npm固定路径配置
NODEJS_CONFIG = {
    "node_path": r"D:\nodejs\node.exe",
    "npm_path": r"D:\nodejs\npm.cmd", 
    "node_modules_path": r"D:\nodejs\node_modules",
    "node_global_path": r"D:\nodejs"
}

# 性能优化配置
PERFORMANCE_CONFIG = {
    "fast_mode": True,              # 启用快速模式
    "skip_prerequisites": True,     # 跳过前置条件检查
    "cache_timeout": 300,           # 缓存超时时间（秒）
    "startup_wait_time": 3,         # 启动等待时间（秒）
    "port_check_wait": 2,           # 端口检查等待时间（秒）
    "service_check_timeout": 10,    # 服务健康检查超时（秒）
    "enable_path_cache": True,      # 启用路径缓存
    "optimization_level": "high"    # 优化级别：low, medium, high
}

# Chrome浏览器路径配置
CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Users\{username}\AppData\Local\Google\Chrome\Application\chrome.exe"
]

# npm优化配置
NPM_CONFIG = {
    "registry": "https://registry.npmmirror.com",  # 使用国内镜像
    "cache_clean": False,          # 是否清理缓存
    "install_timeout": 300,        # 安装超时时间
    "skip_optional": True,         # 跳过可选依赖
    "production_mode": True,       # 生产模式安装
    "prefer_offline": True         # 优先使用离线缓存
}

# 环境变量配置
ENV_CONFIG = {
    "NODE_ENV": "production",
    "PYTHONIOENCODING": "utf-8",
    "PUPPETEER_SKIP_CHROMIUM_DOWNLOAD": "true",
    "PUPPETEER_CACHE_DIR": r"D:\nodejs\.puppeteer_cache",
    "CHROME_DEVEL_SANDBOX": "false",
    "NODE_OPTIONS": "--max-old-space-size=4096"
}

# BrowserGap服务配置
BROWSERGAP_SERVICE_CONFIG = {
    "default_port": 8081,
    "default_target_url": "https://fh.dji.com",
    "websocket_timeout": 30000,
    "http_timeout": 10000,
    "max_clients": 10,
    "performance_mode": "balanced",  # quality, balanced, performance
    "auto_restart": True,
    "health_check_interval": 30
}

# 启动优化配置
STARTUP_OPTIMIZATION = {
    "parallel_checks": True,        # 并行执行检查
    "skip_version_checks": True,    # 跳过版本检查
    "preload_chrome": False,        # 预加载Chrome（可选）
    "fast_fail": True,             # 快速失败机制
    "minimal_logging": False        # 最小日志输出
}

def get_optimized_config():
    """获取完整的优化配置"""
    return {
        "nodejs": NODEJS_CONFIG,
        "performance": PERFORMANCE_CONFIG,
        "chrome_paths": CHROME_PATHS,
        "npm": NPM_CONFIG,
        "env": ENV_CONFIG,
        "service": BROWSERGAP_SERVICE_CONFIG,
        "startup": STARTUP_OPTIMIZATION
    }

def get_node_path():
    """获取Node.js路径"""
    return NODEJS_CONFIG["node_path"]

def get_npm_path():
    """获取npm路径"""
    return NODEJS_CONFIG["npm_path"]

def is_fast_mode_enabled():
    """检查是否启用快速模式"""
    return PERFORMANCE_CONFIG["fast_mode"]

def get_chrome_path():
    """获取Chrome路径"""
    username = os.getenv("USERNAME", "")
    for chrome_path in CHROME_PATHS:
        if chrome_path.find("{username}") != -1:
            chrome_path = chrome_path.replace("{username}", username)
        if os.path.exists(chrome_path):
            return chrome_path
    return None

def validate_paths():
    """验证配置路径是否存在"""
    issues = []
    
    # 检查Node.js路径
    if not os.path.exists(NODEJS_CONFIG["node_path"]):
        issues.append(f"Node.js路径不存在: {NODEJS_CONFIG['node_path']}")
    
    # 检查npm路径
    if not os.path.exists(NODEJS_CONFIG["npm_path"]):
        issues.append(f"npm路径不存在: {NODEJS_CONFIG['npm_path']}")
    
    # 检查Chrome路径
    chrome_path = get_chrome_path()
    if not chrome_path:
        issues.append("Chrome浏览器路径均不存在")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "chrome_path": chrome_path
    }

def get_env_variables():
    """获取环境变量配置"""
    env = ENV_CONFIG.copy()
    
    # 动态设置Chrome路径
    chrome_path = get_chrome_path()
    if chrome_path:
        env["CHROME_PATH"] = chrome_path
        env["PUPPETEER_EXECUTABLE_PATH"] = chrome_path
    
    return env

def get_startup_command(port=None, target_url=None):
    """获取启动命令"""
    port = port or BROWSERGAP_SERVICE_CONFIG["default_port"]
    target_url = target_url or BROWSERGAP_SERVICE_CONFIG["default_target_url"]
    
    node_path = get_node_path()
    script_path = BASE_DIR / "external" / "browser_server_2.js"
    
    return [
        str(node_path),
        str(script_path),
        str(port),
        target_url
    ]

# 配置验证和自检
if __name__ == "__main__":
    print("BrowserGap配置验证")
    print("=" * 40)
    
    validation = validate_paths()
    
    if validation["valid"]:
        print("所有路径配置正确")
        config = get_optimized_config()
        print("\n当前配置:")
        for section, settings in config.items():
            print(f"\n{section.upper()}:")
            if isinstance(settings, dict):
                for key, value in settings.items():
                    print(f"  {key}: {value}")
            else:
                print(f"  {settings}")
                
        print(f"\nChrome路径: {validation['chrome_path']}")
        print(f"Node.js路径: {get_node_path()}")
        print(f"npm路径: {get_npm_path()}")
        print(f"快速模式: {'启用' if is_fast_mode_enabled() else '禁用'}")
    else:
        print("配置验证失败:")
        for issue in validation["issues"]:
            print(f"  - {issue}")