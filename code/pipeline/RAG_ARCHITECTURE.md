# RAG MVP+ architecture

## Статус

Текущее состояние — рабочий прототип уровня MVP+: wiki-генератор, AI-обогащение, Markdown-RAG разметка, Docker Milvus, semantic search и OpenCode MCP-wrapper подтверждены на контрольных запросах.

Clean pipeline уже выполняет полный маршрут:

```text
исходники Pascal/Delphi
→ Markdown wiki в data/wiki_out/current
→ индексация в markdown-rag-mcp / Milvus
→ контрольный semantic search
```

## Основная цель clean-версии

Сделать систему воспроизводимой:

- все стабильные пути задаются централизованно в `.config/rag-pipeline.local.conf`;
- AI-настройки отделены в `.config/ai-descr.local.conf`;
- wiki всегда создаётся в стабильную папку `data/wiki_out/current`;
- индексация запускается оркестратором, а не руками;
- OpenCode получает только runtime MCP-tool для поиска.

## Pipeline генерации

```text
Pascal/Delphi source
→ PasDoc SimpleXML
→ ai-descr-ai-v3-config-rag-md-v3.sh
→ Obsidian-compatible Markdown wiki
→ markdown-rag-mcp index
→ Docker Milvus vector index
```

## Pipeline runtime-поиска

```text
OpenCode
→ markdown_rag_wrapper MCP
→ markdown-rag-mcp Python API
→ Milvus
→ найденные Markdown-секции
```

## Роли компонентов

### `code/wiki/ai-descr-ai-v3-config-rag-md-v3.sh`

Создаёт Markdown wiki из PasDoc SimpleXML и добавляет RAG-oriented поля:

- `RAG-поисковые ключи`;
- `kind`;
- `id`;
- `source_path`;
- списки `classes`, `methods`, `fields`, `properties`;
- method-level `ID`, `Объявление`, `Видимость`.

Скрипт читает AI-настройки из `AI_CONFIG`, но пути, переданные оркестратором через окружение, имеют приоритет над значениями из `AI_CONFIG`.

Это важно, потому что `.config/ai-descr.local.conf` должен отвечать за AI, а не за layout проекта.

### `tools/markdown-rag-mcp`

Внешний backend. Отвечает за:

- парсинг Markdown;
- chunking;
- embeddings;
- хранение в Milvus;
- semantic search.

Backend не модифицируется нами.

### `code/mcp/markdown-rag-mcp-wrapper`

Наш тонкий MCP-wrapper. Использует Python API backend напрямую, без subprocess.

Чистовые tools:

- `markdown_rag_search`;
- `markdown_rag_reload_engine`;
- `markdown_rag_ping`.

Wrapper не выполняет индексацию и не знает путь к `wiki_out/current`. Он работает с уже подготовленным Milvus-индексом.

### `code/pipeline/build-wiki-rag.sh`

Оркестратор build-процесса:

1. читает `.config/rag-pipeline.local.conf`;
2. очищает `data/wiki_out/current`;
3. запускает/проверяет Milvus;
4. запускает wiki-generator;
5. индексирует wiki через `markdown-rag-mcp`;
6. выполняет контрольный search.

### `code/pipeline/check-rag.sh`

Лёгкая ручная проверка уже построенного индекса.

### OpenCode

OpenCode отвечает за агентную работу и, при необходимости, чтение/редактирование файлов собственными built-in tools.

### pasls MCP

Read-only code-intelligence слой:

- diagnostics;
- hover;
- definition.

RAG не заменяет pasls. RAG находит структурную сущность и metadata; точный код/тела методов достаются через OpenCode/pasls/filesystem.

## Почему индексация не MCP-tool

Индексация относится к build pipeline, а не к runtime-диалогу агента.

Причины:

- агент не должен случайно переиндексировать не ту папку;
- индексация должна происходить сразу после генерации wiki;
- путь wiki должен контролироваться оркестратором;
- runtime MCP должен быть read-only и предсказуемым.

## filesystem MCP

`filesystem MCP` считается optional.

Если OpenCode built-in tools уже умеют читать и редактировать нужные файлы, чистовая конфигурация может состоять только из:

- `pasls`;
- `markdown_rag_wrapper`.

Filesystem MCP имеет смысл оставить только если нужен явный дополнительный доступ к папкам или совместимость с workflow, который ожидает MCP filesystem tools.

## Что не входит в clean MVP

- старый `MCP-Markdown-RAG` на Milvus Lite;
- CLI-wrapper через subprocess;
- subprocess diagnostic tools;
- JSON/JSONL chunk формат;
- graph-ready relations;
- rerank;
- автоматическое редактирование `opencode.json`;
- MCP-tool для индексации;
- ручной выбор timestamp-папки wiki.

## Текущие ограничения

### Semantic search по идентификаторам

Для Pascal/Delphi identifiers часто нужен низкий threshold:

```text
0.1
```

Идентификаторные запросы полезно формулировать с контекстом:

```text
TGpStringHash FindBucket
Create constructor TGpStringHash
lock free queue
```

### Неполные описания

Если `AI_ENRICH_METHODS=false`, method-level секции могут содержать `Нет описания`. Это не ошибка RAG pipeline, а выбранный режим экономии запросов.

Для демонстрации method-level качества можно включить:

```sh
AI_ENRICH_METHODS="true"
```

### Логи и Unicode

На Windows для `markdown-rag-mcp` нужно выставлять UTF-8 окружение:

```sh
PYTHONIOENCODING="utf-8"
PYTHONUTF8="1"
UV_LINK_MODE="copy"
```

Это нужно из-за вывода emoji и rich-таблиц.
