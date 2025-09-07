"""
配置模块初始化文件
导出主要配置类和BrowserGap配置
"""
from .settings import Config, config
from .browsergap_config import (
    get_optimized_config,
    get_node_path,
    get_npm_path,
    is_fast_mode_enabled,
    validate_paths,
    get_env_variables
)

__all__ = [
    'Config',
    'config',
    'get_optimized_config', 
    'get_node_path',
    'get_npm_path',
    'is_fast_mode_enabled',
    'validate_paths',
    'get_env_variables'
]