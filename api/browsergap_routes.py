"""
BrowserGap API路由模块
"""
from flask import Blueprint, request, jsonify
from services.browsergap_service import browsergap_service

browsergap_bp = Blueprint('browsergap', __name__)

@browsergap_bp.route('/start', methods=['POST'])
def start_browsergap_service():
    """启动BrowserGap服务"""
    data = request.get_json() or {}
    port = data.get('port')
    target_url = data.get('target_url')
    
    result = browsergap_service.start_service(port, target_url)
    status_code = 200 if result["success"] else 500
    return jsonify(result), status_code

@browsergap_bp.route('/stop', methods=['POST'])
def stop_browsergap_service():
    """停止BrowserGap服务"""
    result = browsergap_service.stop_service()
    status_code = 200 if result["success"] else 500
    return jsonify(result), status_code

@browsergap_bp.route('/status', methods=['GET'])
def get_browsergap_status():
    """获取BrowserGap服务状态"""
    result = browsergap_service.get_status()
    status_code = 200 if result["success"] else 500
    return jsonify(result), status_code

@browsergap_bp.route('/performance-mode', methods=['POST'])
def set_performance_mode():
    """设置BrowserGap服务性能模式"""
    data = request.get_json() or {}
    mode = data.get('mode', 'balanced')
    
    result = browsergap_service.set_performance_mode(mode)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code

@browsergap_bp.route('/performance-mode', methods=['GET'])
def get_performance_mode():
    """获取当前性能模式"""
    result = browsergap_service.get_performance_mode()
    status_code = 200 if result["success"] else 500
    return jsonify(result), status_code

@browsergap_bp.route('/navigate', methods=['POST'])
def navigate_to_url():
    """导航到指定URL"""
    data = request.get_json() or {}
    target_url = data.get('url')
    wait_for_load = data.get('wait_for_load', True)
    
    if not target_url:
        return jsonify({
            "success": False,
            "error": "缺少URL参数"
        }), 400
    
    result = browsergap_service.navigate_to_url(target_url, wait_for_load)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code

@browsergap_bp.route('/embed-info', methods=['GET'])
def get_embed_info():
    """获取Vue组件嵌入信息"""
    result = browsergap_service.get_embed_info()
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code

@browsergap_bp.route('/prerequisites', methods=['GET'])
def check_prerequisites():
    """检查BrowserGap服务运行前置条件"""
    result = browsergap_service.check_prerequisites()
    
    # 确保响应格式符合前端期望，即使检查失败也返回200状态码
    # 前端JavaScript期望响应中包含issues字段
    if 'issues' not in result:
        result['issues'] = result.get('error', ['前置条件检查失败']) if not result.get('success') else []
    
    # 始终返回200状态码，通过success字段表示检查结果
    return jsonify(result), 200

@browsergap_bp.route('/restart', methods=['POST'])
def restart_browsergap_service():
    """重启BrowserGap服务 - 新增接口，用于解决连接问题"""
    data = request.get_json() or {}
    port = data.get('port')
    target_url = data.get('target_url')
    
    result = browsergap_service.restart_service(port, target_url)
    status_code = 200 if result["success"] else 500
    return jsonify(result), status_code
