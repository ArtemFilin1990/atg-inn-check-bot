#!/usr/bin/env bash
# scripts/bootstrap.sh — создаёт venv и устанавливает зависимости.
# Запускается один раз на чистой машине или после изменения requirements.txt.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv"

echo "==> Создание виртуального окружения в $VENV_DIR"
python3 -m venv "$VENV_DIR"

echo "==> Обновление pip"
"$VENV_DIR/bin/pip" install --upgrade pip

echo "==> Установка зависимостей из requirements.txt"
"$VENV_DIR/bin/pip" install -r "$REPO_ROOT/requirements.txt"

echo ""
echo "Bootstrap завершён. Для активации окружения выполните:"
echo "  source .venv/bin/activate"
