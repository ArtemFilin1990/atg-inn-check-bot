#!/usr/bin/env bash
# scripts/run.sh — запускает сервер в dev-режиме.
# Требует предварительного выполнения scripts/bootstrap.sh и наличия .env.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv"

if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "ERROR: виртуальное окружение не найдено. Запустите сначала scripts/bootstrap.sh" >&2
    exit 1
fi

# Загружаем переменные из .env, если файл существует
if [ -f "$REPO_ROOT/.env" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$REPO_ROOT/.env"
    set +a
fi

PORT="${PORT:-3000}"
HOST="${HOST:-0.0.0.0}"

echo "==> Запуск uvicorn app.main:app на $HOST:$PORT"
"$VENV_DIR/bin/uvicorn" app.main:app --host "$HOST" --port "$PORT" --reload
