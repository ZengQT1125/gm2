# 从 GitHub 部署到 Hugging Face 指南

本指南将帮助你将 GitHub 上的项目直接部署到 Hugging Face Spaces。

## 🚀 快速部署步骤

### 1. 准备 GitHub 仓库

1. **Fork 或上传项目到你的 GitHub**
   ```bash
   # 如果是新仓库
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/你的用户名/你的仓库名.git
   git push -u origin main
   ```

2. **确保仓库是公开的**（Hugging Face 需要访问你的仓库）

### 2. 在 Hugging Face 创建 Space

1. 访问 [Hugging Face Spaces](https://huggingface.co/spaces)
2. 点击 "Create new Space"
3. 填写信息：
   - **Space name**: 你的空间名称
   - **License**: 选择合适的许可证
   - **SDK**: 选择 `Docker`
   - **Visibility**: 选择 `Private` （推荐）
4. 点击 "Create Space"

### 3. 连接 GitHub 仓库

在创建的 Space 页面：

1. 点击 "Settings" 标签
2. 在 "Repository" 部分：
   - 选择 "Git repository"
   - 输入你的 GitHub 仓库 URL: `https://github.com/你的用户名/你的仓库名`
   - 选择分支（通常是 `main`）
3. 点击 "Update"

### 4. 配置环境变量

在 Space 的 Settings 页面，添加以下环境变量：

#### 必需变量：
```
SECURE_1PSID=你的__Secure-1PSID值
SECURE_1PSIDTS=你的__Secure-1PSIDTS值
```

#### 认证变量（推荐使用 HF_TOKEN）：
```
HF_TOKEN=你的Hugging Face访问令牌  # 推荐
```

#### 可选的传统认证方式：
```
API_KEY=你自定义的API密钥  # 仍然支持，但不推荐
```

### 5. 获取必要的令牌

#### 获取 Gemini Cookie：
1. 访问 [Google Gemini](https://gemini.google.com/) 并登录
2. 打开浏览器开发工具 (F12)
3. 切换到 "Application" 标签
4. 找到 "Cookies" > "gemini.google.com"
5. 复制 `__Secure-1PSID` 和 `__Secure-1PSIDTS` 的值

#### 获取 Hugging Face Token：
1. 访问 [Hugging Face Settings](https://huggingface.co/settings/tokens)
2. 点击 "New token"
3. 选择权限（推荐 "Write"）
4. 复制生成的令牌

### 6. 部署和测试

1. **保存设置后，Space 会自动开始构建**
2. **等待构建完成**（通常需要几分钟）
3. **测试部署**：
   ```bash
   # 健康检查
   curl https://你的用户名-你的空间名.hf.space/

   # 测试 API（推荐使用 X-API-Key）
   curl -X POST "https://你的用户名-你的空间名.hf.space/v1/chat/completions" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: 你的HF_TOKEN" \
     -d '{
       "model": "gemini-2.0-flash",
       "messages": [{"role": "user", "content": "Hello!"}]
     }'

   # 或者使用传统方式（仍然支持）
   curl -X POST "https://你的用户名-你的空间名.hf.space/v1/chat/completions" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer 你的HF_TOKEN" \
     -d '{
       "model": "gemini-2.0-flash",
       "messages": [{"role": "user", "content": "Hello!"}]
     }'
   ```

## 🔄 自动更新

当你的 GitHub 仓库有新的提交时：

1. **自动同步**：Hugging Face 会自动检测更改并重新部署
2. **手动同步**：在 Space 页面点击 "Sync" 按钮
3. **查看日志**：在 "Logs" 标签查看构建和运行日志

## 📁 项目结构

确保你的 GitHub 仓库包含以下文件：

```
你的仓库/
├── Dockerfile              # Docker 构建文件
├── main.py                 # 主应用文件
├── pyproject.toml          # Python 依赖配置
├── README.md               # 项目说明
├── .env.example            # 环境变量模板
├── .gitignore              # Git 忽略文件
├── HUGGINGFACE_DEPLOYMENT.md  # 部署指南
├── test_private_access.py  # 测试脚本
└── examples/
    └── private_space_usage.py  # 使用示例
```

## 🛠️ 故障排除

### 常见问题：

1. **构建失败**
   - 检查 Dockerfile 语法
   - 确保 pyproject.toml 中的依赖正确
   - 查看构建日志获取详细错误信息

2. **运行时错误**
   - 检查环境变量是否正确设置
   - 验证 Gemini Cookie 是否有效
   - 查看运行日志

3. **认证失败**
   - 确认 HF_TOKEN 或 API_KEY 设置正确
   - 检查令牌权限
   - 验证请求头格式

### 调试步骤：

1. **查看 Space 日志**
2. **使用测试脚本验证**：
   ```bash
   python test_private_access.py
   ```
3. **检查环境变量**
4. **重新获取 Gemini Cookie**

## 🎯 优势

从 GitHub 部署的优势：

- ✅ **版本控制**：完整的代码历史记录
- ✅ **自动同步**：代码更新自动部署
- ✅ **协作开发**：支持多人协作
- ✅ **备份安全**：代码安全存储在 GitHub
- ✅ **CI/CD**：可以配置自动化测试和部署

## 📞 支持

如果遇到问题：

1. 查看项目的 [详细部署指南](./HUGGINGFACE_DEPLOYMENT.md)
2. 检查 [使用示例](./examples/private_space_usage.py)
3. 运行 [测试脚本](./test_private_access.py) 进行诊断
