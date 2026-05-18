# tools

Папка `tools` содержит внешние и вспомогательные инструменты, необходимые clean pipeline.

## Ожидаемая структура

```text
tools/
  bin/
    jq.exe
    mcp-language-server.exe

  pasdoc/
    bin/pasdoc.exe

  xmlstarlet/
    xmlstarlet-1.6.1/xml.exe

  pasls/
    pasls.exe

  markdown-rag-mcp/
    pyproject.toml
    uv.lock
    docker/docker-compose.yml
    src/markdown_rag_mcp/
```

## Что относится к tools

Сюда кладутся сторонние программы и backend-компоненты:

- PasDoc;
- xmlstarlet;
- jq;
- pasls;
- `mcp-language-server.exe`;
- внешний backend `markdown-rag-mcp`.

## Установка markdown-rag-mcp

Если backend ещё не установлен:

```sh
cd "D:/Works/учёба/вкр/finalversion/tools"
git clone https://github.com/mohllal/markdown-rag-mcp.git
cd markdown-rag-mcp
uv sync
uv pip install mcp
```

Milvus поднимается из backend-папки:

```sh
cd "D:/Works/учёба/вкр/finalversion/tools/markdown-rag-mcp"
docker compose -f docker/docker-compose.yml up -d
```

Обычно вручную это делать не нужно, потому что `code/pipeline/build-wiki-rag.sh` умеет запускать Docker Compose сам, если в конфиге стоит:

```sh
AUTO_START_MILVUS="true"
```

## Проверка инструментов

Из корня `finalversion`:

```sh
. ".config/rag-pipeline.local.conf"

test -f "$PASDOC_PROG" && echo "PASDOC ok"
test -f "$XMLSTARLET_BIN" && echo "XMLSTARLET ok"
test -f "$JQ_BIN" && echo "JQ ok"
test -f "$PASLS_EXE" && echo "PASLS ok"
test -f "$MCP_LANGUAGE_SERVER_EXE" && echo "MCP language server ok"
test -d "$MARKDOWN_RAG_DIR" && echo "markdown-rag-mcp ok"
```

## Примечание

Внешний backend `markdown-rag-mcp` не модифицируется
