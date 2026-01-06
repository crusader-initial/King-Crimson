#!/bin/bash

set -e  # 遇到错误立即退出

# 获取项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 切换到项目根目录（必需：否则找不到 requirements.txt 和 run.py）
cd "$PROJECT_ROOT"

# 加载环境变量文件（必需：应用需要数据库和 API 配置）
ENV_FILE=".env.beta"
if [ ! -f "$ENV_FILE" ]; then
    ENV_FILE=".env"
    if [ ! -f "$ENV_FILE" ]; then
        echo "错误: .env 文件不存在，请先创建配置文件"
        exit 1
    fi
fi
export $(cat "$ENV_FILE" | grep -v '^#' | xargs)

# 检查 Python（必需：确保能运行应用）
PYTHON_CMD=${PYTHON_CMD:-python3}
if ! command -v "$PYTHON_CMD" &> /dev/null; then
    echo "错误: 未找到 $PYTHON_CMD"
    exit 1
fi

# 安装依赖（必需：应用需要这些包才能运行）
PIP_CMD=${PIP_CMD:-pip3}
$PIP_CMD install -r requirements.txt

# 启动应用（必需：测试环境需要热重载和 DEBUG 日志）
APP_PORT=${APP_PORT:-8080}
$PYTHON_CMD -m uvicorn run:app \
    --host 0.0.0.0 \
    --port $APP_PORT \
    --reload \
    --log-level debug
