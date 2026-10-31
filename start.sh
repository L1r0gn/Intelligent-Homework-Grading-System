#!/usr/bin/env bash
# 一键启动（开发模式），等价于：python deploy.py dev
set -e
cd "$(dirname "$0")"

PY=".venv/bin/python"
[ -x "$PY" ] || PY="python3"

exec "$PY" deploy.py dev "$@"
