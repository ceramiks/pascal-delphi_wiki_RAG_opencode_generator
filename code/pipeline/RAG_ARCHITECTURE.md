# RAG MVP+ architecture

## Статус

Уже выполняет полный маршрут:

```text
исходники Pascal/Delphi
→ Markdown wiki в data/wiki_out/current
→ индексация в markdown-rag-mcp / Milvus
→ контрольный semantic search
```

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
