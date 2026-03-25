#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
RUN_DIR="$PROJECT_DIR/.run"
BACKEND_LOG="$RUN_DIR/backend.log"
BACKEND_HOST="${APP_BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${APP_BACKEND_PORT:-8000}"
FRONTEND_HOST="${APP_FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${APP_FRONTEND_PORT:-8501}"
BACKEND_URL="http://${BACKEND_HOST}:${BACKEND_PORT}"
FRONTEND_URL="http://${FRONTEND_HOST}:${FRONTEND_PORT}"
BACKEND_PID=""

cleanup() {
    local exit_code=$?

    if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo
        echo "Encerrando backend (PID $BACKEND_PID)..."
        kill "$BACKEND_PID" 2>/dev/null || true
        wait "$BACKEND_PID" 2>/dev/null || true
    fi

    exit "$exit_code"
}

trap cleanup EXIT INT TERM

find_python() {
    if command -v python >/dev/null 2>&1; then
        echo "python"
        return 0
    fi

    if command -v py >/dev/null 2>&1; then
        echo "py -3"
        return 0
    fi

    return 1
}

wait_for_backend() {
    local url="$1"
    local attempts="${2:-60}"

    for ((i = 1; i <= attempts; i++)); do
        if [[ -n "$BACKEND_PID" ]] && ! kill -0 "$BACKEND_PID" 2>/dev/null; then
            echo "O backend encerrou inesperadamente durante a inicialização."
            return 1
        fi

        if python - "$url" <<'PY'
import sys
import urllib.request

url = sys.argv[1]

try:
    with urllib.request.urlopen(url, timeout=2) as response:
        raise SystemExit(0 if response.status == 200 else 1)
except Exception:
    raise SystemExit(1)
PY
        then
            return 0
        fi

        sleep 1
    done

    return 1
}

print_backend_log_hint() {
    if [[ -f "$BACKEND_LOG" ]]; then
        echo
        echo "Últimas linhas do log do backend:"
        tail -n 40 "$BACKEND_LOG" || true
    fi
}

cd "$PROJECT_DIR"
mkdir -p "$RUN_DIR"

BOOTSTRAP_PYTHON="$(find_python || true)"
if [[ -z "$BOOTSTRAP_PYTHON" ]]; then
    echo "Python não encontrado no PATH. Instale o Python 3.10+ antes de rodar este script."
    exit 1
fi

if [[ ! -d "$PROJECT_DIR/.venv" ]]; then
    echo "Ambiente virtual .venv não encontrado. Criando automaticamente..."
    eval "$BOOTSTRAP_PYTHON -m venv \"$PROJECT_DIR/.venv\""
fi

# shellcheck disable=SC1091
source "$PROJECT_DIR/.venv/Scripts/activate"

if ! python - <<'PY'
import fastapi
import httpx
import streamlit
import uvicorn
PY
then
    echo "Dependências principais não encontradas na .venv. Instalando requirements.txt..."
    python -m pip install -r requirements.txt
fi

if [[ ! -f "$PROJECT_DIR/.env" && -f "$PROJECT_DIR/.env.example" ]]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "Arquivo .env criado a partir de .env.example. Revise especialmente a GEMINI_API_KEY antes de usar a geração real."
fi

export APP_API_BACKEND_URL="$BACKEND_URL"

echo "Iniciando backend em $BACKEND_URL ..."
python -m uvicorn backend.app.api:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" --reload >"$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

echo "Aguardando backend ficar disponível..."
if ! wait_for_backend "$BACKEND_URL/health" 60; then
    echo "Não foi possível confirmar a subida do backend em $BACKEND_URL."
    print_backend_log_hint
    exit 1
fi

echo "Backend ativo."
echo "- Health: $BACKEND_URL/health"
echo "- Docs:   $BACKEND_URL/docs"
echo
echo "Abrindo frontend Streamlit em $FRONTEND_URL ..."
echo "Pressione Ctrl+C para encerrar frontend e backend juntos."
echo

python -m streamlit run frontend/streamlit_app.py --server.address "$FRONTEND_HOST" --server.port "$FRONTEND_PORT"

