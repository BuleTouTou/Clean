#!/usr/bin/env bash

# macOS Finder 双击入口；终端用户也可以直接运行 start.sh。
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
exec /bin/bash "$SCRIPT_DIR/start.sh"
