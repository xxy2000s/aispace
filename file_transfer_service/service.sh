#!/bin/bash
# 文件传输服务管理脚本

SERVICE_NAME="file-transfer-service"
PID_FILE="/tmp/file-transfer.pid"
LOG_FILE="/tmp/file-transfer.log"
DEFAULT_PORT=8080

# 获取端口参数
PORT=${PORT:-$DEFAULT_PORT}

start_service() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "❌ 服务已在运行 (PID: $PID)"
            return 1
        else
            rm -f "$PID_FILE"
        fi
    fi
    
    echo "🚀 启动文件传输服务 (端口: $PORT)..."
    nohup python app.py --port $PORT > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    
    sleep 2
    if ps -p $(cat "$PID_FILE") > /dev/null 2>&1; then
        echo "✅ 服务启动成功 (PID: $(cat "$PID_FILE"))"
        echo "📝 日志文件: $LOG_FILE"
        echo "🌐 访问地址: http://localhost:$PORT"
    else
        echo "❌ 服务启动失败"
        rm -f "$PID_FILE"
        return 1
    fi
}

stop_service() {
    if [ ! -f "$PID_FILE" ]; then
        echo "❌ 服务未运行"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "🛑 停止服务 (PID: $PID)..."
        kill "$PID"
        sleep 2
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "⚠️  强制终止服务..."
            kill -9 "$PID"
        fi
        rm -f "$PID_FILE"
        echo "✅ 服务已停止"
    else
        echo "❌ 服务进程不存在"
        rm -f "$PID_FILE"
    fi
}

status_service() {
    if [ ! -f "$PID_FILE" ]; then
        echo "⭕ 服务未运行"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        # 从日志中提取端口信息
        if [ -f "$LOG_FILE" ]; then
            PORT_INFO=$(grep -o "端口: [0-9]*" "$LOG_FILE" | tail -1 | cut -d' ' -f2)
            if [ -n "$PORT_INFO" ]; then
                PORT=$PORT_INFO
            fi
        fi
        echo "✅ 服务正在运行 (PID: $PID, 端口: $PORT)"
        echo "🌐 访问地址: http://localhost:$PORT"
        echo "📝 日志文件: $LOG_FILE"
    else
        echo "❌ 服务进程已停止 (PID文件存在但进程不存在)"
        rm -f "$PID_FILE"
        return 1
    fi
}

restart_service() {
    echo "🔄 重启服务..."
    stop_service
    sleep 2
    start_service
}

view_logs() {
    if [ ! -f "$LOG_FILE" ]; then
        echo "❌ 日志文件不存在"
        return 1
    fi
    
    echo "📖 查看服务日志 (按 Ctrl+C 退出):"
    tail -f "$LOG_FILE"
}

show_help() {
    echo "文件传输服务管理脚本"
    echo ""
    echo "用法: $0 {start|stop|restart|status|logs} [端口]"
    echo ""
    echo "命令说明:"
    echo "  start [端口]   - 启动服务（可指定端口，默认8080）"
    echo "  stop           - 停止服务"
    echo "  restart        - 重启服务"
    echo "  status         - 查看服务状态"
    echo "  logs           - 查看实时日志"
    echo ""
    echo "环境变量:"
    echo "  PORT=8081 $0 start  # 使用8081端口启动"
    echo ""
    echo "示例:"
    echo "  $0 start           # 使用默认端口8080启动"
    echo "  $0 start 9090      # 使用9090端口启动"
    echo "  PORT=8081 $0 start # 通过环境变量指定端口"
    echo "  $0 status          # 查看状态"
    echo "  $0 logs            # 查看日志"
}

# 解析命令行参数
case "$1" in
    start)
        if [ -n "$2" ] && [[ "$2" =~ ^[0-9]+$ ]]; then
            PORT=$2
        fi
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        status_service
        ;;
    logs)
        view_logs
        ;;
    *)
        show_help
        exit 1
        ;;
esac