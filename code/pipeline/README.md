# Pascal/Delphi Wiki + RAG pipeline

Эта папка содержит оркестратор для рабочего прототипа: из Pascal/Delphi-кода генерируется Obsidian-compatible Markdown wiki, затем wiki индексируется в `markdown-rag-mcp`, после чего OpenCode получает MCP-tool для поиска по RAG.

Текущий уровень системы: есть wiki-генерация, AI-обогащение, RAG-разметка Markdown, Docker Milvus, semantic search и MCP-wrapper для OpenCode.

## структура

```text
finalversion/
  .config/
  tools/
  code/
  data/
```

Основная идея: `tools` — внешние программы, `code` — код, `data` — входные/выходные данные и runtime-артефакты, `.config` — локальная конфигурация.

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
AI-настройки. Заполнение можно посмотреть в example и local:

## Настройка `rag-pipeline.local.conf`

Файл:

```text
finalversion/.config/rag-pipeline.local.conf
```

Пример минимально нужных настроек там же.

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

Смотреть:

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

то методы могут остаться с `Нет описания`.:

```sh
AI_ENRICH_METHODS="true"
```
 так же описания всегда отсутствуют для properties
