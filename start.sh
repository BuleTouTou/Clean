#!/usr/bin/env bash

# 房源数据清洗工具（macOS / Linux）启动脚本
set -u

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

export HOUSING_CLEANER_OPEN_BROWSER="${HOUSING_CLEANER_OPEN_BROWSER:-1}"

if ! command -v uv >/dev/null 2>&1; then
    echo "未找到 uv。请先安装 uv：https://docs.astral.sh/uv/getting-started/installation/"
    echo "安装后重新运行：./start.sh"
    exit 1
fi

if [ ! -f "frontend/dist/index.html" ]; then
    echo "未找到前端构建产物。请先执行："
    echo "  cd frontend && bun install && bun run build"
    exit 1
fi

# uv 会读取 .python-version 和 pyproject.toml，自动准备指定 Python 版本及依赖环境。
exec uv run uvicorn backend.app:app --host 127.0.0.1 --port "${HOUSING_CLEANER_PORT:-8765}"
