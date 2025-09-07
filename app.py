"""
Smart Inspection Platform - 智能巡检平台
主应用入口文件

本项目是一个基于Flask的智能巡检系统，整合了：
- 浏览器远程控制服务
- TDMS数据处理
- 热成像图像分析
- 知识图谱检索
- 文件管理和任务调度

运行端口：5001
"""

from flask import Flask
from flask_cors import CORS
import os
import logging
import time

# 导入配置
from config.settings import Config
from config.database import init_database

# 导入蓝图路由
from api.browsergap_routes import browsergap_bp
from api.tdms_routes import tdms_bp
from api.thermal_routes import thermal_bp
from api.knowledge_routes import knowledge_bp
from api.file_routes import file_bp

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """创建Flask应用实例"""
    app = Flask(__name__)
    
    # 加载配置
    app.config.from_object(Config)
    
    # 配置CORS
    CORS(app, origins=['http://localhost:3000', 'http://localhost:8080'], supports_credentials=True)
    
    # 初始化数据库连接
    init_database()
    
    # 初始化存储目录
    Config.init_directories()
    
    # 注册蓝图
    app.register_blueprint(browsergap_bp, url_prefix='/api/browsergap')
    app.register_blueprint(tdms_bp, url_prefix='/api')
    app.register_blueprint(thermal_bp, url_prefix='/api')
    app.register_blueprint(knowledge_bp, url_prefix='/api')
    app.register_blueprint(file_bp, url_prefix='/api')
    
    # 健康检查路由
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """健康检查"""
        from flask import jsonify
        return jsonify({
            "success": True,
            "message": "Smart Inspection Platform 运行正常",
            "timestamp": time.time(),
            "version": "1.0.0"
        }), 200
    
    return app

if __name__ == "__main__":
    app = create_app()
    logger.info("Smart Inspection Platform 启动中...")
    logger.info("浏览器远程控制服务端口: 8081")
    logger.info("Flask API服务端口: 5001")
    logger.info("API接口文档:")
    logger.info("  /api/health - 健康检查")
    logger.info("  /api/browsergap/* - 浏览器控制服务")
    logger.info("  /api/upload-tdms - TDMS文件上传")
    logger.info("  /api/upload-thermal-image - 热成像图片上传")
    logger.info("  /api/search - 知识图谱检索")
    
    app.run(debug=True, port=5001, threaded=True)
