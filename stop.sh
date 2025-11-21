#!/bin/bash

echo "========================================"
echo "停止 Facebook 貼文發布工具"
echo "========================================"
echo ""

PORT=8081

# 查找佔用端口的進程
echo "正在查找佔用端口 ${PORT} 的進程..."
PID=$(lsof -ti:${PORT})

if [ -z "$PID" ]; then
    echo "✓ 沒有進程佔用端口 ${PORT}"
    echo ""

    # 檢查是否有 app.py 進程在運行
    APP_PIDS=$(ps aux | grep "[p]ython.*app.py" | awk '{print $2}')
    if [ -n "$APP_PIDS" ]; then
        echo "發現其他 app.py 進程，正在停止..."
        echo "$APP_PIDS" | while read pid; do
            echo "  停止進程 PID: $pid"
            kill $pid 2>/dev/null
        done
        sleep 1
        echo "✓ 已停止所有 app.py 進程"
    fi
else
    echo "找到進程 PID: $PID"

    # 顯示進程信息
    echo ""
    echo "進程信息:"
    ps -p $PID 2>/dev/null || echo "  (進程信息不可用)"
    echo ""

    # 嘗試優雅停止（SIGTERM）
    echo "正在優雅停止進程..."
    kill $PID 2>/dev/null

    # 等待最多 5 秒
    for i in {1..5}; do
        sleep 1
        if ! kill -0 $PID 2>/dev/null; then
            echo "✓ 進程已成功停止"
            break
        fi
        echo "  等待進程停止... ($i/5)"
    done

    # 如果還在運行，強制停止
    if kill -0 $PID 2>/dev/null; then
        echo "進程未響應，強制停止..."
        kill -9 $PID 2>/dev/null
        sleep 1

        if ! kill -0 $PID 2>/dev/null; then
            echo "✓ 進程已強制停止"
        else
            echo "❌ 無法停止進程"
            exit 1
        fi
    fi
fi

# 清理可能的 Chrome 進程（由 Selenium 啟動的）
echo ""
echo "檢查是否有殘留的 Chrome 進程..."
CHROME_PIDS=$(ps aux | grep "[C]hromeDriver\|[c]hromedriver" | awk '{print $2}')
if [ -n "$CHROME_PIDS" ]; then
    echo "發現殘留的 ChromeDriver 進程，正在清理..."
    echo "$CHROME_PIDS" | while read pid; do
        echo "  停止 ChromeDriver PID: $pid"
        kill $pid 2>/dev/null
    done
    sleep 1
    echo "✓ 已清理 ChromeDriver 進程"
else
    echo "✓ 沒有殘留的 ChromeDriver 進程"
fi

# 最後確認
echo ""
FINAL_CHECK=$(lsof -ti:${PORT})
if [ -z "$FINAL_CHECK" ]; then
    echo "========================================"
    echo "✅ 應用已完全停止"
    echo "========================================"
    echo ""
    echo "端口 ${PORT} 現在可以使用"
    echo "如需重新啟動，請執行: ./start.sh"
    echo ""
else
    echo "========================================"
    echo "⚠️  警告: 端口仍被佔用"
    echo "========================================"
    echo ""
    echo "請手動檢查: lsof -i:${PORT}"
    echo ""
fi
