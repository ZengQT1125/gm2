#!/usr/bin/env python3
"""
测试图片支持功能的脚本
"""

import requests
import json
import base64
import os

# 配置
SPACE_URL = "https://zqt25-gmn2a.hf.space"  # 你的空间URL
HF_TOKEN = "your_hf_token_here"  # 替换为你的 HF Token

def encode_image_to_base64(image_path: str) -> str:
    """
    将本地图片编码为 base64 格式
    
    Args:
        image_path: 图片文件路径
    
    Returns:
        base64 编码的图片数据URL
    """
    with open(image_path, "rb") as image_file:
        image_data = image_file.read()
        base64_data = base64.b64encode(image_data).decode('utf-8')
        
        # 根据文件扩展名确定 MIME 类型
        ext = os.path.splitext(image_path)[1].lower()
        if ext in ['.jpg', '.jpeg']:
            mime_type = 'image/jpeg'
        elif ext == '.png':
            mime_type = 'image/png'
        elif ext == '.gif':
            mime_type = 'image/gif'
        elif ext == '.webp':
            mime_type = 'image/webp'
        else:
            mime_type = 'image/png'  # 默认
        
        return f"data:{mime_type};base64,{base64_data}"

def test_image_chat(image_path: str, question: str, token: str) -> str:
    """
    测试图片聊天功能
    
    Args:
        image_path: 图片文件路径
        question: 关于图片的问题
        token: 认证令牌
    
    Returns:
        Gemini 的回复
    """
    
    # 编码图片
    try:
        image_data_url = encode_image_to_base64(image_path)
        print(f"✅ 图片编码成功: {image_path}")
        print(f"📏 Base64 数据长度: {len(image_data_url)} 字符")
    except Exception as e:
        print(f"❌ 图片编码失败: {e}")
        return None
    
    # 准备请求数据
    headers = {
        "X-API-Key": token,
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "gemini-2.0-flash",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": question
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data_url
                        }
                    }
                ]
            }
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        print(f"🚀 发送图片分析请求...")
        response = requests.post(
            f"{SPACE_URL}/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=60  # 图片处理可能需要更长时间
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                print(f"✅ 图片分析成功!")
                print(f"🤖 Gemini 回复: {content}")
                return content
            else:
                print(f"⚠️  响应格式异常: {result}")
                return None
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return None

def test_url_image(image_url: str, question: str, token: str) -> str:
    """
    测试 URL 图片功能
    
    Args:
        image_url: 图片 URL
        question: 关于图片的问题
        token: 认证令牌
    
    Returns:
        Gemini 的回复
    """
    
    headers = {
        "X-API-Key": token,
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "gemini-2.0-flash",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": question
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    }
                ]
            }
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        print(f"🚀 发送 URL 图片分析请求...")
        print(f"🔗 图片 URL: {image_url}")
        
        response = requests.post(
            f"{SPACE_URL}/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                print(f"✅ URL 图片分析成功!")
                print(f"🤖 Gemini 回复: {content}")
                return content
            else:
                print(f"⚠️  响应格式异常: {result}")
                return None
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return None

def main():
    """主函数"""
    
    # 从环境变量获取令牌
    token = os.getenv("HF_TOKEN")
    
    if not token:
        print("请设置 HF_TOKEN 环境变量")
        print("或者直接在代码中修改 HF_TOKEN 变量")
        return
    
    print("🖼️  图片支持功能测试")
    print("=" * 50)
    
    # 测试本地图片
    print("\n📁 测试本地图片...")
    image_path = input("请输入本地图片路径（或按回车跳过）: ").strip()
    
    if image_path and os.path.exists(image_path):
        question = input("请输入关于图片的问题（默认：请描述这张图片）: ").strip()
        if not question:
            question = "请描述这张图片"
        
        result = test_image_chat(image_path, question, token)
        if not result:
            print("❌ 本地图片测试失败")
    elif image_path:
        print(f"❌ 图片文件不存在: {image_path}")
    
    # 测试 URL 图片
    print("\n🌐 测试 URL 图片...")
    image_url = input("请输入图片 URL（或按回车使用默认测试图片）: ").strip()
    
    if not image_url:
        # 使用一个公开的测试图片
        image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
        print(f"使用默认测试图片: {image_url}")
    
    question = input("请输入关于图片的问题（默认：请描述这张图片）: ").strip()
    if not question:
        question = "请描述这张图片"
    
    result = test_url_image(image_url, question, token)
    if not result:
        print("❌ URL 图片测试失败")
    
    print("\n✨ 测试完成！")

if __name__ == "__main__":
    main()
