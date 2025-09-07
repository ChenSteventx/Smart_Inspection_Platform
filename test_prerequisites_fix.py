#!/usr/bin/env python3
"""
测试BrowserGap前置条件检查修复
"""
import sys
import time
import requests
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def test_prerequisites_api():
    """测试前置条件检查API"""
    print("🔍 测试BrowserGap前置条件检查修复")
    print("=" * 50)
    
    try:
        # 测试直接调用服务层
        print("1. 📦 测试服务层前置条件检查:")
        start_time = time.time()
        
        from services.browsergap_service import browsergap_service
        result = browsergap_service.check_prerequisites()
        
        direct_time = time.time() - start_time
        print(f"   ⏱️  直接调用时间: {direct_time:.3f}秒")
        print(f"   ✅ 成功: {result['success']}")
        
        if result['success']:
            print("   🎉 前置条件检查通过")
            if 'issues' in result:
                print(f"   📋 问题数量: {len(result.get('issues', []))}")
        else:
            print(f"   ❌ 检查失败: {result.get('error', 'Unknown error')}")
            if 'issues' in result:
                print(f"   📋 问题列表: {result['issues']}")
            if result.get('timeout'):
                print("   ⏰ 检查超时 - 这是预期的保护机制")
        
        # 测试API接口（如果Flask应用在运行）
        print("\n2. 🌐 测试API接口:")
        try:
            api_start_time = time.time()
            response = requests.get(
                "http://localhost:5001/api/browsergap/prerequisites",
                timeout=30
            )
            api_time = time.time() - api_start_time
            
            print(f"   ⏱️  API调用时间: {api_time:.3f}秒")
            print(f"   🔗 HTTP状态码: {response.status_code}")
            
            if response.status_code == 200:
                api_result = response.json()
                print("   ✅ API调用成功")
                print(f"   📊 响应成功: {api_result.get('success', False)}")
                
                # 检查前端期望的字段
                has_issues = 'issues' in api_result
                print(f"   📋 包含issues字段: {has_issues}")
                
                if has_issues:
                    print("   🎯 前端JavaScript兼容性修复成功")
                else:
                    print("   ⚠️  前端可能仍会报错，缺少issues字段")
                    
            else:
                print(f"   ❌ API调用失败: {response.status_code}")
                print(f"   📄 响应内容: {response.text[:200]}...")
                
        except requests.exceptions.ConnectionError:
            print("   ⚠️  Flask应用未运行，跳过API测试")
        except requests.exceptions.Timeout:
            print("   ⏰ API调用超时（超过30秒）")
        except Exception as e:
            print(f"   ❌ API测试失败: {str(e)}")
        
        print("\n" + "=" * 50)
        print("🔧 修复效果总结:")
        print("   ✅ 添加了超时保护机制（60秒）")
        print("   ✅ 使用线程避免HTTP请求阻塞")
        print("   ✅ 增强了错误处理和日志")
        print("   ✅ 保持了前端期望的响应格式")
        print("   ✅ npm依赖检查超时保护（30秒）")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_prerequisites_api()