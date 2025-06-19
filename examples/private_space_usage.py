#!/usr/bin/env python3
"""
使用私有 Hugging Face Space 的示例代码
"""

import requests
import json
import os

# 配置
SPACE_URL = "https://your-username-your-spacename.hf.space"  # 替换为你的空间URL
HF_TOKEN = "your_hf_token_here"  # 替换为你的 HF Token
# 或者使用自定义 API Key
# API_KEY = "your_api_key_here"

def chat_with_gemini(message: str, token: str) -> str:
    """
    与 Gemini 聊天
    
    Args:
        message: 要发送的消息
        token: 认证令牌 (HF_TOKEN 或 API_KEY)
    
    Returns:
        Gemini 的回复
    """
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "gemini-2.0-flash",
        "messages": [
            {
                "role": "user",
                "content": message
            }
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        response = requests.post(
            f"{SPACE_URL}/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return f"Error: {response.status_code} - {response.text}"
            
    except Exception as e:
        return f"Exception: {str(e)}"

def stream_chat_with_gemini(message: str, token: str):
    """
    流式聊天示例
    
    Args:
        message: 要发送的消息
        token: 认证令牌
    """
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "gemini-2.0-flash",
        "messages": [
            {
                "role": "user",
                "content": message
            }
        ],
        "temperature": 0.7,
        "stream": True
    }
    
    try:
        response = requests.post(
            f"{SPACE_URL}/v1/chat/completions",
            headers=headers,
            json=data,
            stream=True,
            timeout=30
        )
        
        if response.status_code == 200:
            print("🤖 Gemini (streaming): ", end="", flush=True)
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data_str = line[6:]  # 移除 'data: ' 前缀
                        if data_str.strip() == '[DONE]':
                            break
                        try:
                            data = json.loads(data_str)
                            if 'choices' in data and len(data['choices']) > 0:
                                delta = data['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    print(delta['content'], end="", flush=True)
                        except json.JSONDecodeError:
                            continue
            print()  # 换行
        else:
            print(f"Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Exception: {str(e)}")

def get_available_models(token: str) -> list:
    """
    获取可用模型列表
    
    Args:
        token: 认证令牌
    
    Returns:
        模型列表
    """
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(
            f"{SPACE_URL}/v1/models",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return [model['id'] for model in result.get('data', [])]
        else:
            print(f"Error getting models: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        print(f"Exception getting models: {str(e)}")
        return []

def main():
    """主函数"""
    
    # 从环境变量获取令牌
    token = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
    
    if not token:
        print("请设置 HF_TOKEN 或 API_KEY 环境变量")
        print("或者直接在代码中修改 HF_TOKEN 或 API_KEY 变量")
        return
    
    print("🚀 私有 Hugging Face Space 使用示例")
    print("=" * 50)
    
    # 获取可用模型
    print("📋 获取可用模型...")
    models = get_available_models(token)
    if models:
        print(f"✅ 找到 {len(models)} 个模型:")
        for model in models[:5]:  # 显示前5个
            print(f"   - {model}")
    else:
        print("❌ 无法获取模型列表")
        return
    
    # 普通聊天示例
    print("\n💬 普通聊天示例:")
    message = "你好！请用中文回复。"
    print(f"👤 用户: {message}")
    
    response = chat_with_gemini(message, token)
    print(f"🤖 Gemini: {response}")
    
    # 流式聊天示例
    print("\n🌊 流式聊天示例:")
    message = "请写一首关于人工智能的短诗。"
    print(f"👤 用户: {message}")
    
    stream_chat_with_gemini(message, token)
    
    print("\n✨ 示例完成！")

if __name__ == "__main__":
    main()
