#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
FINAL_ROOT_DEFAULT=$(CDPATH= cd -- "${SCRIPT_DIR}/../.." && pwd)
CONFIG_FILE="${RAG_PIPELINE_CONFIG:-${FINAL_ROOT_DEFAULT}/.config/rag-pipeline.local.conf}"

[ -f "$CONFIG_FILE" ] || {
    echo "Ошибка: конфиг не найден: $CONFIG_FILE" >&2
    exit 1
}

# shellcheck disable=SC1090
. "$CONFIG_FILE"

: "${MARKDOWN_RAG_DIR:?MARKDOWN_RAG_DIR не задан}"
: "${UV_EXE:?UV_EXE не задан}"

query="${1:-${RAG_TEST_QUERY:-FindBucket}}"
limit="${RAG_SEARCH_LIMIT:-5}"
threshold="${RAG_SEARCH_THRESHOLD:-0.1}"

cd "$MARKDOWN_RAG_DIR"

PYTHONIOENCODING="utf-8" \
PYTHONUTF8="1" \
UV_LINK_MODE="copy" \
"$UV_EXE" run markdown-rag-mcp search "$query" \
    --limit "$limit" \
    --threshold "$threshold" \
    --include-metadata \
    --format json