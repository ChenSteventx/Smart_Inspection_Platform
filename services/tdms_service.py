"""
TDMS数据处理服务模块
负责TDMS文件的上传、处理、可视化和Excel转换功能
"""
import os
import re
import uuid
import time
import json
import threading
import pickle
import base64
from io import BytesIO
from math import ceil
from concurrent.futures import ThreadPoolExecutor
import logging

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from nptdms import TdmsFile

from config.settings import Config
from storage.warnings_storage import warnings_storage

logger = logging.getLogger(__name__)

class TDMSService:
    """TDMS数据处理服务"""
    
    def __init__(self):
        # 初始化存储
        self.tdms_file_metadata = {}
        self.task_status = {}
        # 优化: 使用全局预警存储，保证数据一致性
        # self.warnings_store = {}  # 已移除，使用全局warnings_storage
        self.excel_data_cache = {}
        
        # 线程池执行器
        self.executor = ThreadPoolExecutor(max_workers=Config.THREAD_POOL_MAX_WORKERS)
        
        # 确保必要目录存在
        Config.init_directories()
        
        # 加载已有元数据
        self._load_metadata()
    
    def _load_metadata(self):
        """加载TDMS文件元数据"""
        try:
            metadata_file = Config.METADATA_FOLDER / "tdms_metadata.json"
            if metadata_file.exists():
                with open(metadata_file, "r", encoding="utf-8") as f:
                    self.tdms_file_metadata = json.load(f)
                    
            # 加载Excel缓存索引
            cache_files = list(Config.EXCEL_CACHE_FOLDER.glob("*_index.pkl"))
            for cache_path in cache_files:
                try:
                    with open(cache_path, 'rb') as f:
                        cache_data = pickle.load(f)
                        file_id = cache_path.stem.split("_")[0]
                        self.excel_data_cache[file_id] = cache_data
                except Exception as e:
                    logger.error(f"加载Excel缓存文件 {cache_path} 失败: {str(e)}")
                    
            logger.info(f"加载了 {len(self.tdms_file_metadata)} 个TDMS文件元数据")
        except Exception as e:
            logger.error(f"加载TDMS元数据失败: {str(e)}")
    
    def _save_metadata(self):
        """保存TDMS文件元数据"""
        try:
            metadata_file = Config.METADATA_FOLDER / "tdms_metadata.json"
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(self.tdms_file_metadata, f, ensure_ascii=False, indent=2)
            logger.info(f"保存了 {len(self.tdms_file_metadata)} 个TDMS文件元数据")
        except Exception as e:
            logger.error(f"保存TDMS元数据失败: {str(e)}")
    
    def upload_tdms(self, file, original_filename=None):
        """上传TDMS文件"""
        try:
            file_id = str(uuid.uuid4())
            file_name = f"{file_id}.tdms"
            file_path = Config.UPLOAD_FOLDER / file_name
            
            # 保存文件
            file.save(file_path)
            
            # 获取文件信息
            file_size = file_path.stat().st_size
            upload_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            display_name = original_filename or f"tdms_file_{file_id[:8]}.tdms"
            
            # 存储文件元数据
            self.tdms_file_metadata[file_id] = {
                "original_name": display_name,
                "file_path": str(file_path),
                "file_size": file_size,
                "upload_time": upload_time,
                "status": "uploaded",
                "display_name": display_name
            }
            
            # 保存元数据
            self._save_metadata()
            
            return {
                "success": True,
                "fileId": file_id,
                "message": "TDMS 文件上传并保存成功",
                "fileSize": file_size,
                "fileName": display_name,
                "uploadTime": upload_time
            }
            
        except Exception as e:
            logger.error(f"TDMS文件上传失败: {str(e)}")
            return {
                "success": False,
                "error": f"上传失败: {str(e)}"
            }
    
    def process_tdms(self, file_id):
        """处理TDMS文件，将数据转换为图像并返回图像的base64编码"""
        try:
            tdms_name = f"{file_id}.tdms"
            tdms_path = Config.UPLOAD_FOLDER / tdms_name
            
            if not tdms_path.exists():
                return {
                    "success": False,
                    "error": "未找到对应的 TDMS 文件"
                }
            
            # 更新处理状态
            if file_id in self.tdms_file_metadata:
                self.tdms_file_metadata[file_id]["status"] = "processing_visualization"
            
            # 读取TDMS文件
            tdms_file = TdmsFile.read(str(tdms_path))
            
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
            
            # 保存预警信息 - 优化: 使用全局预警存储
            if has_warning:
                warnings_storage.add_tdms_warning(file_id, {
                    "type": "内壁破损",
                    "active_channels": active_channels,
                    "is_three_channel_mode": is_three_channel_mode,
                    "inactive_channel": inactive_channel,
                    "positions": warning_positions
                })
            else:
                warnings_storage.remove_tdms_warning(file_id)
            
            # 对每列内的通道按x值排序
            for y in channels_by_col:
                channels_by_col[y].sort(key=lambda item: item[0])
            
            # 可视化部分 - 绘制图形
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
            if file_id in self.tdms_file_metadata:
                self.tdms_file_metadata[file_id]["status"] = "visualization_completed"
                self._save_metadata()
            
            return {
                "success": True,
                "message": "TDMS 处理完成",
                "plot_base64": png_base64,
                "has_warning": has_warning,
                "warning_type": "内壁破损" if has_warning else None,
                "active_channels": active_channels,
                "is_three_channel_mode": is_three_channel_mode,
                "channel_data": channel_thickness_data,
                "warning_positions": warning_positions if has_warning else []
            }
            
        except Exception as e:
            logger.error(f"处理TDMS文件失败: {str(e)}")
            return {
                "success": False,
                "error": f"生成图像失败: {str(e)}"
            }
    
    def get_tdms_summary(self):
        """获取TDMS文件处理概要信息"""
        try:
            total_files = len(self.tdms_file_metadata)
            processed_files = 0
            files_with_warnings = 0
            
            for file_id, metadata in self.tdms_file_metadata.items():
                if metadata.get("status") in ["visualization_completed", "excel_completed"]:
                    processed_files += 1
                
                if file_id in warnings_storage._warnings["tdms"]:  # 优化: 使用全局预警存储
                    files_with_warnings += 1
            
            return {
                "success": True,
                "summary": {
                    "total_files": total_files,
                    "processed_files": processed_files,
                    "pending_files": total_files - processed_files,
                    "files_with_warnings": files_with_warnings,
                    "processing_rate": round((processed_files / total_files * 100) if total_files > 0 else 0, 1)
                }
            }
            
        except Exception as e:
            logger.error(f"获取TDMS概要信息时发生错误: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_latest_tdms_image(self):
        """获取最新的已处理TDMS图像数据，用于导航界面预览"""
        try:
            # 获取所有已处理且有图像数据的TDMS文件
            processed_files = []
            
            for file_id, metadata in self.tdms_file_metadata.items():
                if metadata.get("status") in ["visualization_completed", "excel_completed"]:
                    tdms_name = f"{file_id}.tdms"
                    tdms_path = Config.UPLOAD_FOLDER / tdms_name
                    if tdms_path.exists():
                        processed_files.append({
                            "file_id": file_id,
                            "metadata": metadata,
                            "last_modified": tdms_path.stat().st_mtime
                        })
            
            if not processed_files:
                return {
                    "success": False,
                    "message": "暂无已处理的TDMS文件",
                    "has_image": False
                }
            
            # 按最后修改时间排序，获取最新的文件
            processed_files.sort(key=lambda x: x["last_modified"], reverse=True)
            latest_file = processed_files[0]
            latest_file_id = latest_file["file_id"]
            
            # 尝试重新处理以获取图像（如果图像不存在）
            result = self.process_tdms(latest_file_id)
            
            if result["success"]:
                file_metadata = latest_file["metadata"]
                return {
                    "success": True,
                    "has_image": True,
                    "file_id": latest_file_id,
                    "file_name": file_metadata.get("original_name", f"文件_{latest_file_id[:8]}"),
                    "upload_time": file_metadata.get("upload_time", ""),
                    "plot_base64": result["plot_base64"],
                    "has_warning": result["has_warning"],
                    "warning_type": result["warning_type"],
                    "active_channels": result["active_channels"],
                    "total_files": len(processed_files),
                    "preview_info": {
                        "channels": result["active_channels"],
                        "warning_count": len(result.get("warning_positions", []))
                    }
                }
            else:
                # 如果处理失败，返回文件信息但没有图像
                file_metadata = latest_file["metadata"]
                return {
                    "success": True,
                    "has_image": False,
                    "file_id": latest_file_id,
                    "file_name": file_metadata.get("original_name", f"文件_{latest_file_id[:8]}"),
                    "upload_time": file_metadata.get("upload_time", ""),
                    "error": result.get("error", "图像生成失败"),
                    "total_files": len(processed_files)
                }
                
        except Exception as e:
            logger.error(f"获取最新TDMS图像时发生错误: {str(e)}")
            return {
                "success": False,
                "error": f"获取图像失败: {str(e)}",
                "has_image": False
            }
    
    def process_tdms_to_excel(self, file_id):
        """异步处理TDMS文件转换为Excel文件"""
        try:
            tdms_name = f"{file_id}.tdms"
            tdms_path = Config.UPLOAD_FOLDER / tdms_name
            
            if not tdms_path.exists():
                return {
                    "success": False,
                    "error": "未找到 TDMS 文件"
                }
            
            # 检查是否已经在处理中
            if file_id in self.task_status and self.task_status[file_id].get("status") == "processing":
                return {
                    "success": True,
                    "message": "任务正在处理中",
                    "status": self.task_status[file_id]
                }
            
            # 检查是否已经完成
            xlsx_path = Config.UPLOAD_FOLDER / f"{file_id}.xlsx"
            if xlsx_path.exists() and file_id in self.excel_data_cache:
                return {
                    "success": True,
                    "message": "Excel文件已存在",
                    "status": {"status": "completed", "progress": 100}
                }
            
            # 启动后台任务
            self.executor.submit(self._process_tdms_to_excel_background, file_id)
            
            return {
                "success": True,
                "message": "Excel转换任务已启动",
                "status": {"status": "processing", "progress": 0}
            }
            
        except Exception as e:
            logger.error(f"启动Excel转换任务失败: {str(e)}")
            return {
                "success": False,
                "error": f"启动任务失败: {str(e)}"
            }
    
    def get_warnings(self, file_id=None):
        """获取预警信息 - 优化: 使用全局预警存储"""
        try:
            if file_id:
                warning = warnings_storage.get_tdms_warning(file_id)
                return {
                    "success": True,
                    "warning": warning
                }
            else:
                warnings = warnings_storage.get_all_tdms_warnings()
                return {
                    "success": True,
                    "warnings": warnings
                }
        except Exception as e:
            logger.error(f"获取TDMS预警信息失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取预警信息失败: {str(e)}"
            }

# 全局服务实例
tdms_service = TDMSService()