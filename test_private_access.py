#!/usr/bin/env python3
"""
测试私有 Hugging Face Space 访问的脚本
"""

import requests
import json
import os
from typing import Optional

def test_api_access(
    base_url: str,
    token: str,
    token_type: str = "HF_TOKEN"
) -> None:
    """
    测试 API 访问
    
    Args:
        base_url: Hugging Face Space 的 URL
        token: 访问令牌 (HF_TOKEN 或 API_KEY)
        token_type: 令牌类型，用于日志显示
    """
    
    # 测试健康检查端点
    print(f"🔍 Testing health check endpoint...")
    try:
        response = requests.get(f"{base_url}/")
        print(f"✅ Health check: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return
    
    # 测试模型列表端点（需要认证）
    print(f"\n🔍 Testing models endpoint with {token_type}...")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(f"{base_url}/v1/models", headers=headers)
        if response.status_code == 200:
            models = response.json()
            print(f"✅ Models endpoint: {response.status_code}")
            print(f"📋 Available models: {len(models.get('data', []))} models")
            for model in models.get('data', [])[:3]:  # 显示前3个模型
                print(f"   - {model.get('id', 'Unknown')}")
        else:
            print(f"❌ Models endpoint failed: {response.status_code} - {response.text}")
            return
    except Exception as e:
        print(f"❌ Models endpoint failed: {e}")
        return
    
    # 测试聊天完成端点
    print(f"\n🔍 Testing chat completions endpoint...")
    chat_data = {
        "model": "gemini-2.0-flash",
        "messages": [
            {
                "role": "user",
                "content": "Hello! Please respond with 'API test successful' if you can see this message."
            }
        ],
        "max_tokens": 50,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            headers=headers,
            json=chat_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Chat completion: {response.status_code}")
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                print(f"🤖 Response: {content[:100]}...")
                print(f"📊 Usage: {result.get('usage', {})}")
            else:
                print(f"⚠️  Unexpected response format: {result}")
        else:
            print(f"❌ Chat completion failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Chat completion failed: {e}")

def main():
    """主函数"""
    print("🚀 Hugging Face Private Space API Test")
    print("=" * 50)
    
    # 从环境变量或用户输入获取配置
    base_url = os.getenv("HF_SPACE_URL")
    if not base_url:
        base_url = input("请输入你的 Hugging Face Space URL (例如: https://username-spacename.hf.space): ").strip()
    
    # 移除末尾的斜杠
    base_url = base_url.rstrip('/')
    
    # 获取认证令牌
    hf_token = os.getenv("HF_TOKEN")
    api_key = os.getenv("API_KEY")
    
    if not hf_token and not api_key:
        print("\n🔑 请提供认证信息:")
        print("1. Hugging Face Token")
        print("2. 自定义 API Key")
        choice = input("选择认证方式 (1/2): ").strip()
        
        if choice == "1":
            hf_token = input("请输入你的 HF_TOKEN: ").strip()
        elif choice == "2":
            api_key = input("请输入你的 API_KEY: ").strip()
        else:
            print("❌ 无效选择")
            return
    
    print(f"\n🌐 Testing API at: {base_url}")
    
    # 测试 HF_TOKEN
    if hf_token:
        print(f"\n🔐 Testing with HF_TOKEN...")
        test_api_access(base_url, hf_token, "HF_TOKEN")
    
    # 测试 API_KEY
    if api_key:
        print(f"\n🔐 Testing with API_KEY...")
        test_api_access(base_url, api_key, "API_KEY")
    
    print(f"\n✨ Test completed!")

if __name__ == "__main__":
    main()
