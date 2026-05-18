# markdown-rag-mcp-wrapper

`markdown-rag-mcp-wrapper` — тонкий MCP stdio-wrapper для OpenCode, который даёт агенту доступ к поиску по уже построенному Markdown RAG-индексу.

Wrapper не занимается генерацией wiki, индексацией, embeddings, Milvus и rerank. Эти задачи выполняются build pipeline и backend `markdown-rag-mcp`.

## Назначение

Runtime-цепочка поиска:

```text
OpenCode
→ markdown_rag_wrapper MCP
→ markdown-rag-mcp Python API
→ Milvus
→ найденные Markdown-секции wiki
```

То есть перед использованием wrapper должен быть уже выполнен pipeline:

```sh
sh code/pipeline/build-wiki-rag.sh
```

## MCP tools

- `markdown_rag_search` — поиск по Markdown RAG-индексу;
- `markdown_rag_reload_engine` — сброс кэшированного `RAGEngine`, чтобы следующий поиск переинициализировал backend;
- `markdown_rag_ping` — быстрая проверка, что MCP-server доступен из OpenCode.

Индексация намеренно не является MCP-tool. Она относится к build pipeline, а не к runtime-диалогу агента.

## Основной tool

```text
markdown_rag_search(
  query: string,
  limit: int = 5,
  threshold: float = 0.1,
  include_metadata: bool = true
)
```

Для Pascal/Delphi identifier-heavy запросов обычно нужен низкий threshold, например `0.1`.

Примеры запросов:

```text
FindBucket
TGpStringHash FindBucket
lock free queue
Create constructor TGpStringHash
```

## Важная особенность запуска

Wrapper использует Python API backend-пакета `markdown-rag-mcp`, поэтому его нужно запускать через окружение backend-а:

```text
uv --directory finalversion/tools/markdown-rag-mcp run python finalversion/code/mcp/markdown-rag-mcp-wrapper/server.py
```

Это сделано специально, чтобы не держать отдельную `.venv` внутри wrapper-папки.

## Переменные окружения

Опционально:

```sh
MARKDOWN_RAG_BACKEND_DIR="D:/Works/учёба/вкр/finalversion/tools/markdown-rag-mcp"
MARKDOWN_RAG_DEBUG_LOG_PATH="D:/Works/учёба/вкр/finalversion/data/cache/markdown-rag-mcp-wrapper.log"
MARKDOWN_RAG_MAX_SECTION_CHARS=4000
```

## Ручная проверка wrapper

Перед проверкой должен быть выполнен pipeline:

```sh
cd "D:/Works/учёба/вкр/finalversion"
sh code/pipeline/build-wiki-rag.sh
```

Затем можно проверить импорт и поиск вручную:

```sh
cd "D:/Works/учёба/вкр/finalversion/tools/markdown-rag-mcp"

uv run python - <<'PY'
import sys
import asyncio
import json

sys.path.insert(0, "D:/Works/учёба/вкр/finalversion/code/mcp/markdown-rag-mcp-wrapper")

import server

async def main():
    result = await server.markdown_rag_search(
        query="FindBucket",
        limit=1,
        threshold=0.1,
        include_metadata=True,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2)[:5000])
    await server.markdown_rag_reload_engine()

asyncio.run(main())
PY
```

## Проверка stdio MCP-запуска

```sh
cd "D:/Works/учёба/вкр/finalversion/tools/markdown-rag-mcp"
uv run python "D:/Works/учёба/вкр/finalversion/code/mcp/markdown-rag-mcp-wrapper/server.py"
```

Для stdio MCP-server это нормальное поведение: процесс ждёт MCP-сообщения. Остановить вручную можно через `Ctrl+C`.

## OpenCode config block

Актуальный фрагмент конфигурации должен лежать в:

```text
finalversion/code/agent/opencode.fragment.json
```

Рекомендуемый блок:

```json
"markdown_rag_wrapper": {
  "type": "local",
  "command": [
    "C:/Users/Danii/AppData/Roaming/Python/Python313/Scripts/uv.exe",
    "--directory",
    "D:/Works/учёба/вкр/finalversion/tools/markdown-rag-mcp",
    "run",
    "python",
    "D:/Works/учёба/вкр/finalversion/code/mcp/markdown-rag-mcp-wrapper/server.py"
  ],
  "enabled": true,
  "timeout": 300000,
  "environment": {
    "MARKDOWN_RAG_BACKEND_DIR": "D:/Works/учёба/вкр/finalversion/tools/markdown-rag-mcp",
    "MARKDOWN_RAG_DEBUG_LOG_PATH": "D:/Works/учёба/вкр/finalversion/data/cache/markdown-rag-mcp-wrapper.log",
    "MARKDOWN_RAG_MAX_SECTION_CHARS": "4000",
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUTF8": "1",
    "UV_LINK_MODE": "copy"
  }
}
```
