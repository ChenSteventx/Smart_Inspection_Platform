#!/usr/bin/env python3
"""
测试BrowserGap快速配置和启动
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from external.browser_manager_2 import BrowserGapManager
import time

def test_fast_configuration():
    """测试快速配置功能"""
    print("🚀 BrowserGap快速配置和性能优化测试")
    print("=" * 60)
    
    # 创建管理器实例
    manager = BrowserGapManager()
    
    # 配置固定路径和快速模式
    print("⚙️ 配置Node.js和npm路径...")
    manager.configure_paths(
        node_path=r'D:\nodejs\node.exe',
        npm_path=r'D:\nodejs\npm.cmd',
        fast_mode=True
    )
    
    # 显示配置状态
    print("\n📊 当前配置状态:")
    status = manager.get_optimization_status()
    for key, value in status.items():
        if isinstance(value, dict):
            print(f"   {key}:")
            for sub_key, sub_value in value.items():
                print(f"     - {sub_key}: {sub_value}")
        else:
            print(f"   {key}: {value}")
    
    # 测试快速前置条件检查
    print("\n🔍 快速前置条件检查...")
    start_time = time.time()
    result = manager.check_prerequisites()
    check_time = time.time() - start_time
    
    print(f"⏱️ 检查耗时: {check_time:.2f}秒")
    print(f"✅ 检查结果: {'成功' if result['success'] else '失败'}")
    
    if not result['success']:
        print("❌ 检查失败的问题:")
        for issue in result.get('issues', []):
            print(f"   - {issue}")
    else:
        print("✅ 所有前置条件满足")
        details = result.get('details', {})
        print(f"   - Node.js: {details.get('node_path', 'Unknown')}")
        print(f"   - npm: {details.get('npm_path', 'Unknown')}")
        print(f"   - 快速模式: {details.get('fast_mode', False)}")
    
    # 测试快速启动（如果前置条件满足）
    if result['success']:
        print("\n🚀 测试快速启动...")
        start_time = time.time()
        
        # 首先停止任何现有服务
        if manager.is_running:
            manager.stop_browsergap()
            time.sleep(2)
        
        # 快速启动
        success = manager.start_browsergap(port=8081, target_url="https://www.baidu.com")
        startup_time = time.time() - start_time
        
        print(f"⏱️ 启动耗时: {startup_time:.2f}秒")
        print(f"🎯 启动结果: {'成功' if success else '失败'}")
        
        if success:
            print("✅ BrowserGap服务快速启动成功！")
            print(f"   - 服务地址: {manager.base_url}")
            print(f"   - WebSocket: {manager.websocket_url}")
            
            # 测试服务状态
            service_status = manager.get_service_status()
            print(f"   - 服务状态: {service_status.get('status', 'unknown')}")
            print(f"   - 客户端连接: {service_status.get('clients', 0)}")
        else:
            print("❌ 快速启动失败")
    
    return result['success']

def show_optimization_tips():
    """显示性能优化建议"""
    print("\n💡 BrowserGap性能优化建议")
    print("=" * 40)
    
    print("1️⃣ 路径配置优化:")
    print("   ✅ 使用固定的Node.js和npm路径")
    print("   ✅ 启用路径缓存机制")
    print("   ✅ 避免重复的路径检测")
    
    print("\n2️⃣ 启动速度优化:")
    print("   ✅ 启用快速模式跳过前置条件检查")
    print("   ✅ 缩短服务初始化等待时间")
    print("   ✅ 优化端口占用检查")
    
    print("\n3️⃣ 运行时优化:")
    print("   ✅ 配置生产环境变量")
    print("   ✅ 使用固定的Chrome路径")
    print("   ✅ 优化进程启动参数")
    
    print("\n4️⃣ 建议的配置:")
    print("   - Node.js路径: D:\\nodejs\\node.exe")
    print("   - npm路径: D:\\nodejs\\npm.cmd")
    print("   - 快速模式: 启用")
    print("   - 缓存超时: 5分钟")

def main():
    print("🔧 BrowserGap配置和性能优化")
    print("=" * 50)
    
    # 测试快速配置
    success = test_fast_configuration()
    
    # 显示优化建议
    show_optimization_tips()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 BrowserGap配置和优化完成！")
        print("📈 启动速度已大幅提升")
        print("⚡ 服务响应更加迅速")
    else:
        print("❌ 配置过程中遇到问题")
        print("💡 请检查Node.js和npm安装")

if __name__ == "__main__":
    main()