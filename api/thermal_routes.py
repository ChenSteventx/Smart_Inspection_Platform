"""
热成像API路由模块 - 完全按照app_14.py接口格式
"""
from flask import Blueprint, request, jsonify
from services.thermal_service import thermal_service

thermal_bp = Blueprint("thermal", __name__)

@thermal_bp.route("/upload-thermal-image", methods=["POST"])
def upload_thermal_image():
    """上传热成像图片 - 完全按照app_14.py接口格式"""
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "未上传文件"}), 400
    
    # 调用服务处理，但按app_14.py格式返回
    result = thermal_service.upload_thermal_image(file, file.filename)
    
    if not result["success"]:
        return jsonify({"error": result["error"]}), 500
    
    # 按照app_14.py的格式返回，去掉success包装
    return jsonify({
        "fileId": result["fileId"],
        "message": result["message"],
        "original_plot_base64": result["original_plot_base64"],
        "plot_base64": result["plot_base64"],
        "highest_temp_info": result["highest_temp_info"],
        "has_warning": result["has_warning"],
        "warning_type": result["warning_type"]
    }), 200

@thermal_bp.route("/list-thermal-files", methods=["GET"])
def list_thermal_files():
    """列出所有已上传的热成像文件 - 完全按照app_14.py接口格式"""
    result = thermal_service.list_thermal_files()
    
    if not result["success"]:
        return jsonify({
            "success": False,
            "error": result["error"]
        }), 500
    
    # 按照app_14.py格式返回
    return jsonify({
        "success": True,
        "files": result["files"]
    }), 200

@thermal_bp.route("/get-thermal-data/<file_id>", methods=["GET"])
def get_thermal_data(file_id):
    """获取热成像数据 - 完全按照app_14.py接口格式"""
    result = thermal_service.get_thermal_data(file_id)
    
    if not result["success"]:
        return jsonify({"error": result["error"]}), 404
    
    # 按照app_14.py格式返回，直接返回数据，不包装success
    return jsonify({
        "original_plot_base64": result["original_plot_base64"],
        "plot_base64": result["plot_base64"],
        "highest_temp_info": result["highest_temp_info"],
        "has_warning": result["has_warning"],
        "warning_type": result["warning_type"]
    }), 200

@thermal_bp.route("/get-temperature/<file_id>", methods=["GET"])
def get_temperature(file_id):
    """获取指定热成像图片的温度数据，根据前端传入的 x 和 y 坐标返回对应温度值 - 完全按照app_14.py接口格式"""
    try:
        x = request.args.get('x', type=int)
        y = request.args.get('y', type=int)
        if x is None or y is None:
            return jsonify({"error": "缺少 x 或 y 参数"}), 400
        
        result = thermal_service.get_temperature(file_id, x, y)
        
        if not result["success"]:
            return jsonify({"error": result["error"]}), 404
        
        # 按照app_14.py格式返回，直接返回数据
        return jsonify({
            "x": result["x"],
            "y": result["y"],
            "temperature": result["temperature"],
            "has_warning": result["has_warning"]
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"获取温度数据错误: {str(e)}"}), 500

@thermal_bp.route("/delete-thermal-image/<file_id>", methods=["DELETE"])
def delete_thermal_image(file_id):
    """删除指定热成像图片文件及相关数据 - 完全按照app_14.py接口格式"""
    result = thermal_service.delete_thermal_image(file_id)
    
    if not result["success"]:
        return jsonify({"error": result["error"]}), 500
    
    # 按照app_14.py格式返回
    return jsonify({"message": result["message"]}), 200

@thermal_bp.route("/delete-thermal-data/<file_id>", methods=["DELETE"])
def delete_thermal_data(file_id):
    """删除指定热成像数据及相关文件 - 完全按照app_14.py接口格式"""
    return delete_thermal_image(file_id)

@thermal_bp.route("/get-warnings", methods=["GET"])
def get_warnings():
    """获取所有预警信息 - 完全按照app_14.py接口格式"""
    file_id = request.args.get('fileId')
    
    if file_id:
        # 获取特定文件的预警
        result = thermal_service.get_warnings(file_id)
        if result["success"] and result["warning"]:
            return jsonify({
                "thermal": result["warning"],
                "tdms": None  # 保持app_14.py格式
            }), 200
        else:
            return jsonify({
                "thermal": None,
                "tdms": None
            }), 200
    else:
        # 获取所有预警
        result = thermal_service.get_warnings()
        if result["success"]:
            return jsonify({
                "thermal": [
                    {
                        "fileId": warning["fileId"],
                        "warning": warning["warning"]
                    } for warning in result["warnings"]
                ],
                "tdms": []  # 保持app_14.py格式
            }), 200
        else:
            return jsonify({
                "thermal": [],
                "tdms": []
            }), 200