#!/bin/bash
# Local dev launcher
# Frontend on :8000, Backend on :5001
# Backend uses local SQLite by default (no Neon needed for testing)

set -e
cd "$(dirname "$0")"

# 后端
if [ ! -d backend/venv ]; then
  cd backend && python3 -m venv venv && cd ..
fi
source backend/venv/bin/activate
pip install -q -r backend/requirements.txt

# 用 SQLite 后端（如果未配 Neon）
if [ -z "$DATABASE_URL" ]; then
  export DATABASE_URL="sqlite:///$(pwd)/backend/dev.db"
  echo "[dev] Using SQLite: $DATABASE_URL (no Neon needed)"
fi

# 启动后端
cd backend
nohup python app.py > /tmp/hua-backend.log 2>&1 &
BACKEND_PID=$!
echo "backend PID: $BACKEND_PID"
cd ..

# 启动前端
cd frontend
nohup python3 -m http.server 8000 > /tmp/hua-frontend.log 2>&1 &
FRONTEND_PID=$!
echo "frontend PID: $FRONTEND_PID"
cd ..

sleep 2

echo ""
echo "============================================"
echo "  hua-web 本地开发环境已启动"
echo "============================================"
echo "前端:     http://127.0.0.1:8000"
echo "后端 API: http://127.0.0.1:5001"
echo "后端日志: tail -f /tmp/hua-backend.log"
echo "前端日志: tail -f /tmp/hua-frontend.log"
echo ""
echo "停止:    pkill -f 'http.server 8000'; pkill -f 'python app.py'"
echo "============================================"
