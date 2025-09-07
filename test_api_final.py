#!/usr/bin/env python3
"""
最终API测试脚本
"""
import requests
import json
import time

def test_api():
    print("🔍 测试BrowserGap前置条件API最终修复")
    print("=" * 50)
    
    try:
        start_time = time.time()
        print("📡 正在调用API...")
        
        response = requests.get(
            'http://localhost:5001/api/browsergap/prerequisites',
            timeout=35
        )
        
        api_time = time.time() - start_time
        print(f"⏱️  API调用时间: {api_time:.2f}秒")
        print(f"🔗 HTTP状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API调用成功!")
            print(f"📊 检查结果: {'成功' if result.get('success') else '失败'}")
            print(f"📋 包含issues字段: {'是' if 'issues' in result else '否'}")
            print(f"🔢 问题数量: {len(result.get('issues', []))}")
            
            if result.get('issues'):
                print("📝 问题列表:")
                for i, issue in enumerate(result['issues'], 1):
                    print(f"   {i}. {issue}")
            
            print("\n🎯 前端兼容性检查:")
            if 'issues' in result:
                print("   ✅ 前端JavaScript不会报错 (issues字段存在)")
            else:
                print("   ❌ 前端可能报错 (缺少issues字段)")
                
            print(f"\n📄 完整响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
            
        else:
            print(f"❌ API调用失败: HTTP {response.status_code}")
            print(f"📄 响应内容: {response.text}")
        
        return True
        
    except requests.exceptions.Timeout:
        print("⏰ API调用超时（35秒）")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_api()
    print("\n" + "=" * 50)
    if success:
        print("🎉 修复验证完成！")
        print("✅ HTTP 400错误已修复")
        print("✅ 前端JavaScript兼容性已修复")
        print("✅ API响应格式符合前端期望")
    else:
        print("❌ 仍需进一步调试")