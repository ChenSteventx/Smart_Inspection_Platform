import subprocess
import time
import requests
import json
import psutil
import os
import signal
import threading
from typing import Dict, Optional, Tuple
import platform
import shutil
import logging

# 配置日志记录系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BrowserGapManager:
    """
    优化版浏览器隔离服务管理器
    提供与Flask应用集成的标准化接口
    """
    
    def __init__(self):
        self.process = None
        self.port = 8081
        self.host = "localhost"
        self.base_url = f"http://{self.host}:{self.port}"
        self.websocket_url = f"ws://{self.host}:{self.port}"
        self.is_running = False
        self.startup_timeout = 60
        self.server_script_path = os.path.join(os.path.dirname(__file__), 'browser_server_2.js')
        
        # 配置固定的Node.js和npm路径以提高性能
        self.npm_path = r'D:\nodejs\npm.cmd'  # 固定npm路径
        self.node_path = r'D:\nodejs\node.exe'  # 固定Node.js路径
        self.performance_mode = 'balanced'
        
        # 缓存机制 - 优化性能
        self._path_cache = {
            'node': self.node_path,
            'npm': self.npm_path,
            'chrome': None
        }
        self._cache_timestamp = {
            'node': time.time(),
            'npm': time.time()
        }
        self._cache_timeout = 300  # 5分钟缓存超时
        
        # 性能优化配置
        self._skip_version_check = False  # 是否跳过版本检查以加快启动
        self._fast_mode = True  # 启用快速模式
        
    def check_prerequisites(self) -> Dict:
        """
        检查系统运行前置条件 - 快速模式优化
        返回包含检查结果和问题列表的字典
        """
        issues = []
        
        # 快速模式：优先检查固定路径
        if self._fast_mode:
            logger.info("启用快速检查模式")
            
            # 快速检查Node.js
            if os.path.exists(self.node_path):
                logger.info(f"Node.js环境已确认: {self.node_path}")
            else:
                # 备用检查
                if self._find_node():
                    logger.info(f"Node.js环境已确认: {self.node_path}")
                else:
                    issues.append("Node.js运行环境未找到，请确保Node.js已正确安装")
            
            # 快速检查npm
            if os.path.exists(self.npm_path):
                logger.info(f"npm包管理器已确认: {self.npm_path}")
            else:
                # 备用检查
                if self._find_npm():
                    logger.info(f"npm包管理器已确认: {self.npm_path}")
                else:
                    issues.append("npm包管理器未找到，请确保npm已正确安装")
            
            # 快速检查Chrome
            chrome_found = self._find_chrome()
            if not chrome_found:
                issues.append("Google Chrome浏览器未找到，请确保Chrome已正确安装")
            
            # 检查脚本文件
            if not os.path.exists(self.server_script_path):
                issues.append(f"服务器脚本文件不存在: {self.server_script_path}")
            
            # 在快速模式下跳过npm依赖检查以加快启动
            if not issues:
                logger.info("快速模式：跳过npm依赖检查以加快启动")
        else:
            # 正常模式：完整检查
            is_windows = platform.system() == 'Windows'
            
            # 执行Node.js环境检查
            node_found = self._find_node()
            if not node_found:
                issues.append("Node.js运行环境未找到，请确保Node.js已正确安装并配置环境变量")
            else:
                logger.info(f"Node.js环境已确认: {self.node_path}")
            
            # 执行npm包管理器检查
            npm_found = self._find_npm()
            if not npm_found:
                issues.append("npm包管理器未找到，请确保npm已正确安装")
            else:
                logger.info(f"npm包管理器已确认: {self.npm_path}")
            
            # 执行Chrome浏览器检查
            chrome_found = self._find_chrome()
            if not chrome_found:
                issues.append("Google Chrome浏览器未找到，请确保Chrome已正确安装")
            
            # 验证服务器脚本文件存在性
            if not os.path.exists(self.server_script_path):
                issues.append(f"服务器脚本文件不存在: {self.server_script_path}")
            
            # 在基础条件满足时检查npm依赖包（添加超时保护）
            if not issues:
                try:
                    # 使用单独线程检查npm依赖，避免阻塞
                    import threading
                    import time
                    
                    def check_npm_packages():
                        try:
                            self._ensure_npm_packages()
                        except Exception as e:
                            logger.warning(f"npm依赖包检查失败: {str(e)}")
                    
                    npm_thread = threading.Thread(target=check_npm_packages)
                    npm_thread.daemon = True
                    npm_thread.start()
                    npm_thread.join(timeout=30)  # 30秒超时
                    
                    if npm_thread.is_alive():
                        logger.warning("npm依赖包检查超时，但基础环境可用")
                        
                except Exception as e:
                    logger.warning(f"npm依赖包检查过程出错: {str(e)}")
        
        return {
            "success": len(issues) == 0,
            "issues": issues,
            "details": {
                "node_path": self.node_path,
                "npm_path": self.npm_path,
                "script_path": self.server_script_path,
                "fast_mode": self._fast_mode
            }
        }
    
    def _find_node(self) -> bool:
        """
        优化版Node.js检测 - 智能路径检测与缓存机制
        """
        # 检查缓存
        if self._is_cache_valid('node'):
            self.node_path = self._path_cache['node']
            if self.node_path and self._test_node_version(self.node_path):
                logger.info(f"Node.js缓存路径有效: {self.node_path}")
                return True
        
        # 常用路径快速检测
        common_node_paths = self._get_common_node_paths()
        for node_path in common_node_paths:
            if self._test_node_path(node_path):
                self._cache_path('node', node_path)
                return True
        
        # 全面路径扫描
        all_node_paths = self._get_all_node_paths()
        for node_path in all_node_paths:
            if node_path not in common_node_paths and self._test_node_path(node_path):
                self._cache_path('node', node_path)
                return True
        
        return False
    
    def _get_common_node_paths(self) -> list:
        """获取常用Node.js路径"""
        common_paths = ['node']  # 环境变量中的node
        
        if platform.system() == 'Windows':
            common_paths.extend([
                r'D:\nodejs\node.exe',
                r'C:\Program Files\nodejs\node.exe',
                r'C:\Program Files (x86)\nodejs\node.exe',
            ])
        
        return common_paths
    
    def _get_all_node_paths(self) -> list:
        """获取所有可能的Node.js路径"""
        all_paths = []
        
        if platform.system() == 'Windows':
            all_paths.extend([
                os.path.expanduser(r'~\AppData\Roaming\nvm\nodejs\node.exe'),
                os.path.join(os.environ.get('PROGRAMFILES', ''), 'nodejs', 'node.exe'),
                os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'nodejs', 'node.exe'),
            ])
        
        return all_paths
    
    def _test_node_path(self, node_path: str) -> bool:
        """测试Node.js路径是否有效"""
        if not node_path:
            return False
            
        # 先检查文件是否存在
        if not os.path.exists(node_path) and not shutil.which(node_path):
            return False
            
        return self._test_node_version(node_path)
    
    def _test_node_version(self, node_path: str) -> bool:
        """测试Node.js版本"""
        try:
            if os.path.exists(node_path):
                result = subprocess.run(
                    [node_path, '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    encoding='utf-8',
                    errors='replace'
                )
            else:
                result = subprocess.run(
                    [node_path, '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    shell=True,
                    encoding='utf-8',
                    errors='replace'
                )
                
            if result.returncode == 0:
                self.node_path = node_path
                logger.info(f"Node.js版本检测: {result.stdout.strip()}")
                return True
        except Exception as e:
            logger.debug(f"Node.js路径检测失败 {node_path}: {str(e)}")
        return False
    
    def _find_npm(self) -> bool:
        """
        超快速npm包管理器检测 - 针对已知环境的优化策略
        """
        # 检查缓存
        if self._is_cache_valid('npm'):
            self.npm_path = self._path_cache['npm']
            if self.npm_path and self._test_npm_version(self.npm_path):
                logger.info(f"npm缓存路径有效: {self.npm_path}")
                return True
        
        # 针对已知的D:\nodejs安装的快速检测
        known_npm_path = r'D:\nodejs\npm.cmd'
        if os.path.exists(known_npm_path):
            if self._test_npm_version(known_npm_path):
                self._cache_path('npm', known_npm_path)
                logger.info(f"快速找到已知npm路径: {known_npm_path}")
                return True
        
        # 基于Node.js路径的智能检测（第二快）
        if self.node_path:
            npm_from_node = self._find_npm_near_node()
            if npm_from_node:
                self._cache_path('npm', npm_from_node)
                return True
        
        # 常用路径快速检测（减少路径数量，提高速度）
        quick_npm_paths = [
            'npm.cmd',  # 系统PATH中的npm
            'npm',
            r'C:\Program Files\nodejs\npm.cmd',  # 标准安装路径
        ]
        
        for npm_cmd in quick_npm_paths:
            if self._test_npm_path(npm_cmd):
                self._cache_path('npm', npm_cmd)
                return True
        
        # 如果还是找不到，尝试where命令（但限制超时）
        if platform.system() == 'Windows':
            npm_from_where = self._find_npm_via_where()
            if npm_from_where:
                self._cache_path('npm', npm_from_where)
                return True
        
        logger.warning("npm包管理器未找到，请确保npm已正确安装")
        return False
    
    def _find_npm_via_where(self) -> str:
        """使用where命令快速定位npm（Windows优先策略）"""
        try:
            where_result = subprocess.run(
                'where npm',
                capture_output=True,
                text=True,
                shell=True,
                encoding='utf-8',
                errors='replace',
                timeout=2  # 进一步减少超时时间
            )
            
            if where_result.returncode == 0 and where_result.stdout:
                npm_location = where_result.stdout.strip().split('\n')[0]
                if os.path.exists(npm_location) and self._test_npm_version(npm_location):
                    logger.info(f"npm版本检测（通过where定位）: 快速找到")
                    return npm_location
        except subprocess.TimeoutExpired:
            logger.debug("where命令超时，跳过")
        except Exception as e:
            logger.debug(f"where命令查找npm失败: {str(e)}")
        return None
    
    def _find_npm_near_node(self) -> str:
        """基于Node.js路径智能查找npm"""
        if not self.node_path:
            # 如果没有node_path，尝试从当前可用的node命令获取路径
            try:
                result = subprocess.run(
                    ['where', 'node'] if platform.system() == 'Windows' else ['which', 'node'],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    encoding='utf-8',
                    errors='replace'
                )
                if result.returncode == 0 and result.stdout:
                    potential_node_path = result.stdout.strip().split('\n')[0]
                    if os.path.exists(potential_node_path):
                        node_dir = os.path.dirname(potential_node_path)
                        logger.debug(f"从where/which命令获取Node.js目录: {node_dir}")
                    else:
                        node_dir = None
                else:
                    node_dir = None
            except:
                node_dir = None
        elif self.node_path == 'node':
            # 当node_path是'node'命令时，尝试找到实际路径
            try:
                result = subprocess.run(
                    ['where', 'node'] if platform.system() == 'Windows' else ['which', 'node'],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    encoding='utf-8',
                    errors='replace'
                )
                if result.returncode == 0 and result.stdout:
                    actual_node_path = result.stdout.strip().split('\n')[0]
                    if os.path.exists(actual_node_path):
                        node_dir = os.path.dirname(actual_node_path)
                        logger.debug(f"从'node'命令解析到实际路径: {actual_node_path}, 目录: {node_dir}")
                    else:
                        node_dir = None
                else:
                    node_dir = None
            except:
                node_dir = None
        else:
            node_dir = os.path.dirname(self.node_path)
            
        if not node_dir:
            return None
            
        potential_npm_paths = [
            os.path.join(node_dir, 'npm.cmd'),
            os.path.join(node_dir, 'npm'),
            os.path.join(node_dir, 'npm.bat'),
        ]
        
        for npm_path in potential_npm_paths:
            if os.path.exists(npm_path) and self._test_npm_version(npm_path):
                logger.info(f"npm在Node.js目录中找到: {npm_path}")
                return npm_path
        return None
    
    def _get_common_npm_paths(self) -> list:
        """获取常用npm路径（按使用频率排序）"""
        if platform.system() == 'Windows':
            return [
                'npm.cmd',  # 最常用
                'npm',
                r'D:\nodejs\npm.cmd',  # 用户自定义安装
                r'C:\Program Files\nodejs\npm.cmd',  # 标准安装
                os.path.expanduser(r'~\AppData\Roaming\npm\npm.cmd'),  # 用户安装
            ]
        else:
            return ['npm', '/usr/local/bin/npm', '/usr/bin/npm']
    
    def _get_all_npm_paths(self) -> list:
        """获取所有可能的npm路径"""
        if platform.system() == 'Windows':
            return [
                r'D:\nodejs\npm.bat',
                r'C:\Program Files (x86)\nodejs\npm.cmd',
                r'C:\Program Files (x86)\nodejs\npm',
                os.path.expanduser(r'~\AppData\Roaming\npm\npm'),
            ]
        else:
            return []  # Linux/Mac路径已在common中包含
    
    def _test_npm_path(self, npm_cmd: str) -> bool:
        """测试npm路径是否有效（优化版）"""
        if not npm_cmd:
            return False
            
        # 先检查文件是否存在（快速筛选）
        if not os.path.exists(npm_cmd) and not shutil.which(npm_cmd):
            return False
            
        return self._test_npm_version(npm_cmd)
    
    def _test_npm_version(self, npm_cmd: str) -> bool:
        """测试npm版本（快速版本检测）"""
        try:
            if platform.system() == 'Windows':
                # 使用更直接的方式调用，并设置shell=True以确保兼容性
                result = subprocess.run(
                    [npm_cmd, '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5,  # 缩短超时时间以提高检测效率
                    encoding='utf-8',
                    errors='replace',
                    shell=True  # 设置shell=True以确保兼容性
                )
            else:
                result = subprocess.run(
                    [npm_cmd, '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    encoding='utf-8',
                    errors='replace',
                    shell=False
                )
                
            if result.returncode == 0 and result.stdout.strip():
                self.npm_path = npm_cmd
                version = result.stdout.strip()
                logger.info(f"npm版本检测: {version}")
                return True
            else:
                logger.debug(f"npm命令返回错误码: {result.returncode}, stderr: {result.stderr.strip()}")
                
        except subprocess.TimeoutExpired:
            logger.debug(f"npm版本检测超时 {npm_cmd} (5秒)")
        except Exception as e:
            logger.debug(f"npm版本测试失败 {npm_cmd}: {str(e)}")
        return False
    
    def configure_paths(self, node_path: str = None, npm_path: str = None, fast_mode: bool = True):
        """
        配置Node.js和npm路径，启用快速模式
        """
        if node_path:
            self.node_path = node_path
            self._path_cache['node'] = node_path
            self._cache_timestamp['node'] = time.time()
            logger.info(f"已配置Node.js路径: {node_path}")
        
        if npm_path:
            self.npm_path = npm_path
            self._path_cache['npm'] = npm_path
            self._cache_timestamp['npm'] = time.time()
            logger.info(f"已配置npm路径: {npm_path}")
        
        self._fast_mode = fast_mode
        logger.info(f"快速模式: {'\u5df2\u542f\u7528' if fast_mode else '\u5df2\u7981\u7528'}")
    
    def get_optimization_status(self) -> Dict:
        """
        获取优化配置状态
        """
        return {
            "fast_mode": self._fast_mode,
            "node_path": self.node_path,
            "npm_path": self.npm_path,
            "node_exists": os.path.exists(self.node_path) if self.node_path else False,
            "npm_exists": os.path.exists(self.npm_path) if self.npm_path else False,
            "cache_status": {
                "node_cached": 'node' in self._path_cache and self._path_cache['node'] is not None,
                "npm_cached": 'npm' in self._path_cache and self._path_cache['npm'] is not None,
                "chrome_cached": 'chrome' in self._path_cache and self._path_cache['chrome'] is not None
            }
        }

    def _is_cache_valid(self, tool: str) -> bool:
        """检查缓存是否有效"""
        if tool not in self._path_cache or not self._path_cache[tool]:
            return False
            
        if tool not in self._cache_timestamp:
            return False
            
        return time.time() - self._cache_timestamp[tool] < self._cache_timeout
    
    def _cache_path(self, tool: str, path: str):
        """缓存工具路径"""
        self._path_cache[tool] = path
        self._cache_timestamp[tool] = time.time()
        logger.debug(f"缓存{tool}路径: {path}")
    
    def _find_chrome(self) -> bool:
        """
        优化版Chrome浏览器检测 - 使用缓存机制
        """
        # 检查缓存
        if self._is_cache_valid('chrome'):
            chrome_path = self._path_cache['chrome']
            if chrome_path and os.path.exists(chrome_path):
                logger.info(f"Chrome缓存路径有效: {chrome_path}")
                return True
        
        chrome_paths = [
            r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
            os.path.expanduser(r'~\AppData\Local\Google\Chrome\Application\chrome.exe'),
        ]
        
        for path in chrome_paths:
            if os.path.exists(path):
                logger.info(f"Chrome浏览器已确认: {path}")
                self._cache_path('chrome', path)
                return True
        
        return False
    
    def _ensure_npm_packages(self):
        """
        确保项目所需的npm依赖包已正确安装
        """
        work_dir = os.path.dirname(self.server_script_path)
        package_json_path = os.path.join(work_dir, 'package.json')
        node_modules_path = os.path.join(work_dir, 'node_modules')
        
        if not os.path.exists(package_json_path):
            logger.info("正在创建package.json配置文件")
            self._create_package_json()
        
        required_packages = ['express', 'puppeteer-core', 'ws', 'cors', 'body-parser']
        missing_packages = []
        
        if not os.path.exists(node_modules_path):
            missing_packages = required_packages
        else:
            for package in required_packages:
                package_path = os.path.join(node_modules_path, package)
                if not os.path.exists(package_path):
                    missing_packages.append(package)
        
        puppeteer_path = os.path.join(node_modules_path, 'puppeteer')
        puppeteer_core_path = os.path.join(node_modules_path, 'puppeteer-core')

        if os.path.exists(puppeteer_path) and not os.path.exists(puppeteer_core_path):
            logger.info("检测到puppeteer包，需要切换到puppeteer-core")
            self._uninstall_puppeteer()
            missing_packages.append('puppeteer-core')

        if missing_packages:
            logger.info(f"需要安装npm依赖包: {', '.join(missing_packages)}")
            self._install_npm_packages()
    
    def _create_package_json(self):
        """
        创建npm项目配置文件
        """
        package_json = {
            "name": "browsergap-service-optimized",
            "version": "2.0.0",
            "description": "Optimized remote browser isolation service",
            "main": "browser_server_2.js",
            "scripts": {
                "start": "node browser_server_2.js"
            },
            "dependencies": {
                "express": "^4.18.2",
                "puppeteer-core": "^21.0.0",
                "ws": "^8.13.0",
                "cors": "^2.8.5",
                "body-parser": "^1.20.2"
            },
            "engines": {
                "node": ">=14.0.0"
            }
        }
        
        work_dir = os.path.dirname(self.server_script_path)
        package_json_path = os.path.join(work_dir, 'package.json')
        
        with open(package_json_path, 'w', encoding='utf-8') as f:
            json.dump(package_json, f, indent=2)
        
        logger.info("package.json配置文件创建完成")

    def _install_npm_packages(self, packages=None):
        """
        执行npm依赖包安装过程
        """
        try:
            work_dir = os.path.dirname(self.server_script_path)
            npm_cmd = self.npm_path or 'npm'
            
            logger.info("正在安装npm依赖包，此过程可能需要几分钟时间")
            
            cache_clean_cmd = f'{npm_cmd} cache clean --force'
            subprocess.run(
                cache_clean_cmd,
                shell=True,
                cwd=work_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30
            )
            
            if packages:
                packages_str = ' '.join(packages)
                install_cmd = f'{npm_cmd} install {packages_str} --registry https://registry.npmmirror.com'
            else:
                install_cmd = f'{npm_cmd} install --registry https://registry.npmmirror.com'
            
            result = subprocess.run(
                install_cmd,
                shell=True,
                cwd=work_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=300
            )
            
            if result.returncode == 0:
                logger.info("npm依赖包安装成功完成")
            else:
                logger.warning(f"npm安装过程出现警告: {result.stderr}")
        except subprocess.TimeoutExpired:
            logger.warning("npm安装过程超时，但可能已部分完成")
        except Exception as e:
            logger.error(f"npm包安装过程中发生错误: {str(e)}")
    
    def start_browsergap(self, port: int = 8081, target_url: str = "https://fh.dji.com") -> bool:
        """
        启动优化版浏览器隔离服务 - 快速模式
        """
        try:
            # 快速模式：跳过前置条件检查以加快启动
            if not self._fast_mode:
                prereq_check = self.check_prerequisites()
                if not prereq_check["success"]:
                    logger.error(f"前置条件检查失败: {', '.join(prereq_check['issues'])}")
                    return False
            else:
                logger.info("快速模式: 跳过前置条件检查，直接启动服务")
            
            self.port = port
            self.base_url = f"http://{self.host}:{self.port}"
            self.websocket_url = f"ws://{self.host}:{self.port}"
            
            if self._is_port_in_use(port):
                logger.info(f"端口 {port} 被占用，正在终止现有进程")
                self._kill_process_on_port(port)
                time.sleep(2)  # 缩短等待时间
            
            # 使用固定的Node.js路径
            node_cmd = self.node_path if os.path.exists(self.node_path) else 'node'
            start_cmd = f'"{node_cmd}" "{self.server_script_path}" {port} "{target_url}"'
            
            logger.info(f"执行启动命令: {start_cmd}")
            logger.info(f"目标网址: {target_url}")
            
            env = os.environ.copy()
            env['NODE_ENV'] = 'production'
            env['PYTHONIOENCODING'] = 'utf-8'
            
            # 优化Chrome路径检测
            chrome_paths = [
                r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
                os.path.expanduser(r'~\AppData\Local\Google\Chrome\Application\chrome.exe'),
            ]
            chrome_found = False
            for chrome_path in chrome_paths:
                if os.path.exists(chrome_path):
                    env['CHROME_PATH'] = chrome_path
                    env['PUPPETEER_EXECUTABLE_PATH'] = chrome_path
                    logger.info(f"Chrome路径环境变量设置: {chrome_path}")
                    chrome_found = True
                    break
            if not chrome_found:
                logger.error("Chrome浏览器未找到，服务可能无法正常启动")
                return False
            
            # 添加Node.js路径到PATH环境变量
            if self.node_path and os.path.dirname(self.node_path) not in env.get('PATH', ''):
                env['PATH'] = os.path.dirname(self.node_path) + os.pathsep + env.get('PATH', '')
            
            if platform.system() == 'Windows':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                
                self.process = subprocess.Popen(
                    start_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True,
                    env=env,
                    startupinfo=startupinfo,
                    encoding='utf-8',
                    errors='replace',
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                self.process = subprocess.Popen(
                    start_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True,
                    env=env,
                    encoding='utf-8',
                    errors='replace',
                    preexec_fn=os.setsid
                )
            
            self._start_output_threads()
            
            logger.info("等待服务完成初始化")
            time.sleep(3)  # 缩短等待时间从5秒到3秒
            
            if self.process.poll() is None:
                if self._wait_for_service():
                    self.is_running = True
                    logger.info(f"浏览器隔离服务成功启动，运行端口: {port}")
                    logger.info(f"WebSocket连接地址: {self.websocket_url}")
                    logger.info(f"HTTP API地址: {self.base_url}")
                    return True
                else:
                    logger.error("服务未能正常响应健康检查")
                    self.stop_browsergap()
                    return False
            else:
                logger.error(f"服务进程启动失败，退出代码: {self.process.returncode}")
                return False
            
        except Exception as e:
            logger.error(f"启动浏览器隔离服务时发生错误: {str(e)}")
            return False
    
    def _start_output_threads(self):
        """
        启动后台线程监控服务器输出
        """
        def read_stdout():
            try:
                for line in iter(self.process.stdout.readline, ''):
                    if line:
                        logger.info(f"[服务器输出]: {line.strip()}")
            except Exception as e:
                logger.debug(f"读取标准输出流错误: {e}")
        
        def read_stderr():
            try:
                for line in iter(self.process.stderr.readline, ''):
                    if line:
                        logger.warning(f"[服务器错误]: {line.strip()}")
            except Exception as e:
                logger.debug(f"读取错误输出流错误: {e}")
        
        stdout_thread = threading.Thread(target=read_stdout, daemon=True)
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stdout_thread.start()
        stderr_thread.start()
    
    def stop_browsergap(self) -> bool:
        """
        停止浏览器隔离服务并清理资源
        """
        try:
            if self.is_running:
                try:
                    requests.post(f"{self.base_url}/api/shutdown", timeout=5)
                    time.sleep(1)
                except:
                    pass
            
            if self.process:
                logger.info("正在终止浏览器隔离服务进程")
                
                if platform.system() == 'Windows':
                    try:
                        subprocess.run(
                            f'taskkill /F /T /PID {self.process.pid}',
                            shell=True,
                            capture_output=True,
                            timeout=10
                        )
                    except:
                        self.process.terminate()
                        try:
                            self.process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            self.process.kill()
                            self.process.wait(timeout=5)
                else:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                    try:
                        self.process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                        self.process.wait(timeout=5)
                
                self.process = None
                self.is_running = False
                logger.info("浏览器隔离服务已成功停止")
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"停止浏览器隔离服务时发生错误: {str(e)}")
            self.is_running = False
            self.process = None
            self._kill_process_on_port(self.port)
            return False
    
    def get_service_status(self) -> Dict:
        """
        获取服务运行状态和详细信息 - 优化版本，增加连接状态管理
        """
        try:
            # 检查进程状态
            if self.process and self.process.poll() is not None:
                self.is_running = False
                self.process = None
                logger.warning("服务进程意外终止")
            
            if not self.is_running:
                return {
                    "status": "stopped",
                    "url": None,
                    "websocket_url": None,
                    "port": self.port,
                    "message": "服务当前未运行",
                    "reconnect_available": True
                }
            
            # 尝试连接服务，增加重试机制
            response = None
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = requests.get(f"{self.base_url}/api/status", timeout=3)
                    break
                except requests.exceptions.RequestException as e:
                    if attempt == max_retries - 1:
                        logger.warning(f"服务状态检查失败，尝试 {attempt + 1}/{max_retries}: {str(e)}")
                        # 服务可能失去响应，但不立即停止
                        return {
                            "status": "unhealthy",
                            "url": self.base_url,
                            "websocket_url": self.websocket_url,
                            "port": self.port,
                            "message": "服务无响应，建议重启",
                            "error": str(e),
                            "reconnect_available": True
                        }
                    time.sleep(0.5)
            
            if response and response.status_code == 200:
                data = response.json()
                
                return {
                    "status": "running",
                    "url": self.base_url,
                    "websocket_url": self.websocket_url,
                    "port": self.port,
                    "response_time": response.elapsed.total_seconds(),
                    "initialized": data.get("initialized", False),
                    "clients": data.get("clients", 0),
                    "performance_mode": data.get("performanceMode", "unknown"),
                    "reconnect_available": False,
                    "details": data
                }
            else:
                return {
                    "status": "error",
                    "url": self.base_url,
                    "websocket_url": self.websocket_url,
                    "port": self.port,
                    "message": f"服务响应异常: {response.status_code if response else 'No response'}",
                    "reconnect_available": True
                }
                return {
                    "status": "error",
                    "url": self.base_url,
                    "websocket_url": self.websocket_url,
                    "port": self.port,
                    "error": f"HTTP响应错误 {response.status_code}"
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "status": "error" if self.is_running else "stopped",
                "url": self.base_url,
                "websocket_url": self.websocket_url,
                "port": self.port,
                "error": f"连接错误: {str(e)}"
            }
        except Exception as e:
            return {
                "status": "unknown",
                "url": self.base_url,
                "websocket_url": self.websocket_url,
                "port": self.port,
                "error": f"状态检查异常: {str(e)}"
            }
    
    def navigate_to_url(self, url: str) -> Dict:
        """
        通过API导航到指定网址 - 优化版本，增加重试机制
        """
        try:
            if not self.is_running:
                return {
                    "success": False,
                    "error": "服务当前未运行",
                    "reconnect_needed": True
                }
            
            # 增加重试机制
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        f"{self.base_url}/api/navigate",
                        json={"url": url},
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        return {
                            "success": True,
                            "message": "导航操作成功完成",
                            "url": url,
                            "attempt": attempt + 1
                        }
                    else:
                        if attempt == max_retries - 1:  # 最后一次尝试
                            return {
                                "success": False,
                                "error": f"导航操作失败: HTTP {response.status_code}",
                                "reconnect_needed": True
                            }
                        time.sleep(1)  # 等待然后重试
                        
                except requests.exceptions.RequestException as e:
                    if attempt == max_retries - 1:
                        return {
                            "success": False,
                            "error": f"导航操作连接失败: {str(e)}",
                            "reconnect_needed": True
                        }
                    time.sleep(1)
                    
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "导航操作超时",
                "reconnect_needed": False
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"导航操作异常: {str(e)}",
                "reconnect_needed": True
            }
    
    def set_performance_mode(self, mode: str) -> Dict:
        """
        设置服务性能模式
        支持的模式: quality, balanced, performance
        """
        valid_modes = ['quality', 'balanced', 'performance']
        if mode not in valid_modes:
            return {
                "success": False,
                "error": f"无效的性能模式，支持的模式: {', '.join(valid_modes)}"
            }
        
        try:
            if not self.is_running:
                return {
                    "success": False,
                    "error": "服务当前未运行"
                }
            
            # 通过WebSocket发送性能模式设置命令
            # 这里可以扩展为HTTP API调用
            self.performance_mode = mode
            return {
                "success": True,
                "message": f"性能模式已设置为: {mode}",
                "mode": mode
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"设置性能模式时发生错误: {str(e)}"
            }
    
    def restart_service(self, port: int = None, target_url: str = None) -> Dict:
        """
        重启服务 - 新增方法，用于解决连接问题
        """
        try:
            logger.info("正在重启浏览器隔离服务")
            
            # 停止当前服务
            stop_result = self.stop_browsergap()
            if not stop_result:
                logger.warning("停止服务时出现问题，尝试强制清理")
                self._kill_process_on_port(port or self.port)
            
            # 等待一段时间确保资源释放
            time.sleep(3)
            
            # 重新启动服务
            start_result = self.start_browsergap(
                port or self.port, 
                target_url or "https://fh.dji.com"
            )
            
            if start_result:
                return {
                    "success": True,
                    "message": "服务重启成功",
                    "service_url": self.base_url,
                    "websocket_url": self.websocket_url
                }
            else:
                return {
                    "success": False,
                    "error": "服务重启失败"
                }
                
        except Exception as e:
            logger.error(f"重启服务时发生错误: {str(e)}")
            return {
                "success": False,
                "error": f"重启服务失败: {str(e)}"
            }
    
    def _wait_for_service(self) -> bool:
        """
        等待服务完成启动并响应健康检查
        """
        logger.info(f"等待服务在 {self.base_url} 完成启动")
        start_time = time.time()
        max_wait = self.startup_timeout
        
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(f"{self.base_url}/health", timeout=5)
                if response.status_code == 200:
                    logger.info("服务健康检查通过")
                    return True
            except requests.exceptions.RequestException as e:
                if "Connection refused" in str(e) or "Max retries exceeded" in str(e):
                    pass
                else:
                    logger.debug(f"等待服务启动时发生错误: {str(e)}")
            
            if self.process and self.process.poll() is not None:
                logger.error(f"服务进程异常退出，退出代码: {self.process.returncode}")
                return False
            
            time.sleep(2)
        
        logger.error(f"等待服务启动超时（{max_wait}秒）")
        return False
    
    def _is_port_in_use(self, port: int) -> bool:
        """
        检查指定端口是否被占用
        """
        try:
            connections = psutil.net_connections()
            for conn in connections:
                if hasattr(conn, 'laddr') and conn.laddr.port == port:
                    return True
        except (psutil.AccessDenied, AttributeError):
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.settimeout(1)
                result = sock.connect_ex((self.host, port))
                sock.close()
                return result == 0
            except:
                return False
        except Exception as e:
            logger.debug(f"端口占用检查时发生错误: {str(e)}")
        
        return False
    
    def _kill_process_on_port(self, port: int):
        """
        终止占用指定端口的进程
        """
        try:
            connections = psutil.net_connections()
            killed_pids = set()
            
            for conn in connections:
                if hasattr(conn, 'laddr') and conn.laddr.port == port and conn.pid:
                    if conn.pid not in killed_pids:
                        try:
                            process = psutil.Process(conn.pid)
                            process_name = process.name()
                            logger.info(f"终止占用端口{port}的进程: {process_name} (PID: {conn.pid})")
                            process.terminate()
                            
                            try:
                                process.wait(timeout=5)
                            except psutil.TimeoutExpired:
                                process.kill()
                                process.wait(timeout=5)
                            
                            killed_pids.add(conn.pid)
                        except psutil.NoSuchProcess:
                            pass
                        except psutil.AccessDenied:
                            logger.warning(f"权限不足，无法终止进程 PID: {conn.pid}")
                        except Exception as e:
                            logger.debug(f"终止进程时发生错误: {str(e)}")
            
            if killed_pids:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"清理端口资源时发生错误: {str(e)}")

    def _uninstall_puppeteer(self):
        """
        卸载旧版本puppeteer包
        """
        try:
            work_dir = os.path.dirname(self.server_script_path)
            npm_cmd = self.npm_path or 'npm'
            
            logger.info("正在卸载puppeteer包")
            
            uninstall_cmd = f'{npm_cmd} uninstall puppeteer'
            
            result = subprocess.run(
                uninstall_cmd,
                shell=True,
                cwd=work_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info("puppeteer包卸载成功")
            else:
                logger.warning(f"卸载puppeteer包时出现警告: {result.stderr}")
                
        except Exception as e:
            logger.error(f"卸载puppeteer包时发生错误: {str(e)}")

# 全局管理器实例，用于Flask应用集成
browsergap_manager = BrowserGapManager()