# 内网文件传输服务

一个轻量级的局域网文件传输工具，支持手机和电脑间的快速文件互传。

## 🚀 快速开始

### 方法一：直接运行
```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务（默认8080端口）
python app.py
```

### 方法二：全局命令（推荐）
```bash
# 首次使用需要将项目复制到推荐位置
cp -r . ~/Projects/file_transfer_service

# 启动服务
file-transfer

# 指定端口启动
file-transfer --port 9090
```

访问 `http://localhost:8080` 开始使用。

## ⚙️ 端口配置

### 方法一：命令行参数
```bash
# 指定端口启动
python app.py --port 9090

# 指定监听地址和端口
python app.py --host 127.0.0.1 --port 8081
```

### 方法二：环境变量
```bash
# Linux/macOS
export PORT=9090
python app.py

# Windows
set PORT=9090
python app.py
```

### 方法三：全局命令（最便捷）
```bash
# 使用默认端口
file-transfer

# 指定端口
file-transfer --port 9090

# 指定项目路径
file-transfer /path/to/your/project

# 使用环境变量
FILE_TRANSFER_PATH=/path/to/your/project file-transfer
```

### 端口冲突自动处理
当指定端口被占用时，服务会自动寻找下一个可用端口并提示：
```
⚠️  端口 8080 已被占用，使用端口 8081
```

## ⚡ 服务管理

### Linux/macOS 用户
```bash
# 启动服务（默认8080端口）
./service.sh start

# 启动服务（指定端口）
./service.sh start 9090

# 通过环境变量指定端口
PORT=8081 ./service.sh start

# 停止服务
./service.sh stop

# 重启服务
./service.sh restart

# 查看状态
./service.sh status

# 查看日志
./service.sh logs
```

### Windows 用户
```cmd
# 运行管理脚本
service.bat
```

## 🌐 全局命令安装

### 1. 复制项目到推荐位置
```bash
# 推荐位置
mkdir -p ~/Projects
cp -r /path/to/your/file_transfer_service ~/Projects/
```

### 2. 使用全局命令
```bash
# 启动服务（无需进入项目目录）
file-transfer

# 指定端口
file-transfer --port 9090

# 查看帮助
file-transfer --help
```

### 3. 全局命令选项
```bash
file-transfer [选项] [项目路径]

选项:
  -p, --port PORT    指定服务端口 (默认: 8080)
  --host HOST        指定监听地址 (默认: 0.0.0.0)
  -h, --help         显示帮助信息

环境变量:
  FILE_TRANSFER_PATH    指定项目路径
```

## 📱 使用方法

1. **电脑上传**：拖拽文件到网页上传区域
2. **手机访问**：扫描页面上的二维码
3. **文件传输**：手机可上传下载文件

## 📁 项目结构

```
file_transfer_service/
├── app.py              # 主程序
├── config.json         # 配置文件
├── requirements.txt    # 依赖列表
├── README.md           # 说明文档
├── file-transfer       # 全局命令脚本
├── service.sh          # Linux/macOS管理脚本
├── service.bat         # Windows管理脚本
├── templates/          # 网页模板
├── static/             # 静态资源
├── uploads/            # 上传文件
└── temp/               # 临时目录
```

## ⚠️ 安全提醒

仅限局域网内可信环境使用，不要在公网部署。