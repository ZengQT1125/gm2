# Hugging Face 私有空间部署指南

本指南将帮助你在 Hugging Face Spaces 上部署私有的 Gemi2Api-Server。

## 部署步骤

### 1. 创建 Hugging Face Space

1. 访问 [Hugging Face Spaces](https://huggingface.co/spaces)
2. 点击 "Create new Space"
3. 填写以下信息：
   - **Space name**: 你的空间名称（例如：`my-gemi2api-server`）
   - **License**: 选择合适的许可证
   - **SDK**: 选择 `Docker`
   - **Visibility**: 选择 `Private` （这是关键！）
4. 点击 "Create Space"

### 2. 上传项目文件

将以下文件上传到你的 Hugging Face Space：

- `Dockerfile`
- `main.py`
- `pyproject.toml`
- `README.md`

### 3. 配置环境变量

在 Hugging Face Space 的 Settings 页面中，添加以下环境变量：

#### 必需的环境变量：

```
SECURE_1PSID=你的__Secure-1PSID值
SECURE_1PSIDTS=你的__Secure-1PSIDTS值
```

#### 认证相关环境变量（二选一）：

**选项 1: 使用自定义 API Key**
```
API_KEY=你自定义的API密钥
```

**选项 2: 使用 Hugging Face Token（推荐用于私有空间）**
```
HF_TOKEN=你的Hugging Face访问令牌
```

### 4. 获取 Hugging Face Token

1. 访问 [Hugging Face Settings](https://huggingface.co/settings/tokens)
2. 点击 "New token"
3. 选择 token 类型：
   - **Read**: 用于只读访问
   - **Write**: 用于读写访问（推荐）
4. 复制生成的 token
5. 将此 token 设置为 `HF_TOKEN` 环境变量

### 5. 获取 Gemini Cookie 凭据

1. 使用隐身标签访问 [Google Gemini](https://gemini.google.com/) 并登录
2. 打开浏览器开发工具 (F12)
3. 切换到 "Application" 或 "应用程序" 标签
4. 在左侧找到 "Cookies" > "gemini.google.com"
5. 复制 `__Secure-1PSID` 和 `__Secure-1PSIDTS` 的值

## 使用私有空间

### 通过 Hugging Face Token 访问

当你的空间设置为私有时，你需要在 API 请求中包含认证信息：

```bash
curl -X POST "https://你的用户名-你的空间名.hf.space/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 你的HF_TOKEN" \
  -d '{
    "model": "gemini-2.0-flash",
    "messages": [
      {
        "role": "user",
        "content": "Hello, how are you?"
      }
    ]
  }'
```

### 通过自定义 API Key 访问

如果你设置了 `API_KEY` 环境变量：

```bash
curl -X POST "https://你的用户名-你的空间名.hf.space/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 你的API_KEY" \
  -d '{
    "model": "gemini-2.0-flash",
    "messages": [
      {
        "role": "user",
        "content": "Hello, how are you?"
      }
    ]
  }'
```

## 支持的认证方式

修改后的服务器支持两种认证方式：

1. **API_KEY**: 自定义的 API 密钥
2. **HF_TOKEN**: Hugging Face 访问令牌

服务器会按以下优先级检查认证：
1. 首先检查是否匹配 `API_KEY`
2. 如果不匹配，再检查是否匹配 `HF_TOKEN`
3. 如果都不匹配，返回 401 错误

## 优势

使用私有空间的优势：

1. **隐私保护**: 只有你可以访问你的 API 服务
2. **安全性**: 通过 Hugging Face token 进行认证
3. **成本控制**: 避免被他人滥用你的 Gemini 凭据
4. **访问控制**: 可以随时撤销或更新访问令牌

## 注意事项

1. **Cookie 过期**: Gemini cookie 可能会过期，需要定期更新
2. **Token 安全**: 妥善保管你的 Hugging Face token
3. **访问限制**: 私有空间只能通过认证访问
4. **日志监控**: 定期检查空间日志以确保正常运行

## 故障排除

### 常见问题

1. **500 错误**: 通常是 Gemini cookie 过期或 IP 问题
   - 解决方案：重新获取 cookie 凭据

2. **401 错误**: 认证失败
   - 检查 `HF_TOKEN` 或 `API_KEY` 是否正确设置
   - 确认请求头中的 Authorization 格式正确

3. **空间无法访问**: 
   - 确认空间状态为 "Running"
   - 检查环境变量是否正确设置

### 调试步骤

1. 查看空间日志
2. 检查环境变量设置
3. 验证 Hugging Face token 有效性
4. 重新获取 Gemini cookie 凭据
