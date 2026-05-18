#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
FINAL_ROOT_DEFAULT=$(CDPATH= cd -- "${SCRIPT_DIR}/../.." && pwd)
CONFIG_FILE="${RAG_PIPELINE_CONFIG:-${FINAL_ROOT_DEFAULT}/.config/rag-pipeline.local.conf}"

error_exit() {
    echo "Ошибка: $1" >&2
    exit 1
}

info() {
    echo "[pipeline] $1"
}

require_file() {
    [ -f "$1" ] || error_exit "$2: $1"
}

require_dir() {
    [ -d "$1" ] || error_exit "$2: $1"
}

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || error_exit "команда не найдена: $1"
}

to_win_path() {
    if command -v cygpath >/dev/null 2>&1; then
        cygpath -am "$1"
    else
        printf '%s\n' "$1"
    fi
}

load_config() {
    [ -f "$CONFIG_FILE" ] || error_exit "конфиг не найден: $CONFIG_FILE"

    # shellcheck disable=SC1090
    . "$CONFIG_FILE"

    : "${FINAL_ROOT:?FINAL_ROOT не задан}"
    : "${PROJECT_ROOT:?PROJECT_ROOT не задан}"
    : "${WIKI_CODE_DIR:?WIKI_CODE_DIR не задан}"
    : "${WIKI_SCRIPT:?WIKI_SCRIPT не задан}"
    : "${WIKI_DIR:?WIKI_DIR не задан}"
    : "${AI_CONFIG:?AI_CONFIG не задан}"
    : "${PASDOC_PROG:?PASDOC_PROG не задан}"
    : "${XMLSTARLET_BIN:?XMLSTARLET_BIN не задан}"
    : "${JQ_BIN:?JQ_BIN не задан}"
    : "${MARKDOWN_RAG_DIR:?MARKDOWN_RAG_DIR не задан}"
    : "${MILVUS_COMPOSE_FILE:?MILVUS_COMPOSE_FILE не задан}"
    : "${UV_EXE:?UV_EXE не задан}"
    : "${LOG_DIR:?LOG_DIR не задан}"
    : "${LAST_WIKI_DIR_FILE:?LAST_WIKI_DIR_FILE не задан}"
    : "${CACHE_DIR:?CACHE_DIR не задан}"
    : "${MARKDOWN_RAG_WRAPPER_DIR:?MARKDOWN_RAG_WRAPPER_DIR не задан}"
    : "${MARKDOWN_RAG_WRAPPER_SERVER:?MARKDOWN_RAG_WRAPPER_SERVER не задан}"
}

start_milvus_if_needed() {
    if [ "${AUTO_START_MILVUS:-true}" != "true" ]; then
        info "AUTO_START_MILVUS=false, пропускаю запуск Docker Compose"
        return 0
    fi

    require_cmd docker
    require_file "$MILVUS_COMPOSE_FILE" "docker-compose.yml для Milvus не найден"

    info "Запускаю/проверяю Milvus через Docker Compose"
    docker compose -f "$MILVUS_COMPOSE_FILE" up -d

    container_name="${MILVUS_CONTAINER_NAME:-milvus-standalone}"
    timeout_seconds="${MILVUS_HEALTH_TIMEOUT_SECONDS:-120}"
    elapsed=0

    while [ "$elapsed" -lt "$timeout_seconds" ]; do
        status=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_name" 2>/dev/null || true)

        if [ "$status" = "healthy" ] || [ "$status" = "running" ]; then
            info "Milvus готов: ${container_name} (${status})"
            return 0
        fi

        sleep 2
        elapsed=$((elapsed + 2))
    done

    docker compose -f "$MILVUS_COMPOSE_FILE" ps || true
    error_exit "Milvus не стал healthy за ${timeout_seconds} секунд"
}

prepare_output_dirs() {
    mkdir -p "$LOG_DIR"
    mkdir -p "$CACHE_DIR"
    mkdir -p "$(dirname "$LAST_WIKI_DIR_FILE")"

    if [ "${CLEAN_WIKI_DIR:-true}" = "true" ]; then
        info "Очищаю WIKI_DIR: $WIKI_DIR"
        rm -rf "$WIKI_DIR"
    fi

    mkdir -p "$WIKI_DIR"
}

run_wiki_generation() {
    require_dir "$PROJECT_ROOT" "PROJECT_ROOT не найден"
    require_dir "$WIKI_CODE_DIR" "WIKI_CODE_DIR не найден"
    require_file "$WIKI_SCRIPT" "wiki script не найден"
    require_file "$AI_CONFIG" "AI_CONFIG не найден"
    require_file "$PASDOC_PROG" "PASDOC_PROG не найден"
    require_file "$XMLSTARLET_BIN" "XMLSTARLET_BIN не найден"
    require_file "$JQ_BIN" "JQ_BIN не найден"
    require_dir "$MARKDOWN_RAG_WRAPPER_DIR" "MARKDOWN_RAG_WRAPPER_DIR не найден"
    require_file "$MARKDOWN_RAG_WRAPPER_SERVER" "MARKDOWN_RAG_WRAPPER_SERVER не найден"

    now=$(date +%Y-%m-%d_%H-%M-%S)
    WIKI_LOG="${LOG_DIR}/wiki-build-${now}.log"

    info "Генерирую Markdown wiki"
    info "WIKI_DIR: $WIKI_DIR"
    info "Лог wiki: $WIKI_LOG"

    (
        cd "$WIKI_CODE_DIR"
        PATH="$(dirname "$JQ_BIN"):$WIKI_CODE_DIR:$PATH" \
        AI_CONFIG="$AI_CONFIG" \
        PROJECT_ROOT="$PROJECT_ROOT" \
        WIKI_DIR="$WIKI_DIR" \
        PASDOC_PROG="$PASDOC_PROG" \
        XMLSTARLET_BIN="$XMLSTARLET_BIN" \
        JQ_BIN="$JQ_BIN" \
        CACHE_DIR="$CACHE_DIR" \
        sh "$WIKI_SCRIPT"
    ) 2>&1 | tee "$WIKI_LOG"

    [ -d "$WIKI_DIR" ] || error_exit "созданная wiki-директория не найдена: $WIKI_DIR"
    [ -f "$WIKI_DIR/Home.md" ] || error_exit "Home.md не найден в wiki-директории: $WIKI_DIR"

    printf '%s\n' "$WIKI_DIR" > "$LAST_WIKI_DIR_FILE"
    info "Wiki создана: $WIKI_DIR"
}

index_wiki() {
    require_dir "$MARKDOWN_RAG_DIR" "MARKDOWN_RAG_DIR не найден"
    require_file "$UV_EXE" "uv.exe не найден"
    require_dir "$WIKI_DIR" "WIKI_DIR не найден"

    WIKI_DIR_WIN=$(to_win_path "$WIKI_DIR")
    recursive_flag="--no-recursive"
    [ "${RAG_RECURSIVE:-false}" = "true" ] && recursive_flag="--recursive"

    force_flag=""
    [ "${RAG_FORCE_REINDEX:-true}" = "true" ] && force_flag="--force"

    now=$(date +%Y-%m-%d_%H-%M-%S)
    INDEX_LOG="${LOG_DIR}/rag-index-${now}.log"

    info "Индексирую wiki в markdown-rag-mcp"
    info "Лог index: $INDEX_LOG"

    (
    cd "$MARKDOWN_RAG_DIR"
    PYTHONIOENCODING="utf-8" \
    PYTHONUTF8="1" \
    UV_LINK_MODE="copy" \
    "$UV_EXE" run markdown-rag-mcp index \
        --index-dir "$WIKI_DIR_WIN" \
        $recursive_flag \
        $force_flag
    ) 2>&1 | tee "$INDEX_LOG"

    if grep -q "Directory indexing complete: .* success, 0 failed" "$INDEX_LOG"; then
        info "Индексация завершена без ошибок"
    elif grep -q "Files Failed.*│[[:space:]]*0[[:space:]]*│" "$INDEX_LOG"; then
        info "Индексация завершена без ошибок"
    elif grep -q '"failed_files"[[:space:]]*:[[:space:]]*0' "$INDEX_LOG"; then
        info "Индексация завершена без ошибок"
    else
        error_exit "индексация не подтвердила 0 failed files. Лог: $INDEX_LOG"
    fi
}

check_rag_search() {
    query="${RAG_TEST_QUERY:-FindBucket}"
    threshold="${RAG_SEARCH_THRESHOLD:-0.1}"
    limit="${RAG_SEARCH_LIMIT:-1}"

    now=$(date +%Y-%m-%d_%H-%M-%S)
    SEARCH_LOG="${LOG_DIR}/rag-search-check-${now}.log"

    info "Контрольный RAG search: ${query}"

    (
    cd "$MARKDOWN_RAG_DIR"
    PYTHONIOENCODING="utf-8" \
    PYTHONUTF8="1" \
    UV_LINK_MODE="copy" \
    "$UV_EXE" run markdown-rag-mcp search "$query" \
        --limit "$limit" \
        --threshold "$threshold" \
        --include-metadata \
        --format json
    ) 2>&1 | tee "$SEARCH_LOG"

    grep -q '"results"' "$SEARCH_LOG" || error_exit "контрольный search не вернул JSON results. Лог: $SEARCH_LOG"

    if grep -q '"results"[[:space:]]*:[[:space:]]*\[\]' "$SEARCH_LOG"; then
        error_exit "контрольный search вернул пустой results. Лог: $SEARCH_LOG"
    fi

    info "Контрольный search завершён. Лог: $SEARCH_LOG"
}

main() {
    load_config
    prepare_output_dirs

    info "CONFIG_FILE: $CONFIG_FILE"
    info "FINAL_ROOT: $FINAL_ROOT"
    info "PROJECT_ROOT: $PROJECT_ROOT"
    info "WIKI_DIR: $WIKI_DIR"

    start_milvus_if_needed
    run_wiki_generation
    index_wiki
    check_rag_search

    echo ""
    echo "Готово."
    echo "Wiki: $WIKI_DIR"
    echo "Last wiki marker: $LAST_WIKI_DIR_FILE"
    echo "RAG backend: $MARKDOWN_RAG_DIR"
    echo "OpenCode MCP wrapper: $MARKDOWN_RAG_WRAPPER_DIR"
}

main "$@"