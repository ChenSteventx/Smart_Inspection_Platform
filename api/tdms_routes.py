"""
TDMS API路由模块
"""
from flask import Blueprint, request, jsonify, send_from_directory, Response
from urllib.parse import quote
import os
from services.tdms_service import tdms_service
from config.settings import Config

tdms_bp = Blueprint("tdms", __name__)

@tdms_bp.route("/upload-tdms", methods=["POST"])
def upload_tdms():
    """上传TDMS文件"""
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "未上传文件"}), 400
    
    result = tdms_service.upload_tdms(file, file.filename)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code

@tdms_bp.route("/process-tdms", methods=["POST"])
def process_tdms():
    """处理TDMS文件，将数据转换为图像并返回图像的base64编码"""
    file_id = request.form.get("fileId") or request.json.get("fileId")
    if not file_id:
        return jsonify({"error": "未提供 fileId"}), 400
    
    result = tdms_service.process_tdms(file_id)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code

@tdms_bp.route("/get-latest-tdms-image", methods=["GET"])
def get_latest_tdms_image():
    """获取最新的已处理TDMS图像数据，用于导航界面预览"""
    result = tdms_service.get_latest_tdms_image()
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code

@tdms_bp.route("/get-tdms-summary", methods=["GET"])
def get_tdms_summary():
    """获取TDMS文件处理概要信息，用于导航界面显示统计数据"""
    result = tdms_service.get_tdms_summary()
    status_code = 200 if result["success"] else 500
    return jsonify(result), status_code

@tdms_bp.route("/process-tdms-to-excel", methods=["POST"])
def process_tdms_to_excel():
    """异步处理TDMS文件转换为Excel文件"""
    data = request.get_json() or {}
    file_id = data.get("fileId")
    
    if not file_id:
        return jsonify({"error": "未提供 fileId"}), 400
    
    result = tdms_service.process_tdms_to_excel(file_id)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code

@tdms_bp.route("/get-task-status/<file_id>", methods=["GET"])
def get_task_status(file_id):
    """获取任务处理状态"""
    result = tdms_service.get_task_status(file_id)
    return jsonify(result), 200

@tdms_bp.route("/get-all-task-status", methods=["GET"])
def get_all_task_status():
    """获取所有正在进行的任务状态"""
    result = tdms_service.get_all_task_status()
    return jsonify(result), 200

@tdms_bp.route("/download-excel/<file_id>", methods=["GET"])
def download_excel(file_id):
    """下载生成的Excel文件"""
    try:
        xlsx_name = f"{file_id}.xlsx"
        xlsx_path = Config.UPLOAD_FOLDER / xlsx_name
        
        if not xlsx_path.exists():
            return jsonify({"error": "未找到 Excel 文件"}), 404
        
        # 获取原始文件名并处理
        original_name = "tdms_data"
        if file_id in tdms_service.tdms_file_metadata:
            original_name = tdms_service.tdms_file_metadata[file_id].get("original_name", "tdms_data")
            if original_name.lower().endswith('.tdms'):
                original_name = original_name[:-5]  # 移除.tdms扩展名
            elif original_name.lower().endswith('.xlsx'):
                original_name = original_name[:-5]  # 移除.xlsx扩展名，后面会重新添加
        
        # 确保文件名安全，移除特殊字符
        safe_filename = "".join(c for c in original_name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
        if not safe_filename:
            safe_filename = f"tdms_data_{file_id[:8]}"
        
        download_filename = f"{safe_filename}.xlsx"
        
        # 使用 URL 编码处理中文文件名
        encoded_filename = quote(download_filename.encode('utf-8'))
        
        def generate():
            with open(xlsx_path, 'rb') as f:
                while True:
                    data = f.read(4096)
                    if not data:
                        break
                    yield data
        
        response = Response(
            generate(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={
                'Content-Disposition': f'attachment; filename="{download_filename}"; filename*=UTF-8\'\'{encoded_filename}',
                'Content-Length': str(xlsx_path.stat().st_size)
            }
        )
        
        return response
        
    except Exception as e:
        return jsonify({"error": f"下载文件失败: {str(e)}"}), 500

@tdms_bp.route("/download-tdms/<file_id>", methods=["GET"])
def download_tdms(file_id):
    """下载TDMS文件"""
    try:
        tdms_name = f"{file_id}.tdms"
        tdms_path = Config.UPLOAD_FOLDER / tdms_name
        
        if not tdms_path.exists():
            return jsonify({"error": "未找到文件"}), 404
        
        # 获取原始文件名
        original_name = f"tdms_file_{file_id[:8]}.tdms"
        if file_id in tdms_service.tdms_file_metadata:
            original_name = tdms_service.tdms_file_metadata[file_id].get("original_name", original_name)
        
        # 确保文件名安全
        safe_filename = "".join(c for c in original_name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
        if not safe_filename:
            safe_filename = f"tdms_file_{file_id[:8]}.tdms"
        
        # 使用 URL 编码处理中文文件名
        encoded_filename = quote(safe_filename.encode('utf-8'))
        
        def generate():
            with open(tdms_path, 'rb') as f:
                while True:
                    data = f.read(4096)
                    if not data:
                        break
                    yield data
        
        response = Response(
            generate(),
            mimetype='application/octet-stream',
            headers={
                'Content-Disposition': f'attachment; filename="{safe_filename}"; filename*=UTF-8\'\'{encoded_filename}',
                'Content-Length': str(tdms_path.stat().st_size)
            }
        )
        
        return response
        
    except Exception as e:
        return jsonify({"error": f"下载TDMS文件失败: {str(e)}"}), 500

@tdms_bp.route("/get-excel-data/<file_id>", methods=["GET"])
def get_excel_data(file_id):
    """获取Excel数据，支持分页显示"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 50, type=int)
    
    result = tdms_service.get_excel_data(file_id, page, page_size)
    status_code = 200 if result["success"] else 500
    return jsonify(result), status_code

@tdms_bp.route("/delete-tdms/<file_id>", methods=["DELETE"])
def delete_tdms(file_id):
    """删除TDMS文件及相关数据"""
    result = tdms_service.delete_tdms(file_id)
    status_code = 200 if result["success"] else 500
    return jsonify(result), status_code