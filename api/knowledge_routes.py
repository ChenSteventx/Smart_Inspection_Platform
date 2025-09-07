"""
知识图谱API路由模块
"""
from flask import Blueprint, request, jsonify, send_from_directory
from services.knowledge_service import knowledge_service
from config.settings import Config

knowledge_bp = Blueprint("knowledge", __name__)

@knowledge_bp.route("/search", methods=["POST"])
def wstm_search_api():
    """搜索API，返回JSON格式的搜索结果"""
    if request.method != "POST":
        return jsonify({"error": "只支持POST请求"}), 405
    
    # 获取请求数据
    data = request.get_json()
    if not data or "keyword" not in data:
        return jsonify({"error": "缺少keyword参数"}), 400
    
    keyword = data["keyword"]
    result = knowledge_service.search_knowledge(keyword)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code

@knowledge_bp.route("/hot-search", methods=["GET"])
def hot_search_api():
    """获取热搜数据API"""
    result = knowledge_service.get_hot_search()
    status_code = 200 if result["success"] else 500
    return jsonify(result), status_code

@knowledge_bp.route("/pdf/<filename>", methods=["GET"])
def serve_pdf(filename):
    """提供PDF文件下载或预览"""
    try:
        return send_from_directory(
            Config.PDF_FOLDER,
            "A.pdf",
            as_attachment=False,
            mimetype="application/pdf"
        )
    except Exception as e:
        return jsonify({"error": f"提供PDF文件时出错: {str(e)}"}), 500
