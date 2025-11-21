#!/bin/bash

echo "=========================================="
echo "查看完整應用日誌"
echo "=========================================="
echo ""

LOG_FILE="logs/app.log"
PID_FILE="logs/app.pid"

# 檢查日誌文件是否存在
if [ ! -f "$LOG_FILE" ]; then
    echo "❌ 日誌文件不存在: $LOG_FILE"
    echo ""
    echo "應用可能未啟動，請先執行: ./start.sh"
    exit 1
fi

# 檢查應用是否在運行
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "✓ 應用正在運行 (PID: $PID)"
    else
        echo "⚠️  應用似乎已停止 (PID: $PID)"
    fi
else
    echo "⚠️  找不到 PID 文件"
fi

echo ""
echo "日誌文件: $LOG_FILE"
echo "文件大小: $(du -h "$LOG_FILE" | cut -f1)"
echo "=========================================="
echo ""

# 顯示完整日誌
cat "$LOG_FILE"

echo ""
echo "=========================================="
echo "日誌結束"
echo "=========================================="
echo ""
echo "提示："
echo "  ./tail.sh  - 實時查看日誌"
echo "  ./stop.sh  - 停止應用"
echo ""
