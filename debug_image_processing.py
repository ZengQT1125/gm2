#!/usr/bin/env python3
"""
调试图片处理功能的脚本
"""

import asyncio
import base64
import tempfile
import os
from pathlib import Path
from gemini_webapi import GeminiClient

# 创建一个简单的测试图片（1x1 红色像素）
def create_test_image() -> str:
    """创建一个简单的测试图片并返回 base64 编码"""
    # 1x1 红色 PNG 图片的 base64 数据
    red_pixel_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    return red_pixel_png

async def test_gemini_image_processing():
    """测试 Gemini 图片处理功能"""
    
    # 从环境变量获取凭据
    SECURE_1PSID = os.getenv("SECURE_1PSID", "")
    SECURE_1PSIDTS = os.getenv("SECURE_1PSIDTS", "")
    
    if not SECURE_1PSID or not SECURE_1PSIDTS:
        print("❌ 请设置 SECURE_1PSID 和 SECURE_1PSIDTS 环境变量")
        return
    
    try:
        # 初始化客户端
        print("🔄 初始化 Gemini 客户端...")
        client = GeminiClient(SECURE_1PSID, SECURE_1PSIDTS)
        await client.init(timeout=30)
        print("✅ Gemini 客户端初始化成功")
        
        # 测试 1: 纯文本请求
        print("\n📝 测试 1: 纯文本请求")
        response = await client.generate_content("你好，请回复'文本测试成功'")
        print(f"✅ 文本响应: {response.text[:100]}...")
        
        # 测试 2: 创建临时图片文件
        print("\n🖼️  测试 2: 创建临时图片文件")
        base64_data = create_test_image()
        image_data = base64.b64decode(base64_data)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(image_data)
            temp_file_path = tmp.name
            print(f"✅ 创建临时文件: {temp_file_path} (大小: {len(image_data)} 字节)")
        
        # 测试 3: 使用 Path 对象发送图片
        print("\n🔍 测试 3: 使用 Path 对象发送图片")
        try:
            path_obj = Path(temp_file_path)
            print(f"📁 文件路径: {path_obj}")
            print(f"📊 文件存在: {path_obj.exists()}")
            print(f"📏 文件大小: {path_obj.stat().st_size} 字节")
            
            response = await client.generate_content(
                "请描述这张图片，它是什么颜色？", 
                files=[path_obj]
            )
            print(f"✅ 图片响应: {response.text}")
            
        except Exception as e:
            print(f"❌ Path 对象测试失败: {str(e)}")
        
        # 测试 4: 使用字符串路径发送图片
        print("\n🔍 测试 4: 使用字符串路径发送图片")
        try:
            response = await client.generate_content(
                "请描述这张图片，它是什么颜色？", 
                files=[temp_file_path]
            )
            print(f"✅ 图片响应: {response.text}")
            
        except Exception as e:
            print(f"❌ 字符串路径测试失败: {str(e)}")
        
        # 测试 5: 检查 gemini-webapi 版本和功能
        print("\n📦 测试 5: 检查 gemini-webapi 信息")
        try:
            import gemini_webapi
            print(f"📋 gemini-webapi 版本: {getattr(gemini_webapi, '__version__', '未知')}")
            print(f"📋 客户端类型: {type(client)}")
            print(f"📋 可用方法: {[m for m in dir(client) if not m.startswith('_')]}")
        except Exception as e:
            print(f"❌ 版本检查失败: {str(e)}")
        
        # 清理临时文件
        try:
            os.unlink(temp_file_path)
            print(f"🗑️  清理临时文件: {temp_file_path}")
        except Exception as e:
            print(f"⚠️  清理文件失败: {str(e)}")
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_image_upload_simulation():
    """模拟网页端的图片上传流程"""
    
    print("\n🌐 测试 6: 模拟网页端图片上传流程")
    
    # 这里我们可以尝试理解网页端是如何处理图片的
    # 基于你抓取的 URL: https://push.clients6.google.com/upload/
    
    print("📋 网页端图片处理流程分析:")
    print("1. 用户粘贴/上传图片")
    print("2. 图片被上传到 Google 服务器 (push.clients6.google.com)")
    print("3. 获得 upload_id")
    print("4. 在对话中引用 upload_id 而不是原始图片数据")
    
    print("\n💡 可能的解决方案:")
    print("1. 检查 gemini-webapi 库是否正确处理文件上传")
    print("2. 确认临时文件路径格式正确")
    print("3. 验证图片文件格式和大小")
    print("4. 检查网络连接和权限")

def main():
    """主函数"""
    print("🔧 Gemini 图片处理调试工具")
    print("=" * 50)
    
    # 运行测试
    asyncio.run(test_gemini_image_processing())
    asyncio.run(test_image_upload_simulation())
    
    print("\n✨ 调试完成！")
    print("\n📝 如果图片处理仍然失败，可能的原因:")
    print("1. gemini-webapi 库版本问题")
    print("2. Google 账户权限限制")
    print("3. 网络连接问题")
    print("4. 临时文件权限问题")
    print("5. Gemini 服务端变更")

if __name__ == "__main__":
    main()
