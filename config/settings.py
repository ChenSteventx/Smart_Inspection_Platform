#!/usr/bin/env python3
"""
Smart Inspection Platform 配置管理
"""
import os
import time
from pathlib import Path

class Config:
    """应用配置类"""
    
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'smart-inspection-platform-secret-key'
    DEBUG = True
    
    # 服务端口配置
    FLASK_PORT = 5001
    BROWSERGAP_PORT = 8081
    
    # 项目根目录
    BASE_DIR = Path(__file__).parent.parent
    
    # 文件存储配置
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    THERMAL_DATA_FOLDER = UPLOAD_FOLDER / "thermal_data"
    METADATA_FOLDER = UPLOAD_FOLDER / "metadata"
    EXCEL_CACHE_FOLDER = UPLOAD_FOLDER / "excel_cache"
    PDF_FOLDER = BASE_DIR / "data"
    
    # 外部工具路径配置 - 更新为实际的DJI IRP路径
    DJI_IRP_PATH = BASE_DIR / "external" / "temperReader" / "dji_thermal_sdk_v1.5_20240507" / "sample" / "bin" / "windows" / "release_x64" / "dji_irp.exe"
    
    # Abaqus配置（用于命令执行功能）
    ABAQUS_SCRIPT_DIR = r"D:\abap-server\ABAP-Next-Innovation-Installation-Package"
    ABAQUS_TMP_PATH = r"D:\abap-server\tmp.txt"
    ABAQUS_OUTPUT_DIR = r"D:\abap-server\abap-yst"
    ABAQUS_OUTPUT_IMAGE = r"D:\abap-server\abap-yst\assembly_viewport.png"
    
    # 数据库配置（知识图谱功能）
    MYSQL_HOST = '127.0.1.1'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = '123456'
    MYSQL_PORT = 3306
    MYSQL_DATABASE = 'school'
    MYSQL_CHARSET = 'utf8'
    
    # BrowserGap目标URL
    DJI_TARGET_URL = "https://fh.dji.com"
    
    # BrowserGap优化配置
    BROWSERGAP_FAST_MODE = True
    BROWSERGAP_SKIP_PREREQUISITES = True
    BROWSERGAP_CACHE_TIMEOUT = 300
    BROWSERGAP_STARTUP_WAIT = 3
    
    # Node.js和npm路径（可被环境变量覆盖）
    NODEJS_PATH = os.environ.get('NODEJS_PATH') or r'D:\nodejs\node.exe'
    NPM_PATH = os.environ.get('NPM_PATH') or r'D:\nodejs\npm.cmd'
    
    # Flask应用配置
    SEND_FILE_MAX_AGE_DEFAULT = 300
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
    
    # 线程池配置
    THREAD_POOL_MAX_WORKERS = 4
    
    @classmethod
    def init_directories(cls):
        """初始化必要的目录"""
        directories = [
            cls.UPLOAD_FOLDER,
            cls.THERMAL_DATA_FOLDER,
            cls.METADATA_FOLDER,
            cls.EXCEL_CACHE_FOLDER,
            cls.PDF_FOLDER
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        print(f"已初始化存储目录: {len(directories)} 个")
    
    @staticmethod
    def get_current_timestamp():
        """获取当前时间戳"""
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

# 环境变量配置
class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'production-secret-key-please-change'

# 配置映射
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}