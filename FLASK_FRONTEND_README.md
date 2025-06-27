# 财务报告系统 - Flask前端启动指南

## 🚀 快速启动

### 方法1: 使用启动脚本 (推荐)

```bash
# 直接运行启动脚本
python start_frontend.py
```

启动脚本会自动：
- ✅ 检查Python版本
- 📦 安装依赖
- 📁 创建必要目录
- 🔗 检查后端状态
- 🚀 启动Flask应用

### 方法2: 手动启动

```bash
# 1. 安装依赖
pip install -r flask_frontend/requirements.txt

# 2. 创建必要目录
mkdir -p flask_frontend/uploads
mkdir -p flask_frontend/downloads

# 3. 启动Flask应用
cd flask_frontend
python app.py
```

## 🌐 访问地址

启动成功后，可以通过以下地址访问：

- **本地访问**: http://localhost:5000
- **网络访问**: http://0.0.0.0:5000

## 📋 系统要求

- **Python**: 3.8或更高版本
- **操作系统**: Windows/Linux/macOS
- **内存**: 推荐2GB以上
- **磁盘空间**: 100MB以上

## 📁 目录结构

```
flask_frontend/
├── app.py              # Flask主应用
├── requirements.txt    # Python依赖
├── templates/          # HTML模板
│   ├── base.html      # 基础模板
│   ├── index.html     # 首页
│   ├── upload.html    # 上传页面
│   └── process.html   # 处理页面
├── static/            # 静态文件
├── uploads/           # 上传文件存储
└── downloads/         # 下载文件存储
```

## ⚙️ 配置说明

### 应用配置
- **端口**: 5000
- **调试模式**: 开启
- **最大文件大小**: 16MB
- **支持文件格式**: .xlsx, .xls

### 后端配置
- **FastAPI地址**: http://localhost:8000
- **超时设置**: 5分钟

## 🔧 常见问题

### 1. 端口被占用
```bash
# 查看端口占用
netstat -ano | findstr :5000  # Windows
lsof -i :5000                 # Linux/macOS

# 修改端口 (在app.py中)
app.run(debug=True, host='0.0.0.0', port=5001)
```

### 2. 依赖安装失败
```bash
# 使用国内镜像
pip install -r flask_frontend/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 或者升级pip
python -m pip install --upgrade pip
```

### 3. 后端连接失败
- 确保FastAPI后端已启动 (http://localhost:8000)
- 检查防火墙设置
- 验证网络连接

### 4. 文件上传失败
- 检查文件大小是否超过16MB
- 确认文件格式为.xlsx或.xls
- 验证uploads目录权限

## 🔗 接口依赖关系

```
Flask前端 (端口5000) ←→ FastAPI后端 (端口8000)
     ↓                        ↓
用户界面交互              实际业务逻辑处理
```

### 接口映射

| Flask路由 | FastAPI接口 | 功能 |
|-----------|------------|------|
| `/api/generate_summary` | `/finance/summary/generate` | 数据汇总 |
| `/api/generate_database` | `/finance/database/generate` | 结构化数据库 |
| `/api/generate_visualization` | `/finance/visualization/generate` | 数据可视化 |
| `/api/generate_reporting` | `/finance/reporting/generate` | 智能报告 |
| `/api/execute_workflow` | `/finance/workflow/execute` | 一体化工作流 |

## 📝 日志说明

Flask应用会输出详细的日志信息：
- **INFO**: 正常操作信息
- **WARNING**: 警告信息
- **ERROR**: 错误信息

日志包含：
- 文件上传状态
- API调用结果
- 错误详情
- 处理进度

## 🛠️ 开发调试

### 启用调试模式
```python
# 在app.py中
app.run(debug=True)
```

### 查看详细错误
- 浏览器会显示详细的错误堆栈
- 代码修改会自动重启应用

## 🔒 安全注意事项

1. **生产环境部署**:
   - 关闭调试模式: `debug=False`
   - 使用环境变量设置SECRET_KEY
   - 配置HTTPS
   - 限制文件上传大小

2. **文件安全**:
   - 文件名会自动清理 (secure_filename)
   - 只允许指定的文件格式
   - 定期清理临时文件

## 📞 技术支持

如果遇到问题，请检查：
1. Python版本是否符合要求
2. 依赖是否正确安装
3. FastAPI后端是否运行
4. 网络连接是否正常
5. 文件权限是否正确 