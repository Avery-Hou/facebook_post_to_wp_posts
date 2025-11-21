#!/bin/bash

echo "=========================================="
echo "應用狀態檢查"
echo "=========================================="
echo ""

PORT=8081
PID_FILE="logs/app.pid"
LOG_FILE="logs/app.log"

# 檢查端口
echo "1. 檢查端口 ${PORT}..."
PORT_PID=$(lsof -ti:${PORT} 2>/dev/null)
if [ -n "$PORT_PID" ]; then
    echo "   ✓ 端口 ${PORT} 正在使用"
    echo "   進程 PID: $PORT_PID"
else
    echo "   ✗ 端口 ${PORT} 未被使用"
fi

echo ""

# 檢查 PID 文件
echo "2. 檢查 PID 文件..."
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    echo "   ✓ PID 文件存在"
    echo "   記錄的 PID: $PID"

    # 檢查進程是否在運行
    if ps -p $PID > /dev/null 2>&1; then
        echo "   ✓ 進程正在運行"

        # 顯示進程信息
        echo ""
        echo "   進程詳情:"
        ps -p $PID | tail -n +2 | sed 's/^/   /'
    else
        echo "   ✗ 進程已停止"
    fi
else
    echo "   ✗ PID 文件不存在"
fi

echo ""

# 檢查日誌文件
echo "3. 檢查日誌文件..."
if [ -f "$LOG_FILE" ]; then
    echo "   ✓ 日誌文件存在"
    echo "   文件大小: $(du -h "$LOG_FILE" | cut -f1)"
    echo "   最後修改: $(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$LOG_FILE" 2>/dev/null || stat -c "%y" "$LOG_FILE" 2>/dev/null)"

    # 顯示最後 5 行日誌
    echo ""
    echo "   最後 5 行日誌:"
    tail -n 5 "$LOG_FILE" | sed 's/^/   /'
else
    echo "   ✗ 日誌文件不存在"
fi

echo ""

# 檢查 app.py 進程
echo "4. 檢查 app.py 進程..."
APP_PIDS=$(ps aux | grep "[p]ython.*app.py" | awk '{print $2}')
if [ -n "$APP_PIDS" ]; then
    echo "   ✓ 找到 app.py 進程:"
    ps aux | grep "[p]ython.*app.py" | sed 's/^/   /'
else
    echo "   ✗ 沒有找到 app.py 進程"
fi

echo ""

# 檢查 ChromeDriver 進程
echo "5. 檢查 ChromeDriver 進程..."
CHROME_PIDS=$(ps aux | grep "[C]hromeDriver\|[c]hromedriver" | awk '{print $2}')
if [ -n "$CHROME_PIDS" ]; then
    echo "   ⚠️  發現 ChromeDriver 進程:"
    ps aux | grep "[C]hromeDriver\|[c]hromedriver" | sed 's/^/   /'
else
    echo "   ✓ 沒有殘留的 ChromeDriver 進程"
fi

echo ""
echo "=========================================="

# 總結狀態
echo ""
if [ -n "$PORT_PID" ] && [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "狀態: ✅ 應用正常運行"
        echo ""
        echo "訪問地址: http://localhost:${PORT}"
        echo ""
        echo "可用命令："
        echo "  ./tail.sh   - 實時查看日誌"
        echo "  ./logs.sh   - 查看完整日誌"
        echo "  ./stop.sh   - 停止應用"
    else
        echo "狀態: ⚠️  應用可能異常（端口被佔用但 PID 不匹配）"
        echo ""
        echo "建議執行: ./stop.sh"
    fi
else
    echo "狀態: ❌ 應用未運行"
    echo ""
    echo "啟動應用: ./start.sh"
fi

echo ""
