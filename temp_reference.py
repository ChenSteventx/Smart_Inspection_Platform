import os
import re
import base64
import uuid
import subprocess
import tempfile
import json
import time
from io import BytesIO
from math import ceil
import glob
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
import pickle
from urllib.parse import quote

from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from nptdms import TdmsFile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize

import pandas as pd
import cv2

import logging
from browser_manager_2 import browsergap_manager

# 配置上传文件夹路径
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Thermal Data 存储路径
THERMAL_DATA_FOLDER = os.path.join(UPLOAD_FOLDER, "thermal_data")
os.makedirs(THERMAL_DATA_FOLDER, exist_ok=True)

# 文件元数据存储路径
METADATA_FOLDER = os.path.join(UPLOAD_FOLDER, "metadata")
os.makedirs(METADATA_FOLDER, exist_ok=True)

# Excel数据缓存文件夹
EXCEL_CACHE_FOLDER = os.path.join(UPLOAD_FOLDER, "excel_cache")
os.makedirs(EXCEL_CACHE_FOLDER, exist_ok=True)

# DJI IRP 工具路径
DJI_IRP_PATH = r"D:\\ctx\\Documents\\UAV\\temperReader\\dji_thermal_sdk_v1.5_20240507\\sample\\bin\\windows\\release_x64\\dji_irp.exe"

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins=['http://localhost:3000', 'http://localhost:8080'], supports_credentials=True)

# 全局配置
DJI_TARGET_URL = "https://fh.dji.com"
BROWSERGAP_PORT = 8081

# 配置Flask超时
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 300
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB



@app.route('/api/browsergap/start', methods=['POST'])
def start_browsergap_service():
    """启动优化版BrowserGap服务"""
    try:
        data = request.get_json() or {}
        port = data.get('port', BROWSERGAP_PORT)
        target_url = data.get('target_url', DJI_TARGET_URL)
        
        logger.info(f"启动BrowserGap服务请求，端口: {port}, 目标URL: {target_url}")
        
        # 检查服务是否已运行
        status = browsergap_manager.get_service_status()
        if status["status"] == "running":
            return jsonify({
                "success": True,
                "message": "BrowserGap服务已在运行",
                "service_url": status["url"],
                "websocket_url": status["websocket_url"],
                "port": status["port"],
                "performance_mode": status.get("performance_mode", "balanced")
            }), 200
        
        # 启动服务
        success = browsergap_manager.start_browsergap(port, target_url)
        
        if success:
            # 等待服务完全启动
            time.sleep(2)
            final_status = browsergap_manager.get_service_status()
            
            return jsonify({
                "success": True,
                "message": "BrowserGap服务启动成功",
                "service_url": browsergap_manager.base_url,
                "websocket_url": browsergap_manager.websocket_url,
                "port": port,
                "target_url": target_url,
                "performance_mode": final_status.get("performance_mode", "balanced"),
                "clients": final_status.get("clients", 0)
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "BrowserGap服务启动失败",
                "details": "请检查Node.js环境和Chrome浏览器是否正确安装"
            }), 500
            
    except Exception as e:
        logger.error(f"启动BrowserGap服务时发生错误: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"服务启动失败: {str(e)}"
        }), 500

@app.route('/api/browsergap/stop', methods=['POST'])
def stop_browsergap_service():
    """停止BrowserGap服务"""
    try:
        logger.info("停止BrowserGap服务请求")
        
        success = browsergap_manager.stop_browsergap()
        
        if success:
            return jsonify({
                "success": True,
                "message": "BrowserGap服务已停止"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "停止服务失败"
            }), 500
            
    except Exception as e:
        logger.error(f"停止BrowserGap服务时发生错误: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"停止服务失败: {str(e)}"
        }), 500

@app.route('/api/browsergap/status', methods=['GET'])
def get_browsergap_status():
    """获取优化版BrowserGap服务状态"""
    try:
        status = browsergap_manager.get_service_status()
        
        # 添加额外的服务信息
        enhanced_status = {
            **status,
            "server_version": "2.0",
            "optimization_features": [
                "事件节流优化",
                "二进制传输",
                "帧差检测",
                "性能模式切换"
            ]
        }
        
        return jsonify({
            "success": True,
            "status": enhanced_status
        }), 200
        
    except Exception as e:
        logger.error(f"获取服务状态时发生错误: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/browsergap/performance-mode', methods=['POST'])
def set_performance_mode():
    """设置BrowserGap服务性能模式"""
    try:
        data = request.get_json() or {}
        mode = data.get('mode', 'balanced')
        
        logger.info(f"设置性能模式请求: {mode}")
        
        # 检查服务状态
        status = browsergap_manager.get_service_status()
        if status["status"] != "running":
            return jsonify({
                "success": False,
                "error": "BrowserGap服务未运行，请先启动服务"
            }), 400
        
        # 设置性能模式
        result = browsergap_manager.set_performance_mode(mode)
        
        return jsonify(result), 200 if result["success"] else 400
        
    except Exception as e:
        logger.error(f"设置性能模式时发生错误: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/browsergap/performance-mode', methods=['GET'])
def get_performance_mode():
    """获取当前性能模式"""
    try:
        status = browsergap_manager.get_service_status()
        
        return jsonify({
            "success": True,
            "current_mode": status.get("performance_mode", "unknown"),
            "available_modes": ["quality", "balanced", "performance"],
            "mode_descriptions": {
                "quality": "高质量模式 - 最佳图像质量，适合精细操作",
                "balanced": "平衡模式 - 质量与性能兼顾，推荐使用",
                "performance": "高性能模式 - 最快响应速度，适合快速交互"
            }
        }), 200
        
    except Exception as e:
        logger.error(f"获取性能模式时发生错误: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/browsergap/navigate', methods=['POST'])
def navigate_to_url():
    """导航到指定URL"""
    try:
        data = request.get_json() or {}
        target_url = data.get('url', DJI_TARGET_URL)
        wait_for_load = data.get('wait_for_load', True)
        
        logger.info(f"导航请求，目标URL: {target_url}")
        
        # 检查服务状态
        status = browsergap_manager.get_service_status()
        if status["status"] != "running":
            return jsonify({
                "success": False,
                "error": "BrowserGap服务未运行，请先启动服务"
            }), 400
        
        # 执行导航
        result = browsergap_manager.navigate_to_url(target_url)
        
        # 添加额外的导航信息
        if result["success"]:
            result["navigation_timestamp"] = time.time()
            result["service_url"] = status["url"]
            result["websocket_url"] = status["websocket_url"]
        
        return jsonify(result), 200 if result["success"] else 400
        
    except Exception as e:
        logger.error(f"导航时发生错误: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/browsergap/embed-info', methods=['GET'])
def get_embed_info():
    """获取Vue组件嵌入信息"""
    try:
        status = browsergap_manager.get_service_status()
        
        if status["status"] == "running":
            return jsonify({
                "success": True,
                "embed_config": {
                    "websocket_url": status["websocket_url"],
                    "http_api_url": status["url"],
                    "performance_mode": status.get("performance_mode", "balanced"),
                    "supports_binary": True,
                    "optimization_enabled": True
                },
                "vue_component_props": {
                    "serverUrl": status["url"],
                    "websocketUrl": status["websocket_url"],
                    "targetUrl": DJI_TARGET_URL,
                    "autoConnect": True,
                    "enableOptimizations": True
                },
                "connection_info": {
                    "port": status["port"],
                    "clients": status.get("clients", 0),
                    "initialized": status.get("initialized", False)
                }
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "BrowserGap服务未运行",
                "status": status["status"]
            }), 400
            
    except Exception as e:
        logger.error(f"获取嵌入信息时发生错误: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/browsergap/prerequisites', methods=['GET'])
def check_prerequisites():
    """检查BrowserGap服务运行前置条件"""
    try:
        logger.info("检查系统前置条件")
        
        prereq_result = browsergap_manager.check_prerequisites()
        
        return jsonify({
            "success": prereq_result["success"],
            "prerequisites": prereq_result,
            "recommendations": [
                "确保Node.js版本 >= 14.0.0",
                "确保Google Chrome浏览器已安装",
                "确保npm依赖包已正确安装",
                "确保系统有足够的内存和CPU资源"
            ] if not prereq_result["success"] else []
        }), 200 if prereq_result["success"] else 400
        
    except Exception as e:
        logger.error(f"检查前置条件时发生错误: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        "success": True,
        "message": "Flask服务运行正常",
        "timestamp": time.time()
    }), 200

# 存储温度数据的简单字典
temperature_data_store = {}

# 存储 Thermal Data 的字典
thermal_data_store = {}

# 存储文件元数据的字典
file_metadata_store = {}

# 存储预警信息的字典
warnings_store = {
    "thermal": {},
    "tdms": {}
}

# Excel数据缓存字典
excel_data_cache = {}

# 任务状态跟踪字典 - 增强版本
task_status = {}

# 线程池执行器
executor = ThreadPoolExecutor(max_workers=4)

# TDMS文件元数据存储 - 增强版本
tdms_file_metadata = {}

# ========================= TDMS 相关路由 =========================

@app.route("/api/upload-tdms", methods=["POST"])
def upload_tdms():
    """
    上传 TDMS 文件的接口，将文件保存到指定目录，并返回文件ID和文件信息
    """
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "未上传文件"}), 400

    file_id = str(uuid.uuid4())
    file_name = f"{file_id}.tdms"
    file_path = os.path.join(UPLOAD_FOLDER, file_name)
    file.save(file_path)

    # 获取文件大小和基本信息
    file_size = os.path.getsize(file_path)
    upload_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    original_filename = file.filename or f"tdms_file_{file_id[:8]}.tdms"
    
    # 存储文件元数据 - 增强版本，包含原始文件名
    tdms_file_metadata[file_id] = {
        "original_name": original_filename,
        "file_path": file_path,
        "file_size": file_size,
        "upload_time": upload_time,
        "status": "uploaded",
        "display_name": original_filename  # 用于显示的文件名
    }

    return jsonify({
        "fileId": file_id,
        "message": "TDMS 文件上传并保存成功",
        "fileSize": file_size,
        "fileName": original_filename,
        "uploadTime": upload_time
    }), 200


# 在后端Flask应用中添加以下新的API路由

@app.route("/api/get-latest-tdms-image", methods=["GET"])
def get_latest_tdms_image():
    """
    获取最新的已处理TDMS图像数据，用于导航界面预览
    """
    try:
        # 获取所有已处理且有图像数据的TDMS文件
        processed_files = []
        
        for file_id, metadata in tdms_file_metadata.items():
            if metadata.get("status") in ["visualization_completed", "excel_completed"]:
                tdms_name = f"{file_id}.tdms"
                tdms_path = os.path.join(UPLOAD_FOLDER, tdms_name)
                if os.path.exists(tdms_path):
                    processed_files.append({
                        "file_id": file_id,
                        "metadata": metadata,
                        "last_modified": os.path.getmtime(tdms_path)
                    })
        
        if not processed_files:
            return jsonify({
                "success": False,
                "message": "暂无已处理的TDMS文件",
                "has_image": False
            }), 200
        
        # 按最后修改时间排序，获取最新的文件
        processed_files.sort(key=lambda x: x["last_modified"], reverse=True)
        latest_file = processed_files[0]
        latest_file_id = latest_file["file_id"]
        
        # 尝试重新处理以获取图像（如果图像不存在）
        try:
            tdms_name = f"{latest_file_id}.tdms"
            tdms_path = os.path.join(UPLOAD_FOLDER, tdms_name)
            
            # 重新处理TDMS文件生成图像
            tdms_file = TdmsFile.read(tdms_path)
            
            pattern = re.compile(r"Row-(\d+)-Col-(\d+)")
            channels_by_col = {0: [], 1: [], 2: [], 3: []}

            # 按照组名匹配，并将Data通道按列存储
            for group in tdms_file.groups():
                gname = group.name
                match = pattern.match(gname)
                if match:
                    x = int(match.group(1))
                    y = int(match.group(2))
                    if y in channels_by_col:
                        for ch in group.channels():
                            if ch.name == "Data":
                                channels_by_col[y].append((x, ch))

            # 判断通道数量和预警状态
            active_channels = 0
            valid_channels = []
            has_warning = False
            warning_positions = []
            standard_thickness = 1.0
            warning_threshold = 0.8

            for y in channels_by_col:
                if not channels_by_col[y]:
                    continue
                    
                valid_data_points = 0
                for x, ch in sorted(channels_by_col[y], key=lambda item: item[0]):
                    data = ch.data
                    if len(data) >= 404:
                        thickness_val = data[400] / 100.0
                        if thickness_val > 0.01:
                            valid_data_points += 1
                        
                        # 检查预警
                        if thickness_val < warning_threshold and thickness_val > 0.01:
                            has_warning = True
                            warning_positions.append({
                                "channel": y,
                                "position": x,
                                "thickness": thickness_val
                            })
                
                if valid_data_points > 0:
                    active_channels += 1
                    valid_channels.append(y)

            # 对每列内的通道按x值排序
            for y in channels_by_col:
                channels_by_col[y].sort(key=lambda item: item[0])

            # 生成图像
            norm = Normalize(vmin=0.8, vmax=1.0)
            cmap = plt.cm.RdYlGn
            fig, ax = plt.subplots(figsize=(8, 5))
            channel_positions = {col_i: idx for idx, col_i in enumerate(channels_by_col.keys())}

            for y, data_list in channels_by_col.items():
                prev_x_val = 0.0
                y_pos = channel_positions[y]
                for x, ch in data_list:
                    data = ch.data
                    if len(data) >= 404:
                        thickness_val = data[400] / 100.0
                        x_val = data[402]
                        color = cmap(norm(thickness_val))

                        rect_width = x_val - prev_x_val
                        ax.add_patch(
                            plt.Rectangle(
                                (prev_x_val, y_pos - 0.4),
                                rect_width,
                                0.8,
                                facecolor=color,
                                edgecolor='none'
                            )
                        )
                        prev_x_val = x_val

            # 设置图表样式
            channel_labels = [f"Channel {y}" for y in channel_positions.keys()]
            ax.set_yticks(list(channel_positions.values()))
            ax.set_yticklabels(channel_labels)
            ax.set_xlabel("")
            ax.set_ylabel("")
            ax.set_title("")
            ax.relim()
            ax.autoscale_view()

            # 添加颜色条
            sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
            sm.set_array([])
            cbar = plt.colorbar(sm, ax=ax)
            cbar.set_label("壁厚比例")

            plt.tight_layout()

            # 转换为base64
            png_io = BytesIO()
            plt.savefig(png_io, format='png', dpi=120, bbox_inches='tight')
            png_io.seek(0)
            png_base64 = base64.b64encode(png_io.getvalue()).decode('utf-8')
            plt.close(fig)
            
            # 构建返回数据
            file_metadata = latest_file["metadata"]
            
            return jsonify({
                "success": True,
                "has_image": True,
                "file_id": latest_file_id,
                "file_name": file_metadata.get("original_name", f"文件_{latest_file_id[:8]}"),
                "upload_time": file_metadata.get("upload_time", ""),
                "plot_base64": png_base64,
                "has_warning": has_warning,
                "warning_type": "内壁破损" if has_warning else None,
                "active_channels": active_channels,
                "total_files": len(processed_files),
                "preview_info": {
                    "channels": active_channels,
                    "warning_count": len(warning_positions)
                }
            }), 200
            
        except Exception as e:
            logger.error(f"重新处理TDMS文件失败: {str(e)}")
            # 如果处理失败，返回文件信息但没有图像
            file_metadata = latest_file["metadata"]
            return jsonify({
                "success": True,
                "has_image": False,
                "file_id": latest_file_id,
                "file_name": file_metadata.get("original_name", f"文件_{latest_file_id[:8]}"),
                "upload_time": file_metadata.get("upload_time", ""),
                "error": f"图像生成失败: {str(e)}",
                "total_files": len(processed_files)
            }), 200
            
    except Exception as e:
        logger.error(f"获取最新TDMS图像时发生错误: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取图像失败: {str(e)}",
            "has_image": False
        }), 500

@app.route("/api/get-tdms-summary", methods=["GET"])
def get_tdms_summary():
    """
    获取TDMS文件处理概要信息，用于导航界面显示统计数据
    """
    try:
        total_files = len(tdms_file_metadata)
        processed_files = 0
        files_with_warnings = 0
        
        for file_id, metadata in tdms_file_metadata.items():
            if metadata.get("status") in ["visualization_completed", "excel_completed"]:
                processed_files += 1
            
            if file_id in warnings_store["tdms"]:
                files_with_warnings += 1
        
        return jsonify({
            "success": True,
            "summary": {
                "total_files": total_files,
                "processed_files": processed_files,
                "pending_files": total_files - processed_files,
                "files_with_warnings": files_with_warnings,
                "processing_rate": round((processed_files / total_files * 100) if total_files > 0 else 0, 1)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"获取TDMS概要信息时发生错误: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/process-tdms", methods=["POST"])
def process_tdms():
    """
    处理 TDMS 文件，将数据转换为图像并返回图像的base64编码
    同时检测壁厚是否小于标准值的80%，如果是则生成预警信息
    增强了通道数量的识别准确性
    """
    file_id = request.form.get("fileId") or request.json.get("fileId")
    if not file_id:
        return jsonify({"error": "未提供 fileId"}), 400

    tdms_name = f"{file_id}.tdms"
    tdms_path = os.path.join(UPLOAD_FOLDER, tdms_name)
    if not os.path.exists(tdms_path):
        return jsonify({"error": "未找到对应的 TDMS 文件"}), 404

    try:
        # 更新处理状态
        if file_id in tdms_file_metadata:
            tdms_file_metadata[file_id]["status"] = "processing_visualization"
            
        tdms_file = TdmsFile.read(tdms_path)
    except Exception as e:
        return jsonify({"error": f"读取TDMS文件失败: {str(e)}"}), 500

    pattern = re.compile(r"Row-(\d+)-Col-(\d+)")
    channels_by_col = {0: [], 1: [], 2: [], 3: []}

    # 按照组名匹配，并将Data通道按列存储
    for group in tdms_file.groups():
        gname = group.name
        match = pattern.match(gname)
        if match:
            x = int(match.group(1))
            y = int(match.group(2))
            if y in channels_by_col:
                for ch in group.channels():
                    if ch.name == "Data":
                        channels_by_col[y].append((x, ch))

    # 判断通道数量 - 改进的通道识别逻辑
    active_channels = 0
    valid_channels = []
    channel_thickness_data = {}

    for y in channels_by_col:
        if not channels_by_col[y]:
            continue
            
        # 计算该通道的壁厚统计数据
        thickness_values = []
        valid_data_points = 0
        
        for x, ch in sorted(channels_by_col[y], key=lambda item: item[0]):
            data = ch.data
            if len(data) >= 404:
                thickness_val = data[400] / 100.0
                thickness_values.append(thickness_val)
                
                if thickness_val > 0.01:
                    valid_data_points += 1
        
        avg_thickness = sum(thickness_values) / len(thickness_values) if thickness_values else 0
        max_thickness = max(thickness_values) if thickness_values else 0
        
        if valid_data_points > 0:
            active_channels += 1
            valid_channels.append(y)
            channel_thickness_data[y] = {
                "avg": avg_thickness,
                "max": max_thickness,
                "valid_points": valid_data_points,
                "total_points": len(thickness_values)
            }
    
    # 区分3通道和4通道的情况
    is_three_channel_mode = False
    inactive_channel = None
    
    if active_channels == 3 and len(channels_by_col) == 4:
        is_three_channel_mode = True
        for y in channels_by_col:
            if y not in valid_channels:
                inactive_channel = y
                break
    
    # 壁厚检测和预警
    has_warning = False
    warning_positions = []
    standard_thickness = 1.0
    warning_threshold = 0.8
    
    for y in valid_channels:
        for x, ch in channels_by_col[y]:
            data = ch.data
            if len(data) >= 404:
                thickness_val = data[400] / 100.0
                if thickness_val < warning_threshold and thickness_val > 0.01:
                    has_warning = True
                    warning_positions.append({
                        "channel": y,
                        "position": x,
                        "thickness": thickness_val,
                        "percentage": thickness_val * 100
                    })

    # 保存预警信息
    if has_warning:
        warnings_store["tdms"][file_id] = {
            "type": "内壁破损",
            "active_channels": active_channels,
            "is_three_channel_mode": is_three_channel_mode,
            "inactive_channel": inactive_channel,
            "positions": warning_positions
        }
    else:
        warnings_store["tdms"].pop(file_id, None)

    # 对每列内的通道按x值排序
    for y in channels_by_col:
        channels_by_col[y].sort(key=lambda item: item[0])

    # 可视化部分 - 绘制图形
    try:
        norm = Normalize(vmin=0.8, vmax=1.0)
        cmap = plt.cm.RdYlGn
        fig, ax = plt.subplots(figsize=(10, 6))
        channel_positions = {col_i: idx for idx, col_i in enumerate(channels_by_col.keys())}

        for y, data_list in channels_by_col.items():
            prev_x_val = 0.0
            y_pos = channel_positions[y]
            for x, ch in data_list:
                data = ch.data
                if len(data) >= 404:
                    thickness_val = data[400] / 100.0
                    x_val = data[402]
                    color = cmap(norm(thickness_val))

                    rect_width = x_val - prev_x_val
                    ax.add_patch(
                        plt.Rectangle(
                            (prev_x_val, y_pos - 0.4),
                            rect_width,
                            0.8,
                            facecolor=color,
                            edgecolor='none'
                        )
                    )
                    prev_x_val = x_val

        channel_labels = []
        for y in channel_positions.keys():
            if is_three_channel_mode and y == inactive_channel:
                channel_labels.append(f"Channel {y} (无效)")
            else:
                channel_labels.append(f"Channel {y}")
                
        ax.set_yticks(list(channel_positions.values()))
        ax.set_yticklabels(channel_labels)
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.set_title("")
        ax.relim()
        ax.autoscale_view()

        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax)
        cbar.set_label("壁厚比例")

        plt.tight_layout()

        png_io = BytesIO()
        plt.savefig(png_io, format='png', dpi=150, bbox_inches='tight')
        png_io.seek(0)
        png_base64 = base64.b64encode(png_io.getvalue()).decode('utf-8')
        plt.close(fig)
        
        # 更新处理状态
        if file_id in tdms_file_metadata:
            tdms_file_metadata[file_id]["status"] = "visualization_completed"
            
    except Exception as e:
        return jsonify({"error": f"生成图像失败: {str(e)}"}), 500

    return jsonify({
        "message": "TDMS 处理完成",
        "plot_base64": png_base64,
        "has_warning": has_warning,
        "warning_type": "内壁破损" if has_warning else None,
        "active_channels": active_channels,
        "is_three_channel_mode": is_three_channel_mode,
        "channel_data": channel_thickness_data,
        "warning_positions": warning_positions if has_warning else []
    }), 200

def process_tdms_to_excel_background(file_id):
    """
    后台处理TDMS转Excel的任务 - 修正ExcelWriter兼容性问题，增加详细进度跟踪
    """
    try:
        task_status[file_id] = {
            "status": "processing",
            "progress": 0,
            "message": "开始处理TDMS文件",
            "start_time": time.time(),
            "current_step": "initializing",
            "estimated_remaining": None,
            "processing_speed": 0,
            "file_name": tdms_file_metadata.get(file_id, {}).get("original_name", f"文件_{file_id[:8]}")
        }
        
        # 更新文件元数据状态
        if file_id in tdms_file_metadata:
            tdms_file_metadata[file_id]["status"] = "converting_to_excel"
        
        tdms_name = f"{file_id}.tdms"
        tdms_path = os.path.join(UPLOAD_FOLDER, tdms_name)
        
        if not os.path.exists(tdms_path):
            task_status[file_id] = {
                "status": "error",
                "message": "未找到TDMS文件",
                "end_time": time.time(),
                "file_name": tdms_file_metadata.get(file_id, {}).get("original_name", f"文件_{file_id[:8]}")
            }
            return
        
        # 更新进度
        task_status[file_id]["progress"] = 5
        task_status[file_id]["message"] = "读取TDMS文件中"
        task_status[file_id]["current_step"] = "reading_file"
        
        # 读取TDMS文件
        tdms_file = TdmsFile.read(tdms_path)
        
        task_status[file_id]["progress"] = 15
        task_status[file_id]["message"] = "分析文件结构中"
        task_status[file_id]["current_step"] = "analyzing_structure"
        
        # 估算总数据量
        total_data_points = 0
        for group in tdms_file.groups():
            for ch in group.channels():
                total_data_points += len(ch.data)
        
        task_status[file_id]["progress"] = 25
        task_status[file_id]["message"] = f"开始转换数据（共 {total_data_points:,} 个数据点）"
        task_status[file_id]["current_step"] = "converting_data"
        
        # 收集所有数据
        rows = []
        processed_points = 0
        last_update_time = time.time()
        start_processing_time = time.time()
        
        for group in tdms_file.groups():
            group_name = group.name
            for ch in group.channels():
                channel_name = ch.name
                channel_data = ch.data
                
                for i, val in enumerate(channel_data):
                    rows.append({
                        "GroupName": group_name,
                        "ChannelName": channel_name,
                        "Index": i,
                        "Value": val
                    })
                    processed_points += 1
                    
                    # 每10000个数据点更新一次进度
                    if processed_points % 10000 == 0:
                        current_time = time.time()
                        elapsed_time = current_time - start_processing_time
                        
                        if elapsed_time > 0:
                            processing_speed = processed_points / elapsed_time
                            remaining_points = total_data_points - processed_points
                            estimated_remaining = remaining_points / processing_speed if processing_speed > 0 else None
                        else:
                            processing_speed = 0
                            estimated_remaining = None
                        
                        progress = 25 + min(int((processed_points / max(total_data_points, 1)) * 50), 50)
                        task_status[file_id].update({
                            "progress": progress,
                            "message": f"已处理 {processed_points:,} / {total_data_points:,} 个数据点",
                            "processing_speed": processing_speed,
                            "estimated_remaining": estimated_remaining
                        })
                        last_update_time = current_time
        
        task_status[file_id]["progress"] = 80
        task_status[file_id]["message"] = "正在生成Excel文件"
        task_status[file_id]["current_step"] = "generating_excel"
        
        # 创建DataFrame
        df = pd.DataFrame(rows)
        
        task_status[file_id]["progress"] = 90
        task_status[file_id]["message"] = "正在写入Excel文件"
        task_status[file_id]["current_step"] = "writing_excel"
        
        # 保存Excel文件
        xlsx_name = f"{file_id}.xlsx"
        xlsx_path = os.path.join(UPLOAD_FOLDER, xlsx_name)
        
        # 使用兼容性最好的方式保存Excel文件
        try:
            # 首先尝试使用基本的to_excel方法
            df.to_excel(xlsx_path, index=False, engine='openpyxl')
        except Exception as excel_error:
            print(f"使用to_excel方法失败: {excel_error}")
            try:
                # 如果失败，尝试使用ExcelWriter但不带额外参数
                with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='TDMS_Data', index=False)
            except Exception as writer_error:
                print(f"使用ExcelWriter失败: {writer_error}")
                # 最后尝试使用xlsxwriter引擎
                df.to_excel(xlsx_path, index=False, engine='xlsxwriter')
        
        task_status[file_id]["progress"] = 95
        task_status[file_id]["message"] = "创建数据索引"
        task_status[file_id]["current_step"] = "creating_index"
        
        # 创建缓存索引
        cache_index_path = os.path.join(EXCEL_CACHE_FOLDER, f"{file_id}_index.pkl")
        cache_index = {
            "total_rows": len(rows),
            "file_path": xlsx_path,
            "created_time": time.time(),
            "columns": ["GroupName", "ChannelName", "Index", "Value"]
        }
        
        with open(cache_index_path, 'wb') as f:
            pickle.dump(cache_index, f)
        
        # 缓存到内存
        excel_data_cache[file_id] = cache_index
        
        # 更新文件元数据状态
        if file_id in tdms_file_metadata:
            tdms_file_metadata[file_id]["status"] = "excel_completed"
        
        task_status[file_id] = {
            "status": "completed",
            "progress": 100,
            "message": "Excel文件生成完成",
            "end_time": time.time(),
            "total_rows": len(rows),
            "current_step": "completed",
            "total_processing_time": time.time() - task_status[file_id]["start_time"],
            "file_name": tdms_file_metadata.get(file_id, {}).get("original_name", f"文件_{file_id[:8]}")
        }
        
    except Exception as e:
        print(f"处理TDMS转Excel时发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # 更新文件元数据状态
        if file_id in tdms_file_metadata:
            tdms_file_metadata[file_id]["status"] = "error"
        
        task_status[file_id] = {
            "status": "error",
            "message": f"处理失败: {str(e)}",
            "end_time": time.time(),
            "current_step": "error",
            "file_name": tdms_file_metadata.get(file_id, {}).get("original_name", f"文件_{file_id[:8]}")
        }

@app.route("/api/process-tdms-to-excel", methods=["POST"])
def process_tdms_to_excel():
    """
    异步处理TDMS文件转换为Excel文件
    """
    data = request.get_json() or {}
    file_id = data.get("fileId")
    
    if not file_id:
        return jsonify({"error": "未提供 fileId"}), 400

    tdms_name = f"{file_id}.tdms"
    tdms_path = os.path.join(UPLOAD_FOLDER, tdms_name)
    if not os.path.exists(tdms_path):
        return jsonify({"error": "未找到 TDMS 文件"}), 404

    # 检查是否已经在处理中
    if file_id in task_status and task_status[file_id].get("status") == "processing":
        return jsonify({
            "success": True,
            "message": "任务正在处理中",
            "status": task_status[file_id]
        }), 200

    # 检查是否已经完成
    xlsx_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.xlsx")
    if os.path.exists(xlsx_path) and file_id in excel_data_cache:
        return jsonify({
            "success": True,
            "message": "Excel文件已存在",
            "status": {"status": "completed", "progress": 100}
        }), 200

    # 启动后台任务
    executor.submit(process_tdms_to_excel_background, file_id)
    
    return jsonify({
        "success": True,
        "message": "Excel转换任务已启动",
        "status": {"status": "processing", "progress": 0}
    }), 200

@app.route("/api/get-task-status/<file_id>", methods=["GET"])
def get_task_status(file_id):
    """
    获取任务处理状态 - 增强版本，包含文件名信息
    """
    status = task_status.get(file_id, {"status": "not_found", "message": "任务不存在"})
    
    # 添加文件元数据信息
    if file_id in tdms_file_metadata:
        file_metadata = tdms_file_metadata[file_id]
        status.update({
            "file_name": file_metadata.get("original_name"),
            "file_size": file_metadata.get("file_size"),
            "upload_time": file_metadata.get("upload_time")
        })
    
    return jsonify(status), 200

@app.route("/api/get-all-task-status", methods=["GET"])
def get_all_task_status():
    """
    获取所有正在进行的任务状态 - 增强版本
    """
    active_tasks = {}
    for file_id, status in task_status.items():
        if status.get("status") == "processing":
            # 添加文件元数据
            if file_id in tdms_file_metadata:
                file_metadata = tdms_file_metadata[file_id]
                status.update({
                    "file_name": file_metadata.get("original_name"),
                    "file_size": file_metadata.get("file_size")
                })
            active_tasks[file_id] = status
    
    return jsonify(active_tasks), 200

@app.route("/api/download-excel/<file_id>", methods=["GET"])
def download_excel(file_id):
    """
    下载生成的 Excel 文件 - 修复文件名问题
    """
    xlsx_name = f"{file_id}.xlsx"
    xlsx_path = os.path.join(UPLOAD_FOLDER, xlsx_name)
    if not os.path.exists(xlsx_path):
        return jsonify({"error": "未找到 Excel 文件"}), 404

    # 获取原始文件名并处理
    original_name = "tdms_data"
    if file_id in tdms_file_metadata:
        original_name = tdms_file_metadata[file_id].get("original_name", "tdms_data")
        if original_name.lower().endswith('.tdms'):
            original_name = original_name[:-5]  # 移除.tdms扩展名
        elif original_name.lower().endswith('.xlsx'):
            original_name = original_name[:-5]  # 移除.xlsx扩展名，后面会重新添加
    
    # 确保文件名安全，移除特殊字符
    safe_filename = "".join(c for c in original_name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
    if not safe_filename:
        safe_filename = f"tdms_data_{file_id[:8]}"
    
    download_filename = f"{safe_filename}.xlsx"
    
    try:
        # 使用 Response 对象来确保正确的文件名编码
        def generate():
            with open(xlsx_path, 'rb') as f:
                while True:
                    data = f.read(4096)
                    if not data:
                        break
                    yield data
        
        # 使用 URL 编码处理中文文件名
        encoded_filename = quote(download_filename.encode('utf-8'))
        
        response = Response(
            generate(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={
                'Content-Disposition': f'attachment; filename="{download_filename}"; filename*=UTF-8\'\'{encoded_filename}',
                'Content-Length': str(os.path.getsize(xlsx_path))
            }
        )
        
        return response
        
    except Exception as e:
        print(f"下载文件时出错: {str(e)}")
        # 如果出现错误，回退到原来的方法
        return send_from_directory(
            UPLOAD_FOLDER,
            xlsx_name,
            as_attachment=True,
            download_name=download_filename
        )

@app.route("/api/download-tdms/<file_id>", methods=["GET"])
def download_tdms(file_id):
    """
    下载 TDMS 文件 - 优化文件名处理
    """
    tdms_name = f"{file_id}.tdms"
    tdms_path = os.path.join(UPLOAD_FOLDER, tdms_name)
    if not os.path.exists(tdms_path):
        return jsonify({"error": "未找到文件"}), 404

    # 获取原始文件名
    original_name = f"tdms_file_{file_id[:8]}.tdms"
    if file_id in tdms_file_metadata:
        original_name = tdms_file_metadata[file_id].get("original_name", original_name)
    
    # 确保文件名安全
    safe_filename = "".join(c for c in original_name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
    if not safe_filename:
        safe_filename = f"tdms_file_{file_id[:8]}.tdms"

    try:
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
                'Content-Length': str(os.path.getsize(tdms_path))
            }
        )
        
        return response
        
    except Exception as e:
        print(f"下载TDMS文件时出错: {str(e)}")
        # 如果出现错误，回退到原来的方法
        return send_from_directory(
            UPLOAD_FOLDER,
            tdms_name,
            as_attachment=True,
            download_name=safe_filename
        )

@app.route("/api/get-excel-data/<file_id>", methods=["GET"])
def get_excel_data(file_id):
    """
    获取 Excel 数据，支持分页显示，优化了大文件读取性能
    """
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 50, type=int)

    # 限制页面大小，防止内存溢出
    page_size = min(page_size, 1000)
    
    try:
        # 首先检查缓存
        if file_id not in excel_data_cache:
            # 尝试从磁盘加载缓存索引
            cache_index_path = os.path.join(EXCEL_CACHE_FOLDER, f"{file_id}_index.pkl")
            if os.path.exists(cache_index_path):
                with open(cache_index_path, 'rb') as f:
                    excel_data_cache[file_id] = pickle.load(f)
            else:
                # 创建新的缓存索引
                xlsx_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.xlsx")
                if not os.path.exists(xlsx_path):
                    return jsonify({"error": "未找到 Excel 文件"}), 404
                
                # 快速读取文件信息
                df_info = pd.read_excel(xlsx_path, nrows=0)  # 只读取列名
                
                # 使用chunk读取计算总行数
                total_rows = 0
                chunk_iter = pd.read_excel(xlsx_path, chunksize=10000)
                for chunk in chunk_iter:
                    total_rows += len(chunk)
                
                cache_index = {
                    "total_rows": total_rows,
                    "file_path": xlsx_path,
                    "created_time": time.time(),
                    "columns": df_info.columns.tolist()
                }
                
                excel_data_cache[file_id] = cache_index
                
                # 保存缓存索引
                with open(cache_index_path, 'wb') as f:
                    pickle.dump(cache_index, f)

        cache_info = excel_data_cache[file_id]
        total_count = cache_info["total_rows"]
        xlsx_path = cache_info["file_path"]
        
        if not os.path.exists(xlsx_path):
            return jsonify({"error": "Excel文件不存在"}), 404

        # 计算分页参数
        total_pages = ceil(total_count / page_size) if page_size else 1
        
        if page < 1:
            page = 1
        if page > total_pages:
            page = total_pages if total_pages > 0 else 1

        start_idx = (page - 1) * page_size
        
        # 使用skiprows和nrows进行高效分页读取
        try:
            if start_idx == 0:
                df_page = pd.read_excel(xlsx_path, nrows=page_size)
            else:
                df_page = pd.read_excel(xlsx_path, skiprows=range(1, start_idx + 1), nrows=page_size)
        except Exception as e:
            # 如果读取失败，尝试使用chunk方式
            chunk_iter = pd.read_excel(xlsx_path, chunksize=page_size)
            current_page = 1
            for chunk in chunk_iter:
                if current_page == page:
                    df_page = chunk
                    break
                current_page += 1
            else:
                df_page = pd.DataFrame()

        # 确保数值类型正确
        if not df_page.empty:
            # 处理可能的数据类型问题
            for col in df_page.columns:
                if df_page[col].dtype == 'object':
                    try:
                        df_page[col] = pd.to_numeric(df_page[col], errors='ignore')
                    except:
                        pass

        data_as_dict = df_page.to_dict(orient="records")

        return jsonify({
            "data": data_as_dict,
            "total": total_count,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size,
            "file_id": file_id
        }), 200
        
    except Exception as e:
        print(f"读取Excel数据时出错: {str(e)}")
        return jsonify({"error": f"读取Excel数据失败: {str(e)}"}), 500

# ========================= Execute Command 路由 =========================

@app.route("/api/execute-command", methods=["POST"])
def execute_command():
    """
    处理前端发送的命令请求
    """
    data = request.get_json()
    if not data or 'command' not in data:
        return jsonify({"error": "未提供命令内容"}), 400
    
    file_content = data['command']
    try:
        tmp_txt_path = r"D:\\adap-server\\tmp.txt"
        with open(tmp_txt_path, "w", encoding="utf-8") as f:
            f.write(file_content)

        target_directory = r"D:\\adap-server\\adap-yst\\"
        for filename in os.listdir(target_directory):
            file_path = os.path.join(target_directory, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"删除 {file_path} 时出错: {e}")
                return jsonify({"error": f"删除 {file_path} 时出错: {e}"}), 500

        cmd = "abq6131 cae noGui=server-abap.py"
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300)
        if result.returncode != 0:
            return jsonify({"error": "执行 abq6131 脚本失败", "details": result.stderr}), 500

        output_img_path = r"D:\\adap-server\\adap-yst\\assembly-viewport.png"
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

# ========================= Thermal Image 相关路由 =========================

@app.route("/api/list-thermal-files", methods=["GET"])
def list_thermal_files():
    """
    列出所有已上传的热成像文件及其相关信息
    """
    try:
        file_list = []

        if file_metadata_store:
            for file_id, metadata in file_metadata_store.items():
                jpg_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.jpg")
                if os.path.exists(jpg_path):
                    has_warning = file_id in warnings_store["thermal"]
                    file_list.append({
                        "fileId": file_id,
                        "name": metadata.get("name", f"thermal_image_{file_id[:8]}.jpg"),
                        "timestamp": metadata.get("timestamp", ""),
                        "uploading": False,
                        "has_warning": has_warning,
                        "warning_type": "外壁超温" if has_warning else None
                    })
        else:
            jpg_files = glob.glob(os.path.join(UPLOAD_FOLDER, "*.jpg"))
            for jpg_path in jpg_files:
                file_id = os.path.basename(jpg_path).split(".")[0]
                json_path = os.path.join(THERMAL_DATA_FOLDER, f"{file_id}.json")
                if os.path.exists(json_path):
                    file_time = os.path.getctime(jpg_path)
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(file_time))
                    file_name = f"thermal_image_{file_id[:8]}.jpg"
                    has_warning = file_id in warnings_store["thermal"]
                    file_list.append({
                        "fileId": file_id,
                        "name": file_name,
                        "timestamp": timestamp,
                        "uploading": False,
                        "has_warning": has_warning,
                        "warning_type": "外壁超温" if has_warning else None
                    })
                    file_metadata_store[file_id] = {
                        "name": file_name,
                        "timestamp": timestamp,
                        "path": jpg_path
                    }

        file_list.sort(key=lambda x: x["timestamp"], reverse=True)
        return jsonify({
            "success": True,
            "files": file_list
        }), 200
    except Exception as e:
        print(f"列出热成像文件时出错: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"列出文件失败: {str(e)}"
        }), 500

@app.route("/api/upload-thermal-image", methods=["POST"])
def upload_thermal_image():
    """
    上传热成像图片的接口，并调用 DJI IRP 工具处理图片，提取温度数据
    同时检测温度是否超过50摄氏度，如果是则生成预警信息
    """
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "未上传文件"}), 400

    file_id = str(uuid.uuid4())
    jpg_filename = f"{file_id}.jpg"
    jpg_path = os.path.join(UPLOAD_FOLDER, jpg_filename)
    file.save(jpg_path)

    original_filename = file.filename
    upload_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    try:
        with open(jpg_path, "rb") as image_file:
            original_image_bytes = image_file.read()
            original_image_base64 = base64.b64encode(original_image_bytes).decode('utf-8')
    except Exception as e:
        print(f"读取原始图片错误: {str(e)}")
        return jsonify({"error": "读取上传图片失败"}), 500

    raw_path = process_with_dji_irp(jpg_path)
    if not raw_path or not os.path.exists(raw_path):
        return jsonify({"error": "处理热成像图片失败"}), 500

    temperature_matrix = extract_temperature_from_raw(raw_path)
    os.remove(raw_path)

    if temperature_matrix is None:
        return jsonify({"error": "提取温度数据失败"}), 500

    highest_temp_info = find_highest_temperature_point(temperature_matrix)
    
    has_warning = highest_temp_info["highest_temp"] > 50.0
    warning_message = None
    
    if has_warning:
        warning_message = "外壁超温"
        warnings_store["thermal"][file_id] = {
            "type": warning_message,
            "temperature": highest_temp_info["highest_temp"],
            "threshold": 50.0,
            "position": highest_temp_info["highest_point"]
        }
    else:
        warnings_store["thermal"].pop(file_id, None)

    try:
        image = cv2.imread(jpg_path)
        if image is None:
            return jsonify({"error": "读取上传图片进行标记失败"}), 500
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        marked_image_base64 = generate_marked_image(image, highest_temp_info)
    except Exception as e:
        print(f"生成标记图片错误: {str(e)}")
        return jsonify({"error": "生成标记图片失败"}), 500

    temperature_data_store[file_id] = temperature_matrix.tolist()

    thermal_data = {
        "original_plot_base64": original_image_base64,
        "plot_base64": marked_image_base64,
        "highest_temp_info": highest_temp_info,
        "has_warning": has_warning,
        "warning_type": warning_message
    }
    thermal_data_store[file_id] = thermal_data

    thermal_data_path = os.path.join(THERMAL_DATA_FOLDER, f"{file_id}.json")
    with open(thermal_data_path, "w") as f:
        json.dump(thermal_data, f)

    temperature_data_path = os.path.join(THERMAL_DATA_FOLDER, f"{file_id}_temp.json")
    with open(temperature_data_path, "w") as f:
        json.dump(temperature_matrix.tolist(), f)

    file_metadata = {
        "name": original_filename or f"thermal_image_{file_id[:8]}.jpg",
        "timestamp": upload_time,
        "path": jpg_path,
        "has_warning": has_warning,
        "warning_type": warning_message
    }
    file_metadata_store[file_id] = file_metadata

    metadata_path = os.path.join(METADATA_FOLDER, f"{file_id}_meta.json")
    with open(metadata_path, "w") as f:
        json.dump(file_metadata, f)

    print(f"已上传热成像图片 {file_id}, original_plot_base64 长度: {len(original_image_base64)}")

    return jsonify({
        "fileId": file_id,
        "message": "热成像图片处理成功",
        "original_plot_base64": original_image_base64,
        "plot_base64": marked_image_base64,
        "highest_temp_info": highest_temp_info,
        "has_warning": has_warning,
        "warning_type": warning_message
    }), 200

@app.route("/api/get-temperature/<file_id>", methods=["GET"])
def get_temperature(file_id):
    """
    获取指定热成像图片的温度数据，根据前端传入的 x 和 y 坐标返回对应温度值
    """
    try:
        x = request.args.get('x', type=int)
        y = request.args.get('y', type=int)
        if x is None or y is None:
            return jsonify({"error": "缺少 x 或 y 参数"}), 400

        temperature_matrix = temperature_data_store.get(file_id)
        if not temperature_matrix:
            temperature_path = os.path.join(THERMAL_DATA_FOLDER, f"{file_id}_temp.json")
            if os.path.exists(temperature_path):
                with open(temperature_path, "r") as f:
                    temperature_matrix = json.load(f)
                temperature_data_store[file_id] = temperature_matrix
            else:
                return jsonify({"error": "未找到温度数据"}), 404

        width = 640
        height = 512
        x = max(0, min(x, width - 1))
        y = max(0, min(y, height - 1))

        print(f"获取温度请求: 原始坐标 ({request.args.get('x')}, {request.args.get('y')}), 修正后坐标 ({x}, {y})")
        temperature = temperature_matrix[y][x]

        return jsonify({
            "x": x,
            "y": y,
            "temperature": temperature,
            "has_warning": temperature > 50.0
        }), 200
    except Exception as e:
        return jsonify({"error": f"获取温度数据错误: {str(e)}"}), 500

@app.route("/api/get-thermal-data/<file_id>", methods=["GET"])
def get_thermal_data(file_id):
    """
    获取热成像数据，如果内存中没有则从磁盘加载
    """
    thermal_data = thermal_data_store.get(file_id)
    if not thermal_data:
        thermal_data_path = os.path.join(THERMAL_DATA_FOLDER, f"{file_id}.json")
        if os.path.exists(thermal_data_path):
            with open(thermal_data_path, "r") as f:
                thermal_data = json.load(f)
            thermal_data_store[file_id] = thermal_data
        else:
            return jsonify({"error": "未找到热成像数据"}), 404
    return jsonify(thermal_data), 200

@app.route("/api/delete-thermal-image/<file_id>", methods=["DELETE"])
def delete_thermal_image(file_id):
    """
    删除指定热成像图片文件及相关数据
    """
    try:
        jpg_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.jpg")
        if os.path.exists(jpg_path):
            os.remove(jpg_path)

        json_path = os.path.join(THERMAL_DATA_FOLDER, f"{file_id}.json")
        if os.path.exists(json_path):
            os.remove(json_path)

        temp_path = os.path.join(THERMAL_DATA_FOLDER, f"{file_id}_temp.json")
        if os.path.exists(temp_path):
            os.remove(temp_path)

        meta_path = os.path.join(METADATA_FOLDER, f"{file_id}_meta.json")
        if os.path.exists(meta_path):
            os.remove(meta_path)

        thermal_data_store.pop(file_id, None)
        temperature_data_store.pop(file_id, None)
        file_metadata_store.pop(file_id, None)
        warnings_store["thermal"].pop(file_id, None)

        return jsonify({"message": "热成像图片及相关数据删除成功"}), 200
    except Exception as e:
        return jsonify({"error": f"删除文件出错: {str(e)}"}), 500

@app.route("/api/delete-thermal-data/<file_id>", methods=["DELETE"])
def delete_thermal_data(file_id):
    """
    删除指定热成像数据及相关文件
    """
    return delete_thermal_image(file_id)

# ========================= 预警相关路由 =========================

@app.route("/api/get-warnings", methods=["GET"])
def get_warnings():
    """
    获取所有预警信息
    """
    file_id = request.args.get('fileId')
    
    if file_id:
        thermal_warning = warnings_store["thermal"].get(file_id)
        tdms_warning = warnings_store["tdms"].get(file_id)
        
        return jsonify({
            "thermal": thermal_warning,
            "tdms": tdms_warning
        }), 200
    else:
        active_warnings = {
            "thermal": [
                {
                    "fileId": file_id,
                    "warning": warning_data
                } for file_id, warning_data in warnings_store["thermal"].items()
            ],
            "tdms": [
                {
                    "fileId": file_id,
                    "warning": warning_data
                } for file_id, warning_data in warnings_store["tdms"].items()
            ]
        }
        return jsonify(active_warnings), 200

@app.route("/api/delete-tdms/<file_id>", methods=["DELETE"])
def delete_tdms(file_id):
    """
    删除TDMS文件及相关数据
    """
    try:
        tdms_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.tdms")
        if os.path.exists(tdms_path):
            os.remove(tdms_path)
            
        xlsx_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.xlsx")
        if os.path.exists(xlsx_path):
            os.remove(xlsx_path)
        
        # 删除缓存文件
        cache_index_path = os.path.join(EXCEL_CACHE_FOLDER, f"{file_id}_index.pkl")
        if os.path.exists(cache_index_path):
            os.remove(cache_index_path)
            
        excel_data_cache.pop(file_id, None)
        task_status.pop(file_id, None)
        warnings_store["tdms"].pop(file_id, None)
        tdms_file_metadata.pop(file_id, None)
        
        return jsonify({"message": "TDMS文件及相关数据删除成功"}), 200
    except Exception as e:
        return jsonify({"error": f"删除TDMS文件出错: {str(e)}"}), 500

# ========================= 辅助函数 =========================

def process_with_dji_irp(jpg_path):
    """
    调用 DJI IRP 工具处理热成像图片，将 jpg 转换为 raw 格式文件
    """
    try:
        raw_path = tempfile.mktemp(suffix=".raw")
        command = [
            DJI_IRP_PATH,
            "-s", jpg_path,
            "-a", "measure",
            "-o", raw_path
        ]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
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
        data = np.fromfile(raw_path, dtype=dtype)
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

        _, buffer = cv2.imencode('.png', marked_image)
        marked_image_base64 = base64.b64encode(buffer).decode('utf-8')
        return marked_image_base64
    except Exception as e:
        print(f"生成标记图片时出错: {str(e)}")
        return None

def load_thermal_data():
    """
    加载存储在磁盘上的热成像数据文件及元数据到内存
    """
    print("正在加载热成像数据...")

    meta_files = glob.glob(os.path.join(METADATA_FOLDER, "*_meta.json"))
    for meta_path in meta_files:
        try:
            with open(meta_path, "r") as f:
                metadata = json.load(f)
                file_id = os.path.basename(meta_path).split("_")[0]
                file_metadata_store[file_id] = metadata
        except Exception as e:
            print(f"加载元数据文件 {meta_path} 失败: {str(e)}")

    thermal_files = glob.glob(os.path.join(THERMAL_DATA_FOLDER, "*.json"))
    for file_path in thermal_files:
        if "_temp.json" in file_path:
            continue
        try:
            with open(file_path, "r") as f:
                thermal_data = json.load(f)
                file_id = os.path.basename(file_path).split(".")[0]
                thermal_data_store[file_id] = thermal_data
                
                if thermal_data.get("has_warning") and thermal_data.get("highest_temp_info", {}).get("highest_temp", 0) > 50.0:
                    warnings_store["thermal"][file_id] = {
                        "type": "外壁超温",
                        "temperature": thermal_data["highest_temp_info"]["highest_temp"],
                        "threshold": 50.0,
                        "position": thermal_data["highest_temp_info"]["highest_point"]
                    }
        except Exception as e:
            print(f"加载热图数据文件 {file_path} 失败: {str(e)}")

    temp_files = glob.glob(os.path.join(THERMAL_DATA_FOLDER, "*_temp.json"))
    for temp_path in temp_files:
        try:
            with open(temp_path, "r") as f:
                temp_data = json.load(f)
                file_id = os.path.basename(temp_path).split("_")[0]
                temperature_data_store[file_id] = temp_data
        except Exception as e:
            print(f"加载温度数据文件 {temp_path} 失败: {str(e)}")

    # 加载Excel缓存索引
    cache_files = glob.glob(os.path.join(EXCEL_CACHE_FOLDER, "*_index.pkl"))
    for cache_path in cache_files:
        try:
            with open(cache_path, 'rb') as f:
                cache_data = pickle.load(f)
                file_id = os.path.basename(cache_path).split("_")[0]
                excel_data_cache[file_id] = cache_data
        except Exception as e:
            print(f"加载Excel缓存文件 {cache_path} 失败: {str(e)}")

    # 加载TDMS文件元数据（如果存在）
    try:
        tdms_metadata_path = os.path.join(METADATA_FOLDER, "tdms_metadata.json")
        if os.path.exists(tdms_metadata_path):
            with open(tdms_metadata_path, "r", encoding="utf-8") as f:
                saved_tdms_metadata = json.load(f)
                tdms_file_metadata.update(saved_tdms_metadata)
        print(f"加载了 {len(tdms_file_metadata)} 个TDMS文件元数据")
    except Exception as e:
        print(f"加载TDMS元数据失败: {str(e)}")

    for file_id in thermal_data_store:
        if file_id not in file_metadata_store:
            jpg_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.jpg")
            if os.path.exists(jpg_path):
                file_time = os.path.getctime(jpg_path)
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(file_time))
                file_name = f"thermal_image_{file_id[:8]}.jpg"
                has_warning = file_id in warnings_store["thermal"]
                file_metadata_store[file_id] = {
                    "name": file_name,
                    "timestamp": timestamp,
                    "path": jpg_path,
                    "has_warning": has_warning,
                    "warning_type": "外壁超温" if has_warning else None
                }
                meta_path = os.path.join(METADATA_FOLDER, f"{file_id}_meta.json")
                with open(meta_path, "w") as f:
                    json.dump(file_metadata_store[file_id], f)

    print(f"加载完成: {len(file_metadata_store)} 个文件元数据, {len(thermal_data_store)} 个热图数据, {len(temperature_data_store)} 个温度数据, {len(excel_data_cache)} 个Excel缓存.")

def save_tdms_metadata():
    """
    保存TDMS文件元数据到磁盘
    """
    try:
        tdms_metadata_path = os.path.join(METADATA_FOLDER, "tdms_metadata.json")
        with open(tdms_metadata_path, "w", encoding="utf-8") as f:
            json.dump(tdms_file_metadata, f, ensure_ascii=False, indent=2)
        print(f"保存了 {len(tdms_file_metadata)} 个TDMS文件元数据")
    except Exception as e:
        print(f"保存TDMS元数据失败: {str(e)}")

# 应用程序关闭时保存元数据
import atexit
atexit.register(save_tdms_metadata)

if __name__ == "__main__":
    load_thermal_data()
    print("服务器启动中...")
    print(f"目标URL: {DJI_TARGET_URL}")
    print(f"BrowserGap端口: {BROWSERGAP_PORT}")
    print("API接口:")
    print("  POST /api/browsergap/start - 启动BrowserGap服务")
    print("  POST /api/browsergap/stop - 停止BrowserGap服务")
    print("  GET  /api/browsergap/status - 获取服务状态")
    print("  POST /api/browsergap/navigate - 导航到指定URL")
    print("  GET  /api/browsergap/embed-info - 获取嵌入信息")
    app.run(debug=True, port=5001, threaded=True)