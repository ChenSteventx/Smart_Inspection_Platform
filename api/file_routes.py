"""
文件管理API路由模块
"""
from flask import Blueprint, request, jsonify
from services.thermal_service import thermal_service
from services.tdms_service import tdms_service
from storage.warnings_storage import warnings_storage
import os
import shutil
import subprocess
import base64
from config.settings import Config

file_bp = Blueprint("file", __name__)

@file_bp.route("/execute-command", methods=["POST"])
def execute_command():
    """处理前端发送的命令请求"""
    data = request.get_json()
    if not data or "command" not in data:
        return jsonify({"error": "未提供命令内容"}), 400
    
    file_content = data["command"]
    try:
        # 步骤1：将txt文件内容写入到目标文件，覆盖原有内容
        tmp_txt_path = Config.ABAQUS_TMP_PATH
        os.makedirs(os.path.dirname(tmp_txt_path), exist_ok=True)
        with open(tmp_txt_path, "w", encoding="utf-8") as f:
            f.write(file_content)
        
        # 步骤2：清空文件夹下的所有文件和文件夹
        target_directory = Config.ABAQUS_OUTPUT_DIR
        os.makedirs(target_directory, exist_ok=True)
        
        for filename in os.listdir(target_directory):
            file_path = os.path.join(target_directory, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                return jsonify({"error": f"删除 {file_path} 时出错: {e}"}), 500
        
        # 步骤3：执行命令
        cmd = "abq6131 cae noGui=server-abap.py"
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300)
        if result.returncode != 0:
            return jsonify({"error": "执行 abq6131 脚本失败", "details": result.stderr}), 500
        
        # 步骤4：读取生成的结果图片
        output_img_path = Config.ABAQUS_OUTPUT_IMAGE
        if not os.path.exists(output_img_path):
            return jsonify({"error": "结果图片未找到"}), 500
        
        with open(output_img_path, "rb") as img_file:
            img_data = img_file.read()
        img_base64 = base64.b64encode(img_data).decode('utf-8')
        
        return jsonify({"output": img_base64, "message": "执行成功"}), 200
        
    except subprocess.TimeoutExpired:
        return jsonify({"error": "命令执行超时"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@file_bp.route("/get-warnings", methods=["GET"])
def get_warnings():
    """获取所有预警信息 - 优化版本，使用全局预警存储"""
    file_id = request.args.get('fileId')
    
    if file_id:
        # 获取特定文件的预警
        thermal_warning = warnings_storage.get_thermal_warning(file_id)
        tdms_warning = warnings_storage.get_tdms_warning(file_id)
        
        return jsonify({
            "thermal": thermal_warning,
            "tdms": tdms_warning
        }), 200
    else:
        # 获取所有预警 - 使用全局存储
        active_warnings = warnings_storage.get_all_warnings()
        return jsonify(active_warnings), 200

@file_bp.route("/get-warnings-count", methods=["GET"])
def get_warnings_count():
    """获取预警数量统计 - 新增接口"""
    try:
        count_info = warnings_storage.get_warnings_count()
        return jsonify({
            "success": True,
            "count": count_info
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500