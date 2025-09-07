"""
热成像处理服务模块
完全按照app_14.py的处理方式实现，保持接口兼容性
"""
import os
import uuid
import time
import json
import subprocess
import tempfile
import base64
import glob

import numpy as np
import cv2

from config.settings import Config

# 完全按照app_14.py：使用全局字典存储数据
temperature_data_store = {}
thermal_data_store = {}
file_metadata_store = {}

# 完全按照app_14.py：使用全局字典存储预警信息
warnings_store = {
    "thermal": {},
    "tdms": {}
}

class ThermalService:
    """热成像处理服务 - 完全按照app_14.py实现"""
    
    def __init__(self):
        # 确保必要目录存在
        Config.init_directories()
        
        # 加载已有数据
        load_thermal_data()
    
    def upload_thermal_image(self, file, original_filename=None):
        """上传热成像图片并处理 - 完全按照app_14.py实现"""
        if not file:
            return {
                "success": False,
                "error": "未上传文件"
            }
        
        file_id = str(uuid.uuid4())
        jpg_filename = f"{file_id}.jpg"
        jpg_path = Config.UPLOAD_FOLDER / jpg_filename
        file.save(jpg_path)
        
        upload_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        
        try:
            with open(jpg_path, "rb") as image_file:
                original_image_bytes = image_file.read()
                original_image_base64 = base64.b64encode(original_image_bytes).decode('utf-8')
        except Exception as e:
            print(f"读取原始图片错误: {str(e)}")
            return {
                "success": False,
                "error": "读取上传图片失败"
            }
        
        # 使用app_14.py的全局函数
        raw_path = process_with_dji_irp(str(jpg_path))
        if not raw_path or not os.path.exists(raw_path):
            return {
                "success": False,
                "error": "处理热成像图片失败"
            }
        
        temperature_matrix = extract_temperature_from_raw(raw_path)
        os.remove(raw_path)
        
        if temperature_matrix is None:
            return {
                "success": False,
                "error": "提取温度数据失败"
            }
        
        highest_temp_info = find_highest_temperature_point(temperature_matrix)
        
        has_warning = highest_temp_info["highest_temp"] > 50.0
        warning_message = None
        
        # 直接使用全局字典存储预警，与 app_7.py 保持一致
        if has_warning:
            warning_message = "外壁超温"
            warnings_store["thermal"][file_id] = {
                "type": warning_message,
                "temperature": highest_temp_info["highest_temp"],
                "threshold": 50.0,
                "position": highest_temp_info["highest_point"]
            }
            # 保存预警信息到文件
            warnings_path = Config.METADATA_FOLDER / "warnings.json"
            with open(warnings_path, "w", encoding="utf-8") as f:
                json.dump(warnings_store, f, ensure_ascii=False, indent=2)
        else:
            warnings_store["thermal"].pop(file_id, None)
        
        try:
            image = cv2.imread(str(jpg_path))
            if image is None:
                return {
                    "success": False,
                    "error": "读取上传图片进行标记失败"
                }
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            marked_image_base64 = generate_marked_image(image, highest_temp_info)
        except Exception as e:
            print(f"生成标记图片错误: {str(e)}")
            return {
                "success": False,
                "error": "生成标记图片失败"
            }
        
        temperature_data_store[file_id] = temperature_matrix.tolist()
        
        thermal_data = {
            "original_plot_base64": original_image_base64,
            "plot_base64": marked_image_base64,
            "highest_temp_info": highest_temp_info,
            "has_warning": has_warning,
            "warning_type": warning_message
        }
        thermal_data_store[file_id] = thermal_data
        
        # 完全按照app_14.py: 保存热成像数据到文件
        thermal_data_path = Config.THERMAL_DATA_FOLDER / f"{file_id}.json"
        with open(thermal_data_path, "w", encoding="utf-8") as f:
            json.dump(thermal_data, f, ensure_ascii=False, indent=2)
        
        # 保存温度数据到文件
        temperature_data_path = Config.THERMAL_DATA_FOLDER / f"{file_id}_temp.json"
        with open(temperature_data_path, "w", encoding="utf-8") as f:
            json.dump(temperature_matrix.tolist(), f, ensure_ascii=False)
        
        # 完全按照app_14.py: 保存文件元数据
        file_metadata = {
            "name": original_filename or f"thermal_image_{file_id[:8]}.jpg",
            "timestamp": upload_time,
            "path": str(jpg_path),
            "has_warning": has_warning,
            "warning_type": warning_message
        }
        file_metadata_store[file_id] = file_metadata
        
        metadata_path = Config.METADATA_FOLDER / f"{file_id}_meta.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(file_metadata, f, ensure_ascii=False, indent=2)
        
        print(f"已上传热成像图片 {file_id}, original_plot_base64 长度: {len(original_image_base64)}")
        
        return {
            "success": True,
            "fileId": file_id,
            "message": "热成像图片处理成功",
            "original_plot_base64": original_image_base64,
            "plot_base64": marked_image_base64,
            "highest_temp_info": highest_temp_info,
            "has_warning": has_warning,
            "warning_type": warning_message
        }
    
    def get_temperature(self, file_id, x, y):
        """获取指定热成像图片的温度数据 - 完全按照app_14.py实现"""
        try:
            temperature_matrix = temperature_data_store.get(file_id)
            if not temperature_matrix:
                temperature_path = Config.THERMAL_DATA_FOLDER / f"{file_id}_temp.json"
                if temperature_path.exists():
                    with open(temperature_path, "r", encoding="utf-8") as f:
                        temperature_matrix = json.load(f)
                    temperature_data_store[file_id] = temperature_matrix
                else:
                    return {
                        "success": False,
                        "error": "未找到温度数据"
                    }
            
            width = 640
            height = 512
            orig_x, orig_y = x, y
            x = max(0, min(x, width - 1))
            y = max(0, min(y, height - 1))
            
            print(f"获取温度请求: 原始坐标 ({orig_x}, {orig_y}), 修正后坐标 ({x}, {y})")
            temperature = temperature_matrix[y][x]
            
            return {
                "success": True,
                "x": x,
                "y": y,
                "temperature": temperature,
                "has_warning": temperature > 50.0
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"获取温度数据错误: {str(e)}"
            }
    
    def get_thermal_data(self, file_id):
        """获取热成像数据 - 完全按照app_14.py实现"""
        thermal_data = thermal_data_store.get(file_id)
        if not thermal_data:
            thermal_data_path = Config.THERMAL_DATA_FOLDER / f"{file_id}.json"
            if thermal_data_path.exists():
                with open(thermal_data_path, "r", encoding="utf-8") as f:
                    thermal_data = json.load(f)
                thermal_data_store[file_id] = thermal_data
            else:
                return {
                    "success": False,
                    "error": "未找到热成像数据"
                }
        
        return {
            "success": True,
            **thermal_data
        }
    
    def delete_thermal_image(self, file_id):
        """删除指定热成像图片文件及相关数据 - 完全按照app_14.py实现"""
        try:
            jpg_path = Config.UPLOAD_FOLDER / f"{file_id}.jpg"
            if jpg_path.exists():
                os.remove(jpg_path)
            
            json_path = Config.THERMAL_DATA_FOLDER / f"{file_id}.json"
            if json_path.exists():
                os.remove(json_path)
            
            temp_path = Config.THERMAL_DATA_FOLDER / f"{file_id}_temp.json"
            if temp_path.exists():
                os.remove(temp_path)
            
            meta_path = Config.METADATA_FOLDER / f"{file_id}_meta.json"
            if meta_path.exists():
                os.remove(meta_path)
            
            thermal_data_store.pop(file_id, None)
            temperature_data_store.pop(file_id, None)
            file_metadata_store.pop(file_id, None)
            warnings_store["thermal"].pop(file_id, None)
            
            # 保存预警更新到文件
            warnings_path = Config.METADATA_FOLDER / "warnings.json"
            with open(warnings_path, "w", encoding="utf-8") as f:
                json.dump(warnings_store, f, ensure_ascii=False, indent=2)
            
            return {
                "success": True,
                "message": "热成像图片及相关数据删除成功"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"删除文件出错: {str(e)}"
            }
    
    def get_warnings(self, file_id=None):
        """获取预警信息 - 完全按照app_14.py实现"""
        if file_id:
            thermal_warning = warnings_store["thermal"].get(file_id)
            return {
                "success": True,
                "warning": thermal_warning
            }
        else:
            warnings_list = [
                {
                    "fileId": file_id,
                    "warning": warning_data
                } for file_id, warning_data in warnings_store["thermal"].items()
            ]
            return {
                "success": True,
                "warnings": warnings_list
            }
    
    def list_thermal_files(self):
        """列出所有已上传的热成像文件 - 完全按照app_14.py实现，修复文件名和时间读取问题"""
        try:
            files = []
            
            for file_id, metadata in file_metadata_store.items():
                # 检查文件是否存在
                jpg_path = Config.UPLOAD_FOLDER / f"{file_id}.jpg"
                if not jpg_path.exists():
                    continue
                
                # 检查是否有预警
                has_warning = file_id in warnings_store["thermal"]
                warning_type = "外壁超温" if has_warning else None
                
                # 修复文件名和时间读取 - 使用正确的字段
                file_name = metadata.get("name", f"thermal_image_{file_id[:8]}.jpg")  # 原始文件名在name字段
                upload_time = metadata.get("timestamp", "")  # 上传时间在timestamp字段
                
                print(f"文件 {file_id}: 名称={file_name}, 时间={upload_time}, 预警={has_warning}")  # 调试输出
                
                files.append({
                    "fileId": file_id,
                    "name": file_name,  # 与app_7.py保持一致，使用name字段
                    "timestamp": upload_time,  # 与app_7.py保持一致，使用timestamp字段
                    "uploading": False,
                    "has_warning": has_warning,
                    "warning_type": warning_type
                })
            
            # 按时间排序，最新的在前
            files.sort(key=lambda x: x["timestamp"], reverse=True)
            
            return {
                "success": True,
                "files": files
            }
            
        except Exception as e:
            print(f"列出文件失败: {str(e)}")  # 调试输出
            return {
                "success": False,
                "error": f"列出文件失败: {str(e)}",
                "files": []
            }


# ========================= 完全按照app_14.py的辅助函数 =========================

def process_with_dji_irp(jpg_path):
    """
    调用 DJI IRP 工具处理热成像图片，将 jpg 转换为 raw 格式文件
    """
    try:
        raw_path = tempfile.mktemp(suffix=".raw")
        command = [
            str(Config.DJI_IRP_PATH),
            "-s", jpg_path,
            "-a", "measure",
            "-o", raw_path
        ]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
        if result.returncode != 0:
            print(f"dji_irp.exe 执行失败: {result.stderr}")
            return None
        return raw_path
    except subprocess.TimeoutExpired:
        print("dji_irp.exe 执行超时")
        return None
    except Exception as e:
        print(f"运行 dji_irp.exe 时出错: {str(e)}")
        return None

def extract_temperature_from_raw(raw_path):
    """
    从 raw 文件中提取温度数据，转换为矩阵形式返回
    """
    try:
        dtype = np.int16
        # 使用内存映射提高读取效率
        with open(raw_path, 'rb') as f:
            data = np.frombuffer(f.read(), dtype=dtype)
        width, height = 640, 512
        if data.size != width * height:
            print("RAW文件大小与预期尺寸不匹配。")
            return None
        temperature_matrix = data.reshape((height, width)) / 10.0
        return temperature_matrix
    except Exception as e:
        print(f"提取温度数据时出错: {str(e)}")
        return None

def find_highest_temperature_point(temperature_matrix):
    """
    查找温度矩阵中最高温度及其位置，并返回相关信息
    """
    highest_temp = np.max(temperature_matrix)
    highest_temp_point = np.unravel_index(np.argmax(temperature_matrix), temperature_matrix.shape)
    return {
        "highest_point": [int(highest_temp_point[1]), int(highest_temp_point[0])],
        "highest_temp": float(highest_temp)
    }

def generate_marked_image(image, highest_temp_info):
    """
    在图片上标记出最高温度点，并返回标记后的图片的 base64 编码
    """
    try:
        x, y = highest_temp_info["highest_point"]
        highest_temp = highest_temp_info["highest_temp"]

        marked_image = image.copy()
        cv2.circle(marked_image, (x, y), 15, (255, 0, 0), 3)
        
        cv2.putText(
            marked_image, f"{highest_temp:.1f}°C",
            (x + 20, y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2
        )

        # 优化PNG编码参数，平衡质量和速度
        encode_params = [cv2.IMWRITE_PNG_COMPRESSION, 6]  # 0-9，6是速度和大小的平衡点
        _, buffer = cv2.imencode('.png', marked_image, encode_params)
        marked_image_base64 = base64.b64encode(buffer).decode('utf-8')
        return marked_image_base64
    except Exception as e:
        print(f"生成标记图片时出错: {str(e)}")
        return None

def load_thermal_data():
    """
    加载存储在磁盘上的热成像数据文件及元数据到内存 - 完全按照app_14.py实现
    """
    print("正在加载热成像数据...")

    # 首先加载预警信息
    warnings_path = Config.METADATA_FOLDER / "warnings.json"
    if warnings_path.exists():
        try:
            with open(warnings_path, "r", encoding="utf-8") as f:
                saved_warnings = json.load(f)
                if isinstance(saved_warnings, dict):
                    if "thermal" in saved_warnings:
                        warnings_store["thermal"] = saved_warnings["thermal"]
                    if "tdms" in saved_warnings:
                        warnings_store["tdms"] = saved_warnings["tdms"]
                    print(f"加载预警数据: 热成像={len(warnings_store['thermal'])}, TDMS={len(warnings_store['tdms'])}")
        except Exception as e:
            print(f"加载预警数据失败: {str(e)}")

    meta_files = glob.glob(str(Config.METADATA_FOLDER / "*_meta.json"))
    for meta_path in meta_files:
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
                file_id = os.path.basename(meta_path).split("_")[0]
                file_metadata_store[file_id] = metadata
        except Exception as e:
            print(f"加载元数据文件 {meta_path} 失败: {str(e)}")

    thermal_files = glob.glob(str(Config.THERMAL_DATA_FOLDER / "*.json"))
    for file_path in thermal_files:
        if "_temp.json" in file_path:
            continue
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                thermal_data = json.load(f)
                file_id = os.path.basename(file_path).split(".")[0]
                thermal_data_store[file_id] = thermal_data
                
                # 不需要重新恢复预警，因为已经从 warnings.json 加载了
                
        except Exception as e:
            print(f"加载热图数据文件 {file_path} 失败: {str(e)}")

    temp_files = glob.glob(str(Config.THERMAL_DATA_FOLDER / "*_temp.json"))
    for temp_path in temp_files:
        try:
            with open(temp_path, "r", encoding="utf-8") as f:
                temp_data = json.load(f)
                file_id = os.path.basename(temp_path).split("_")[0]
                temperature_data_store[file_id] = temp_data
        except Exception as e:
            print(f"加载温度数据文件 {temp_path} 失败: {str(e)}")

    # 补充缺失的元数据 - 按照app_14.py方式
    for file_id in thermal_data_store:
        if file_id not in file_metadata_store:
            jpg_path = Config.UPLOAD_FOLDER / f"{file_id}.jpg"
            if jpg_path.exists():
                file_time = os.path.getctime(jpg_path)
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(file_time))
                file_name = f"thermal_image_{file_id[:8]}.jpg"
                has_warning = file_id in warnings_store["thermal"]
                file_metadata_store[file_id] = {
                    "name": file_name,
                    "timestamp": timestamp,
                    "path": str(jpg_path),
                    "has_warning": has_warning,
                    "warning_type": "外壁超温" if has_warning else None
                }
                meta_path = Config.METADATA_FOLDER / f"{file_id}_meta.json"
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(file_metadata_store[file_id], f, ensure_ascii=False, indent=2)

    print(f"加载完成: {len(file_metadata_store)} 个文件元数据, {len(thermal_data_store)} 个热图数据, {len(temperature_data_store)} 个温度数据, {len(warnings_store['thermal'])} 个温度预警")

# 创建全局服务实例
thermal_service = ThermalService()