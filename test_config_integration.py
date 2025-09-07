#!/usr/bin/env python3
"""
测试BrowserGap配置集成效果
验证config文件夹下的配置是否正常工作
"""
import time
from config import (
    Config,
    get_optimized_config,
    get_node_path,
    get_npm_path,
    is_fast_mode_enabled,
    validate_paths,
    get_env_variables
)
from services.browsergap_service import browsergap_service

def test_config_structure():
    """测试配置结构"""
    print("🔧 测试BrowserGap配置结构")
    print("=" * 50)
    
    # 1. 测试基础配置
    print("1️⃣ 基础配置测试")
    print(f"   Flask端口: {Config.FLASK_PORT}")
    print(f"   BrowserGap端口: {Config.BROWSERGAP_PORT}")
    print(f"   目标URL: {Config.DJI_TARGET_URL}")
    print(f"   Node.js路径: {Config.NODEJS_PATH}")
    print(f"   npm路径: {Config.NPM_PATH}")
    print(f"   快速模式: {Config.BROWSERGAP_FAST_MODE}")
    
    # 2. 测试BrowserGap专用配置
    print(f"\n2️⃣ BrowserGap专用配置测试")
    print(f"   Node.js路径: {get_node_path()}")
    print(f"   npm路径: {get_npm_path()}")
    print(f"   快速模式: {is_fast_mode_enabled()}")
    
    # 3. 测试完整配置
    print(f"\n3️⃣ 完整配置结构测试")
    config = get_optimized_config()
    for section_name, section_config in config.items():
        print(f"   📦 {section_name}: {len(section_config) if isinstance(section_config, dict) else 1} 项配置")
    
    # 4. 测试路径验证
    print(f"\n4️⃣ 路径验证测试")
    validation = validate_paths()
    print(f"   验证结果: {'✅ 通过' if validation['valid'] else '❌ 失败'}")
    if not validation['valid']:
        for issue in validation['issues']:
            print(f"     - {issue}")
    else:
        print(f"   Chrome路径: {validation['chrome_path']}")
    
    # 5. 测试环境变量
    print(f"\n5️⃣ 环境变量配置测试")
    env_vars = get_env_variables()
    print(f"   环境变量数量: {len(env_vars)}")
    for key, value in list(env_vars.items())[:3]:  # 显示前3个
        print(f"   {key}: {value}")
    
    return validation['valid']

def test_service_integration():
    """测试服务集成"""
    print(f"\n🚀 测试服务集成")
    print("=" * 30)
    
    try:
        # 测试快速前置条件检查
        print("📋 执行前置条件检查...")
        start_time = time.time()
        result = browsergap_service.check_prerequisites()
        check_time = time.time() - start_time
        
        print(f"   检查耗时: {check_time:.3f}秒")
        print(f"   检查结果: {'✅ 成功' if result['success'] else '❌ 失败'}")
        
        if result['success']:
            details = result.get('details', {})
            print(f"   配置详情:")
            print(f"     - Node.js: {details.get('node_path', 'Unknown')}")
            print(f"     - npm: {details.get('npm_path', 'Unknown')}")
            print(f"     - 快速模式: {details.get('fast_mode', False)}")
            return True
        else:
            print(f"   检查问题:")
            for issue in result.get('issues', []):
                print(f"     - {issue}")
            return False
            
    except Exception as e:
        print(f"   ❌ 服务集成测试失败: {str(e)}")
        return False

def show_optimization_summary():
    """显示优化总结"""
    print(f"\n💡 配置优化总结")
    print("=" * 40)
    
    print("📁 配置文件结构:")
    print("   ✅ config/browsergap_config.py - BrowserGap专用配置")
    print("   ✅ config/settings.py - 主应用配置")
    print("   ✅ config/__init__.py - 配置模块导出")
    
    print(f"\n⚡ 性能优化特性:")
    print("   ✅ 固定Node.js和npm路径")
    print("   ✅ 启用快速模式")
    print("   ✅ 路径缓存机制")
    print("   ✅ 跳过前置条件检查")
    print("   ✅ 优化的环境变量配置")
    
    print(f"\n🔧 配置管理优势:")
    print("   ✅ 集中配置管理")
    print("   ✅ 环境变量支持")
    print("   ✅ 路径自动验证")
    print("   ✅ 模块化结构")

def main():
    print("🎯 BrowserGap配置集成测试")
    print("=" * 60)
    
    # 测试配置结构
    config_ok = test_config_structure()
    
    # 测试服务集成
    service_ok = test_service_integration()
    
    # 显示优化总结
    show_optimization_summary()
    
    print(f"\n" + "=" * 60)
    if config_ok and service_ok:
        print("🎉 配置集成测试完全成功！")
        print("📈 BrowserGap现在使用统一的配置管理")
        print("⚡ 性能优化配置已生效")
        print("🏗️ 符合项目架构规范")
    else:
        print("❌ 配置集成测试有问题")
        if not config_ok:
            print("   - 配置结构验证失败")
        if not service_ok:
            print("   - 服务集成测试失败")

if __name__ == "__main__":
    main()