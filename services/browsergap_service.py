#!/usr/bin/env python3
"""
BrowserGap浏览器远程控制服务模块
负责浏览器隔离服务的管理和控制
"""
import os
import time
import logging
from config.settings import Config

# 从external目录导入browser_manager_2
import sys
sys.path.append(str(Config.BASE_DIR / "external"))

try:
    from browser_manager_2 import BrowserGapManager
    from config.browsergap_config import get_optimized_config
    MANAGER_AVAILABLE = True
except ImportError as e:
    logging.warning(f"无法导入BrowserGapManager: {e}，将使用模拟模式")
    MANAGER_AVAILABLE = False

logger = logging.getLogger(__name__)

class BrowserGapService:
    """BrowserGap服务管理器 - 使用真实的BrowserGapManager"""
    
    def __init__(self):
        if MANAGER_AVAILABLE:
            # 使用真实的manager
            self.manager = BrowserGapManager()
            
            # 应用优化配置
            try:
                config = get_optimized_config()
                self.manager.configure_paths(
                    node_path=config['nodejs']['node_path'],
                    npm_path=config['nodejs']['npm_path'],
                    fast_mode=config['performance']['fast_mode']
                )
                logger.info("已应用BrowserGap优化配置")
            except Exception as e:
                logger.warning(f"应用优化配置失败: {e}，使用默认配置")
            
            logger.info("使用真实的BrowserGapManager")
        else:
            # 回退到模拟模式
            self.manager = None
            logger.warning("使用模拟模式的BrowserGap服务")
            
        self.port = Config.BROWSERGAP_PORT
        self.target_url = Config.DJI_TARGET_URL
        
    def check_prerequisites(self):
        """检查系统前置条件"""
        try:
            if MANAGER_AVAILABLE and self.manager:
                return self.manager.check_prerequisites()
            else:
                return {
                    "success": False,
                    "issues": ["BrowserGapManager不可用"],
                    "details": {
                        "node_path": "模拟模式",
                        "npm_path": "模拟模式",
                        "fast_mode": False
                    }
                }
        except Exception as e:
            logger.error(f"检查前置条件时发生错误: {str(e)}")
            return {
                "success": False,
                "issues": [f"检查过程出错: {str(e)}"],
                "details": {}
            }
        
    def start_service(self, port=None, target_url=None):
        """启动BrowserGap服务"""
        try:
            port = port or self.port
            target_url = target_url or self.target_url
            
            logger.info(f"启动BrowserGap服务请求，端口: {port}, 目标URL: {target_url}")
            
            if MANAGER_AVAILABLE and self.manager:
                # 使用真实的manager启动服务
                success = self.manager.start_browsergap(port, target_url)
                
                if success:
                    status = self.manager.get_service_status()
                    return {
                        "success": True,
                        "message": "BrowserGap服务启动成功",
                        "service_url": self.manager.base_url,
                        "websocket_url": self.manager.websocket_url,
                        "port": port,
                        "target_url": target_url,
                        "performance_mode": status.get("performance_mode", "balanced"),
                        "clients": status.get("clients", 0)
                    }
                else:
                    return {
                        "success": False,
                        "error": "BrowserGap服务启动失败，请检查Node.js环境和Chrome浏览器"
                    }
            else:
                # 模拟模式
                logger.warning("使用模拟模式启动BrowserGap服务")
                return {
                    "success": True,
                    "message": "BrowserGap服务启动成功（模拟）",
                    "service_url": f"http://localhost:{port}",
                    "websocket_url": f"ws://localhost:{port}/ws",
                    "port": port,
                    "target_url": target_url,
                    "performance_mode": "balanced",
                    "clients": 0
                }
                
        except Exception as e:
            logger.error(f"启动BrowserGap服务时发生错误: {str(e)}")
            return {
                "success": False,
                "error": f"服务启动失败: {str(e)}"
            }
    
    def stop_service(self):
        """停止BrowserGap服务"""
        try:
            logger.info("停止BrowserGap服务请求")
            
            if MANAGER_AVAILABLE and self.manager:
                # 使用真实的manager停止服务
                success = self.manager.stop_browsergap()
                
                if success:
                    return {
                        "success": True,
                        "message": "BrowserGap服务已停止"
                    }
                else:
                    return {
                        "success": False,
                        "error": "停止服务失败"
                    }
            else:
                # 模拟模式
                logger.warning("使用模拟模式停止BrowserGap服务")
                return {
                    "success": True,
                    "message": "BrowserGap服务已停止（模拟）"
                }
                
        except Exception as e:
            logger.error(f"停止BrowserGap服务时发生错误: {str(e)}")
            return {
                "success": False,
                "error": f"停止服务失败: {str(e)}"
            }

# 全局服务实例
browsergap_service = BrowserGapService()