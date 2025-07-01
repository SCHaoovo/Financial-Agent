# 财务报告系统部署信息

## 服务配置

### 后端服务 (FastAPI)
- **平台**: Render.com
- **服务类型**: Web Service
- **启动命令**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **健康检查**: `/health`

### 前端服务 (Flask)
- **平台**: 本地运行 或 Render.com
- **启动命令**: `python flask_frontend/app.py`
- **端口**: 5000 (本地) 或 $PORT (Render)

## 环境变量

### 必需环境变量
```bash
# OpenAI API配置
OPENAI_API_KEY=your_openai_api_key_here

# 后端URL配置
BACKEND_URL=https://your-backend-url.onrender.com

# 数据目录配置
DATA_DIR=/tmp/data
PROCESSED_DATA_DIR=/tmp/data/processed
```

### 可选环境变量
```bash
# 端口配置
PORT=5000

# 环境标识
ENVIRONMENT=production

# 密钥配置
SECRET_KEY=your_secret_key_here
```

## 启动顺序

### 1. 启动后端 (Render)
1. 登录 https://dashboard.render.com
2. 找到后端服务
3. 点击 "Resume" 或重新部署
4. 等待2-3分钟直到服务完全启动

### 2. 验证后端
```bash
curl https://your-backend-url.onrender.com/health
```

### 3. 启动前端
```bash
# 方法1: 使用启动脚本
python start_services.py

# 方法2: 手动启动
export BACKEND_URL=https://your-backend-url.onrender.com
cd flask_frontend
python app.py
```

## 故障排除

### 常见问题
1. **503 Service Unavailable**: 后端服务还在启动中，等待2-3分钟
2. **Connection Error**: 检查BACKEND_URL是否正确
3. **OpenAI API Error**: 检查OPENAI_API_KEY是否设置正确

### 日志查看
- **Render后端日志**: Dashboard → 服务详情 → Logs
- **本地前端日志**: 控制台输出

## 用户权限

### 给其他用户使用权限
1. **只使用**: 分享前端URL，提供用户指南
2. **管理权限**: 在Render Dashboard中邀请团队成员
3. **开发权限**: 在GitHub仓库中添加协作者

## 成本说明

### Render免费额度
- **750小时/月** 的服务运行时间
- **15分钟无活动后自动休眠**
- **冷启动时间**: 30秒-2分钟

### 建议
- 适合测试和演示使用
- 生产环境建议升级到付费计划 