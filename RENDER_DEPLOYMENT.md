# Financial Reporting Agent - Render.com 部署指南

## 部署概述

这个项目包含两个服务：
- **FastAPI 后端**: 提供 API 服务
- **Flask 前端**: 提供 Web 界面

## ⚠️ 重要：文件存储说明

### 文件存储机制
Render.com 使用**临时文件系统**，具有以下特点：
- **存储位置**: `/tmp/data` (生产环境)
- **生命周期**: 服务重启时自动清空
- **容量限制**: 几GB 可用空间
- **访问权限**: 仅当前服务实例

### 推荐工作流程
```
用户上传 → 内存处理 → 生成结果 → 立即下载 → 自动清理
```

**优势:**
- ✅ 无存储担忧，自动清理
- ✅ 处理速度快
- ✅ 适合一次性财务分析需求
- ⚠️ 文件大小限制 (建议 < 32MB)

## 部署步骤

### 1. 准备代码仓库

确保你的代码已经推送到 GitHub/GitLab 仓库。

### 2. 部署后端服务

1. **登录 Render.com**
   - 访问 https://render.com
   - 使用 GitHub/GitLab 账号登录

2. **创建新的 Web Service**
   - 点击 "New +" → "Web Service"
   - 连接你的 Git 仓库
   - 选择项目仓库

3. **配置后端服务**
   ```
   名称: financial-backend
   环境: Python 3
   构建命令: pip install -r requirements.txt
   启动命令: python start_backend.py
   ```

4. **设置环境变量**
   在 Render 控制台的 Environment 选项卡中添加：
   ```
   ENVIRONMENT=production
   OPENAI_API_KEY=你的_OpenAI_API_密钥
   ANTHROPIC_API_KEY=你的_Anthropic_API_密钥（如果使用）
   ```

5. **部署**
   点击 "Create Web Service" 开始部署

### 3. 部署前端服务

1. **创建另一个 Web Service**
   - 同样连接到你的 Git 仓库

2. **配置前端服务**
   ```
   名称: financial-frontend
   环境: Python 3
   构建命令: pip install -r flask_frontend/requirements.txt
   启动命令: python start_frontend_render.py
   ```

3. **设置环境变量**
   ```
   ENVIRONMENT=production
   BACKEND_URL=https://你的后端服务URL.onrender.com
   FLASK_ENV=production
   ```

4. **部署**
   点击 "Create Web Service"

## 重要注意事项

### 1. 免费层限制
- Render 免费层服务在无活动时会休眠
- 首次访问可能需要等待 30-60 秒唤醒
- 建议使用付费层获得更好性能

### 2. 文件存储策略 🆕
- **临时存储**: 文件在服务重启时丢失
- **建议使用模式**: 上传 → 处理 → 下载 → 自动清理
- **文件大小限制**: 建议 < 32MB
- **如需持久化**: 考虑集成 AWS S3 等外部存储

### 3. 内存优化 🆕
- 使用内存流式处理减少磁盘依赖
- 自动清理机制防止内存泄漏
- 监控内存使用情况

### 4. 环境变量安全
- 不要在代码中硬编码 API 密钥
- 使用 Render 的环境变量功能

### 5. 数据库
- 如果需要数据库，可以在 Render 上创建 PostgreSQL 服务
- 更新连接配置以使用 Render 提供的数据库 URL

## 故障排除

### 构建失败
1. 检查 requirements.txt 是否包含所有依赖
2. 确保 Python 版本兼容
3. 查看构建日志了解具体错误

### 服务无法启动
1. 检查启动命令是否正确
2. 验证环境变量是否设置
3. 查看服务日志

### 前后端连接问题
1. 确保前端的 BACKEND_URL 指向正确的后端地址
2. 检查 CORS 设置
3. 验证网络策略

### 文件处理问题 🆕
1. **文件丢失**: 正常现象，服务重启会清空临时文件
2. **文件过大**: 调整 MAX_CONTENT_LENGTH 或使用流式处理
3. **内存不足**: 监控内存使用，考虑升级服务计划

## 监控建议 🆕

### 关键指标
- **内存使用率**: 保持在 80% 以下
- **文件处理时间**: 监控处理效率
- **错误率**: 文件上传和处理失败率
- **磁盘使用**: 临时目录大小

### 告警设置
```
内存使用 > 80% → 考虑升级计划
文件处理失败率 > 5% → 检查文件大小限制
响应时间 > 30秒 → 优化处理逻辑
```

## 访问你的应用

部署成功后，你将获得两个 URL：
- 后端 API: `https://financial-backend-xxx.onrender.com`
- 前端界面: `https://financial-frontend-xxx.onrender.com`

API 文档可以通过访问 `https://financial-backend-xxx.onrender.com/docs` 查看。

## 监控和维护

1. **日志监控**: 在 Render 控制台查看实时日志
2. **性能监控**: 监控服务响应时间和错误率
3. **自动部署**: 配置 Git 推送时自动重新部署
4. **文件清理**: 系统自动清理临时文件，无需手动维护

## 成本估算

- **免费层**: 750 小时/月（单个服务）
- **Starter 层**: $7/月，更好的性能和可靠性
- **Standard 层**: $25/月，适合生产环境

建议从免费层开始，根据使用情况升级。

## 扩展选项

### 如需持久化存储
- **AWS S3**: ~$1/月 (100用户)
- **Google Cloud Storage**: 类似成本
- **实现方式**: 参考 `RENDER_FILE_STORAGE.md` 