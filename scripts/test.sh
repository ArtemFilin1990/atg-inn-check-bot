#!/usr/bin/env bash
# scripts/test.sh — запускает набор тестов через pytest.
# Требует предварительного выполнения scripts/bootstrap.sh.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv"

if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "ERROR: виртуальное окружение не найдено. Запустите сначала scripts/bootstrap.sh" >&2
    exit 1
fi

echo "==> Запуск тестов"
"$VENV_DIR/bin/pytest" "$@"
