#!/bin/bash

echo "========================================"
echo "Facebook 貼文發布到 WordPress 工具"
echo "========================================"
echo ""

# 檢查 Python
if ! command -v python3 &> /dev/null
then
    echo "錯誤: 未找到 Python 3"
    echo "請先安裝 Python 3.8 或更高版本"
    exit 1
fi

echo "✓ Python 版本: $(python3 --version)"

# 檢查 ChromeDriver
if ! command -v chromedriver &> /dev/null
then
    echo "⚠ 警告: 未找到 ChromeDriver"
    echo "請使用以下命令安裝:"
    echo "  macOS: brew install chromedriver"
    echo "  其他: 訪問 https://chromedriver.chromium.org/downloads"
    echo ""
fi

# 檢查是否已安裝依賴
if [ ! -d "venv" ]; then
    echo "首次運行，正在創建虛擬環境..."
    python3 -m venv venv
    source venv/bin/activate
    echo "正在安裝依賴..."
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo ""

# 定義端口號（與 app.py 中的 PORT 保持一致）
PORT=8081
URL="http://localhost:${PORT}"

# 檢查端口是否被佔用
if lsof -ti:${PORT} > /dev/null 2>&1; then
    echo "⚠️  警告: 端口 ${PORT} 已被佔用"
    echo ""
    echo "正在停止舊進程..."
    ./stop.sh
    echo ""
    echo "等待 2 秒後重新啟動..."
    sleep 2
fi

echo "正在啟動應用..."
echo ""

# 創建日誌目錄
LOG_DIR="logs"
mkdir -p $LOG_DIR

# 日誌文件路徑
LOG_FILE="$LOG_DIR/app.log"
PID_FILE="$LOG_DIR/app.pid"

# 清空舊日誌（保留最近的日誌）
if [ -f "$LOG_FILE" ]; then
    # 如果日誌文件大於 10MB，備份並清空
    LOG_SIZE=$(wc -c < "$LOG_FILE" 2>/dev/null || echo 0)
    if [ $LOG_SIZE -gt 10485760 ]; then
        mv "$LOG_FILE" "$LOG_DIR/app.log.old"
        echo "舊日誌已備份到 app.log.old"
    fi
fi

# 在後台啟動 Flask 應用，輸出重定向到日誌文件
# 使用 -u 參數禁用 Python 輸出緩衝，確保 print 語句立即寫入日誌
nohup python3 -u app.py > "$LOG_FILE" 2>&1 &
APP_PID=$!

# 保存 PID
echo $APP_PID > "$PID_FILE"

# 等待應用啟動（等待 3 秒）
echo "等待應用啟動..."
sleep 3

# 檢查應用是否成功啟動
if ps -p $APP_PID > /dev/null 2>&1; then
    echo ""
    echo "✓ 應用啟動成功！"
    echo "  PID: $APP_PID"
    echo "  日誌文件: $LOG_FILE"
    echo ""
    echo "✓ 正在打開 Chrome 瀏覽器..."
    echo ""

    # 打開 Chrome 瀏覽器
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        open -a "Google Chrome" "$URL" 2>/dev/null || open "$URL"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        google-chrome "$URL" 2>/dev/null || chromium-browser "$URL" 2>/dev/null || xdg-open "$URL"
    else
        # Windows (Git Bash)
        start chrome "$URL" 2>/dev/null || start "$URL"
    fi

    echo "✓ Chrome 已打開，訪問地址: $URL"
    echo ""
    echo "=========================================="
    echo "應用已在背景運行"
    echo "=========================================="
    echo ""
    echo "使用以下命令："
    echo "  ./tail.sh     - 實時查看日誌"
    echo "  ./logs.sh     - 查看完整日誌"
    echo "  ./stop.sh     - 停止應用"
    echo ""
else
    echo "❌ 應用啟動失敗"
    echo ""
    echo "請查看日誌文件: $LOG_FILE"
    cat "$LOG_FILE"
    exit 1
fi
