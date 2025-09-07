#!/usr/bin/env python3
"""
修复BrowserGap状态的临时脚本
"""
from services.browsergap_service import browsergap_service
import requests

try:
    # 测试服务是否真的在运行
    response = requests.get('http://localhost:8081/health', timeout=3)
    is_actually_running = response.status_code == 200
    
    print(f"实际服务状态: {'运行中' if is_actually_running else '停止'}")
    print(f"Manager中的is_running: {browsergap_service.manager.is_running}")
    
    # 手动修复状态
    if is_actually_running and not browsergap_service.manager.is_running:
        browsergap_service.manager.is_running = True
        print("✅ 已修复is_running状态")
    
    # 再次检查状态
    result = browsergap_service.get_status()
    print(f"修复后的状态: {result['status']['status']}")
    print(f"客户端连接数: {result['status'].get('clients', 0)}")
    
except Exception as e:
    print(f"错误: {e}")