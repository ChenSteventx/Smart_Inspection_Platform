# Smart Inspection Platform

智能巡检平台 - 集成热成像分析、TDMS数据处理、浏览器控制和知识图谱检索的综合性平台

## 🚀 快速开始

### 环境要求
- Python 3.12+
- Node.js 16+ (可选，用于BrowserGap功能)
- MySQL 8.0+ (用于知识图谱功能)

### 一键环境配置

#### Windows用户 (推荐)
```bash
# PowerShell版本 (推荐，支持彩色输出)
.\setup_sip.ps1

# 或使用批处理版本
.\setup_sip.bat
```

#### 手动配置
```bash
# 1. 创建虚拟环境
python -m venv sip_env

# 2. 激活虚拟环境
# Windows:
sip_env\Scripts\activate.bat
# Linux/macOS:
source sip_env/bin/activate

# 3. 安装Python依赖
pip install -r requirements.txt

# 4. 安装Node.js依赖 (可选)
npm install
```

### 启动应用

#### 快速启动
```bash
# 使用快速启动脚本
.\start_sip.bat
```

#### 手动启动
```bash
# 1. 激活虚拟环境
sip_env\Scripts\activate.bat

# 2. 启动应用
python app.py

# 3. 访问应用
# http://localhost:5001
```

## 📁 项目结构

```
Smart_Inspection_Platform/
├── api/                    # API路由模块
│   ├── __init__.py
│   ├── browsergap_routes.py
│   ├── tdms_routes.py
│   ├── thermal_routes.py
│   └── knowledge_routes.py
├── services/               # 业务服务模块
│   ├── __init__.py
│   ├── browsergap_service.py
│   ├── tdms_service.py
│   ├── thermal_service.py
│   └── knowledge_service.py
├── config/                 # 配置模块
│   ├── __init__.py
│   ├── settings.py
│   └── database.py
├── external/               # 外部工具
│   └── temperReader/       # DJI热成像工具
├── data/                   # 数据文件
├── uploads/               # 上传文件目录
├── utils/                 # 工具函数
├── sip_env/              # 虚拟环境 (新名称)
├── app.py                # 主应用
├── requirements.txt      # Python依赖
├── package.json         # Node.js依赖
├── setup_sip.bat       # 环境配置脚本
├── setup_sip.ps1       # PowerShell配置脚本
├── start_sip.bat       # 快速启动脚本
└── README.md           # 项目文档
```

## 🔧 虚拟环境管理

### 新命名规范
- **虚拟环境名称**: `sip_env` (Smart Inspection Platform Environment)
- **优势**: 简洁、易识别、符合项目特点

### 虚拟环境操作
```bash
# 创建环境
python -m venv sip_env

# 激活环境
sip_env\Scripts\activate.bat    # Windows
source sip_env/bin/activate     # Linux/macOS

# 停用环境
deactivate

# 删除环境
rmdir /s sip_env               # Windows
rm -rf sip_env                 # Linux/macOS
```

## 🌐 功能模块

### 1. TDMS数据处理服务
- **端点**: `/api/upload-tdms`, `/api/tdms-status`, `/api/convert-to-excel`
- **功能**: TDMS文件解析、可视化、Excel转换
- **服务文件**: `services/tdms_service.py`

### 2. 热成像分析服务  
- **端点**: `/api/upload-thermal-image`, `/api/thermal-analysis`
- **功能**: 热成像图片处理、温度提取、预警检测
- **工具集成**: DJI IRP热成像SDK
- **服务文件**: `services/thermal_service.py`

### 3. BrowserGap浏览器控制
- **端点**: `/api/browsergap/start`, `/api/browsergap/stop`
- **功能**: 远程浏览器控制、网页交互
- **端口**: 8081
- **服务文件**: `services/browsergap_service.py`

### 4. 知识图谱检索
- **端点**: `/api/search`, `/api/hot-searches`
- **功能**: 中文分词、智能检索、MySQL查询
- **依赖**: jieba分词、pymysql
- **服务文件**: `services/knowledge_service.py`

## ⚙️ 配置说明

### DJI IRP工具配置
```python
# config/settings.py
DJI_IRP_PATH = "external/temperReader/dji_thermal_sdk_v1.5_20240507/sample/bin/windows/release_x64/dji_irp.exe"
```

### 数据库配置
```python
# config/database.py
MYSQL_CONFIG = {
    'host': '127.0.0.1',
    'database': 'school',
    'user': 'root',
    'password': '123456'
}
```

## 🚦 健康检查

访问以下端点验证服务状态：
- **应用健康**: http://localhost:5001/api/health
- **TDMS服务**: http://localhost:5001/api/tdms-status
- **BrowserGap**: http://localhost:8081/health

## 📦 镜像源配置

### Python包镜像源
```bash
# 清华源 (推荐中国大陆用户)
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple

# 配置脚本会自动询问是否使用镜像源
```

### Node.js包镜像源
```bash
# 淘宝镜像 (推荐中国大陆用户)
npm install --registry=https://registry.npmmirror.com

# 配置脚本会自动询问是否使用镜像源
```

## 🛠️ 开发指南

### 添加新功能模块
1. 在 `services/` 创建新服务类
2. 在 `api/` 创建对应路由蓝图
3. 在 `app.py` 注册新蓝图
4. 更新配置和文档

### 修改现有功能
每个功能模块的文件位置：

| 功能 | 服务文件 | 路由文件 | 相关配置 |
|------|----------|----------|----------|
| TDMS处理 | `services/tdms_service.py` | `api/tdms_routes.py` | `config/settings.py` |
| 热成像分析 | `services/thermal_service.py` | `api/thermal_routes.py` | DJI IRP配置 |
| 浏览器控制 | `services/browsergap_service.py` | `api/browsergap_routes.py` | BrowserGap设置 |
| 知识图谱 | `services/knowledge_service.py` | `api/knowledge_routes.py` | MySQL配置 |

## 🐛 故障排除

### 常见问题

1. **虚拟环境无法激活**
   ```bash
   # 解决方案：重新创建环境
   rmdir /s sip_env
   python -m venv sip_env
   ```

2. **DJI IRP工具未找到**
   ```bash
   # 检查工具路径
   dir external\temperReader\dji_thermal_sdk_v1.5_20240507\sample\bin\windows\release_x64\dji_irp.exe
   ```

3. **MySQL连接失败**
   ```bash
   # 检查MySQL服务状态
   net start mysql
   ```

4. **Node.js依赖安装失败**
   ```bash
   # 清理缓存重试
   npm cache clean --force
   npm install
   ```

### 环境重置
```bash
# 完全重置环境
rmdir /s sip_env
rmdir /s node_modules
python -m venv sip_env
sip_env\Scripts\activate.bat
pip install -r requirements.txt
npm install
```

## 📋 待完成事项

### 必需操作
- [ ] 添加停用词文件: `data/cn_stopwords.txt`
- [ ] 配置MySQL数据库和表结构
- [ ] 添加示例PDF文件: `data/A.pdf`

### 可选优化
- [ ] 添加单元测试
- [ ] 完善错误处理
- [ ] 性能优化
- [ ] 容器化部署
