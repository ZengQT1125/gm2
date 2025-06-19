# 🔐 认证方式更新说明

## 📋 Hugging Face Spaces 的变化

Hugging Face 最近更新了 Spaces 的安全策略，主要变化包括：

1. **推荐使用 `X-API-Key` 头部**而不是 `Authorization` 头部
2. **私有空间的访问控制更严格**
3. **推荐使用 HF Token 而不是自定义 API Key**

## 🔄 代码更新

### 1. 服务端更新 (`main.py`)

我们的 `verify_api_key` 函数现在支持两种认证方式：

```python
async def verify_api_key(
    authorization: str = Header(None),
    x_api_key: str = Header(None, alias="X-API-Key")
):
```

**认证优先级：**
1. 首先检查 `X-API-Key` 头部（Hugging Face Spaces 推荐）
2. 如果没有，回退到 `Authorization: Bearer` 头部（传统方式）

### 2. 客户端更新

#### 新的推荐方式（X-API-Key）：
```bash
curl -X POST "https://your-space.hf.space/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_hf_token_here" \
  -d '{"model": "gemini-2.0-flash", "messages": [{"role": "user", "content": "Hello!"}]}'
```

#### 传统方式（仍然支持）：
```bash
curl -X POST "https://your-space.hf.space/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_hf_token_here" \
  -d '{"model": "gemini-2.0-flash", "messages": [{"role": "user", "content": "Hello!"}]}'
```

## 🚀 部署建议

### 环境变量配置

**推荐配置（仅使用 HF_TOKEN）：**
```
SECURE_1PSID=你的__Secure-1PSID值
SECURE_1PSIDTS=你的__Secure-1PSIDTS值
HF_TOKEN=你的Hugging Face访问令牌
```

**不推荐（但仍支持）：**
```
SECURE_1PSID=你的__Secure-1PSID值
SECURE_1PSIDTS=你的__Secure-1PSIDTS值
API_KEY=你自定义的API密钥
```

### 为什么推荐使用 HF_TOKEN？

1. **原生集成**：与 Hugging Face 生态系统完美集成
2. **权限管理**：可以在 Hugging Face 设置中轻松管理权限
3. **安全性**：可以随时撤销和重新生成
4. **兼容性**：更好地适配 Hugging Face Spaces 的安全策略

## 🧪 测试更新

### 测试脚本更新

我们的测试脚本 (`test_private_access.py`) 现在会：

1. **首先尝试 X-API-Key 认证**
2. **如果失败，回退到 Authorization 认证**
3. **显示哪种方式成功**

### 使用示例更新

`examples/private_space_usage.py` 中的函数现在支持 `use_x_api_key` 参数：

```python
# 使用 X-API-Key（推荐）
response = chat_with_gemini("Hello!", token, use_x_api_key=True)

# 使用传统 Authorization 头
response = chat_with_gemini("Hello!", token, use_x_api_key=False)
```

## 🔧 迁移指南

### 对于现有用户：

1. **无需立即更改**：现有的 `Authorization: Bearer` 方式仍然有效
2. **建议更新**：逐步迁移到 `X-API-Key` 方式
3. **环境变量**：考虑从 `API_KEY` 迁移到 `HF_TOKEN`

### 对于新用户：

1. **直接使用 HF_TOKEN**
2. **使用 X-API-Key 头部**
3. **设置私有空间**

## 📊 兼容性矩阵

| 认证方式 | 头部类型 | 环境变量 | 状态 | 推荐度 |
|---------|---------|---------|------|--------|
| X-API-Key | `X-API-Key: TOKEN` | `HF_TOKEN` | ✅ 支持 | ⭐⭐⭐⭐⭐ |
| X-API-Key | `X-API-Key: TOKEN` | `API_KEY` | ✅ 支持 | ⭐⭐⭐ |
| Authorization | `Authorization: Bearer TOKEN` | `HF_TOKEN` | ✅ 支持 | ⭐⭐⭐⭐ |
| Authorization | `Authorization: Bearer TOKEN` | `API_KEY` | ✅ 支持 | ⭐⭐ |

## 🐛 故障排除

### 常见问题：

1. **401 错误**：
   - 检查是否使用了正确的头部格式
   - 验证 token 是否有效
   - 确认环境变量设置正确

2. **认证方式不确定**：
   - 查看服务器日志，会显示使用了哪种认证方式
   - 使用测试脚本验证两种方式

3. **HF Token 获取**：
   - 访问 [Hugging Face Settings](https://huggingface.co/settings/tokens)
   - 创建新的访问令牌
   - 选择适当的权限（推荐 "Write"）

### 调试技巧：

1. **查看服务器日志**：
   ```
   Successfully authenticated using X-API-Key header with HF_TOKEN
   ```

2. **使用测试脚本**：
   ```bash
   python test_private_access.py
   ```

3. **检查响应头**：
   服务器会在日志中显示使用的认证方式

## 🎯 最佳实践

1. **使用 HF_TOKEN**：更好的集成和安全性
2. **优先使用 X-API-Key**：更好的兼容性
3. **设置私有空间**：保护你的资源
4. **定期更新 token**：提高安全性
5. **监控日志**：了解认证状态
