# Pascal/Delphi Wiki + RAG pipeline

Эта папка содержит clean-оркестратор для рабочего прототипа: из Pascal/Delphi-кода генерируется Obsidian-compatible Markdown wiki, затем wiki индексируется в `markdown-rag-mcp`, после чего OpenCode получает MCP-tool для поиска по RAG.

Текущий уровень системы — MVP+: есть wiki-генерация, AI-обогащение, RAG-разметка Markdown, Docker Milvus, semantic search и MCP-wrapper для OpenCode.

## Рекомендуемая структура

```text
finalversion/
  .config/
    ai-descr.local.conf              # локальные AI-настройки, API key, модель
    rag-pipeline.local.conf          # центральный конфиг путей и pipeline

  tools/
    bin/                             # jq.exe, mcp-language-server.exe
    pasdoc/                          # PasDoc
    xmlstarlet/                      # xmlstarlet
    pasls/                           # pasls.exe
    markdown-rag-mcp/                # внешний RAG backend

  code/
    wiki/                            # PasDoc/wiki generator
    pipeline/                        # оркестратор и документация
    mcp/markdown-rag-mcp-wrapper/    # наш MCP wrapper для OpenCode
    agent/                           # фрагменты OpenCode config

  data/
    input_project/                   # опциональное место для исходников проекта
    wiki_out/current/                # стабильная текущая Markdown wiki
    logs/                            # логи pipeline
    cache/                           # AI-cache и wrapper logs
```

Основная идея: `tools` — внешние программы, `code` — наш код, `data` — входные/выходные данные и runtime-артефакты, `.config` — локальная конфигурация.

## Требуемые программы

Нужно установить или иметь локально:

- Git;
- Git Bash / MSYS2 shell;
- Docker Desktop + Docker Compose;
- Python, управляемый через `uv`;
- `uv`;
- OpenCode;
- PasDoc;
- xmlstarlet;
- jq;
- `curl`, `awk`, `sed`, `grep`, `find`, `md5sum`, `mktemp`, `cygpath` — обычно уже есть в Git Bash/MSYS2.

## Установка backend `markdown-rag-mcp`

Backend находится в:

```text
finalversion/tools/markdown-rag-mcp
```

Если он ещё не скопирован или не клонирован:

```sh
cd "D:/Works/учёба/вкр/finalversion/tools"
git clone https://github.com/mohllal/markdown-rag-mcp.git
cd markdown-rag-mcp
uv sync
uv pip install mcp
docker compose -f docker/docker-compose.yml up -d
```

`mcp` устанавливается именно в окружение backend-проекта, потому что wrapper запускается через backend `.venv` и использует Python API `markdown-rag-mcp`.

## Настройка `ai-descr.local.conf`

Файл:

```text
finalversion/.config/ai-descr.local.conf
```

В нём должны быть только AI-настройки:

```sh
AI_PROVIDER="openrouter"
OPENROUTER_API_KEY="..."
AI_MODEL="poolside/laguna-m.1:free"

AI_TEMPERATURE="0.1"
AI_MAX_TOKENS="800"

AI_ENRICH_UNITS="true"
AI_ENRICH_CLASSES="false"
AI_ENRICH_METHODS="false"
```

Пути к PasDoc, xmlstarlet, jq, проекту и wiki сюда не кладутся. Их источник — `rag-pipeline.local.conf`.

Если API-ключ был случайно отправлен в чат, репозиторий или лог, его нужно перевыпустить у провайдера.

## Настройка `rag-pipeline.local.conf`

Файл:

```text
finalversion/.config/rag-pipeline.local.conf
```

Пример минимально нужных настроек:

```sh
FINAL_ROOT="D:/Works/учёба/вкр/finalversion"

PROJECT_ROOT="D:/Works/учёба/вкр/GpDelphiUnits_very_mini/src"

WIKI_CODE_DIR="${FINAL_ROOT}/code/wiki"
WIKI_SCRIPT="${WIKI_CODE_DIR}/ai-descr-ai-v3-config-rag-md-v3.sh"
WIKI_DIR="${FINAL_ROOT}/data/wiki_out/current"
AI_CONFIG="${FINAL_ROOT}/.config/ai-descr.local.conf"

PASDOC_PROG="${FINAL_ROOT}/tools/pasdoc/bin/pasdoc.exe"
XMLSTARLET_BIN="${FINAL_ROOT}/tools/xmlstarlet/xmlstarlet-1.6.1/xml.exe"
JQ_BIN="${FINAL_ROOT}/tools/bin/jq.exe"

MARKDOWN_RAG_DIR="${FINAL_ROOT}/tools/markdown-rag-mcp"
MILVUS_COMPOSE_FILE="${MARKDOWN_RAG_DIR}/docker/docker-compose.yml"
UV_EXE="C:/Users/Danii/AppData/Roaming/Python/Python313/Scripts/uv.exe"

MARKDOWN_RAG_WRAPPER_DIR="${FINAL_ROOT}/code/mcp/markdown-rag-mcp-wrapper"
MARKDOWN_RAG_WRAPPER_SERVER="${MARKDOWN_RAG_WRAPPER_DIR}/server.py"

LOG_DIR="${FINAL_ROOT}/data/logs"
LAST_WIKI_DIR_FILE="${FINAL_ROOT}/data/wiki_out/last_wiki_dir.txt"
CACHE_DIR="${FINAL_ROOT}/data/cache/ai-descriptions"

AUTO_START_MILVUS="true"
MILVUS_CONTAINER_NAME="milvus-standalone"
MILVUS_HEALTH_TIMEOUT_SECONDS="120"

CLEAN_WIKI_DIR="true"
RAG_RECURSIVE="false"
RAG_FORCE_REINDEX="true"

RAG_TEST_QUERY="FindBucket"
RAG_SEARCH_LIMIT="1"
RAG_SEARCH_THRESHOLD="0.1"
```

## Проверка конфигурации

Из корня `finalversion`:

```sh
cd "D:/Works/учёба/вкр/finalversion"

sh -n "code/pipeline/build-wiki-rag.sh"
sh -n "code/pipeline/check-rag.sh"

. ".config/rag-pipeline.local.conf"

test -d "$PROJECT_ROOT" && echo "PROJECT_ROOT ok"
test -f "$WIKI_SCRIPT" && echo "WIKI_SCRIPT ok"
test -f "$AI_CONFIG" && echo "AI_CONFIG ok"
test -f "$PASDOC_PROG" && echo "PASDOC ok"
test -f "$XMLSTARLET_BIN" && echo "XMLSTARLET ok"
test -f "$JQ_BIN" && echo "JQ ok"
test -d "$MARKDOWN_RAG_DIR" && echo "MARKDOWN_RAG_DIR ok"
test -f "$MILVUS_COMPOSE_FILE" && echo "MILVUS_COMPOSE_FILE ok"
```

## Полный запуск

Из корня `finalversion`:

```sh
cd "D:/Works/учёба/вкр/finalversion"
sh "code/pipeline/build-wiki-rag.sh"
```

Скрипт выполняет:

1. загрузку центрального конфига;
2. очистку `data/wiki_out/current`;
3. запуск/проверку Docker Milvus;
4. генерацию Markdown wiki;
5. индексацию wiki в `markdown-rag-mcp`;
6. контрольный search.

Успешный финал выглядит так:

```text
[pipeline] Индексация завершена без ошибок
[pipeline] Контрольный search завершён.

Готово.
Wiki: D:/Works/учёба/вкр/finalversion/data/wiki_out/current
Last wiki marker: D:/Works/учёба/вкр/finalversion/data/wiki_out/last_wiki_dir.txt
RAG backend: D:/Works/учёба/вкр/finalversion/tools/markdown-rag-mcp
OpenCode MCP wrapper: D:/Works/учёба/вкр/finalversion/code/mcp/markdown-rag-mcp-wrapper
```

## Проверка RAG вручную

После полного pipeline-запуска:

```sh
cd "D:/Works/учёба/вкр/finalversion"
sh "code/pipeline/check-rag.sh" FindBucket
```

Можно менять запрос:

```sh
sh "code/pipeline/check-rag.sh" "TGpStringHash FindBucket"
sh "code/pipeline/check-rag.sh" "lock free queue"
```

## OpenCode MCP config

Смотрите:

```text
finalversion/code/agent/opencode.fragment.json
```

Wrapper должен запускаться через backend окружение:

```text
uv --directory finalversion/tools/markdown-rag-mcp run python finalversion/code/mcp/markdown-rag-mcp-wrapper/server.py
```

## Runtime MCP tools

В чистовом wrapper оставлены только:

- `markdown_rag_search` — поиск по RAG;
- `markdown_rag_reload_engine` — сброс кэша `RAGEngine`;
- `markdown_rag_ping` — быстрая проверка MCP.

Индексация не является MCP-tool: она выполняется оркестратором после генерации wiki.

## Примечание про предупреждения wiki-generator

Предупреждения вида:

```text
содержит пропущенные описания
```

не означают падение pipeline. Они показывают, что для части сущностей описания не были обогащены. Например, если:

```sh
AI_ENRICH_METHODS="false"
```

то методы могут остаться с `Нет описания`. Для демонстрации качества method-level RAG можно временно включить:

```sh
AI_ENRICH_METHODS="true"
```
