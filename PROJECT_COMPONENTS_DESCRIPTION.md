# Полное описание устройства проекта `finalversion`

Документ описывает, за что отвечает каждая крупная часть проекта, какие файлы являются точками входа, какие конфиги чем управляют и как данные проходят путь от Pascal/Delphi-кода до Obsidian wiki и OpenCode-агента.

## 1. Что делает проект

Проект `finalversion` — это локальная RAG-инфраструктура для Pascal/Delphi-кодовой базы.

Главная задача проекта: превратить исходники Pascal/Delphi в человекочитаемую Markdown wiki, пригодную для Obsidian, затем проиндексировать эту wiki в векторную базу и дать OpenCode-агенту инструмент поиска по этой базе.

Итоговый маршрут данных:
Pascal/Delphi source
→ PasDoc SimpleXML
→ Markdown wiki generator
→ Obsidian-compatible Markdown wiki
→ markdown-rag-mcp index
→ Docker Milvus vector database
→ markdown_rag_wrapper MCP
→ OpenCode agent

Иными словами:
1. Пользователь кладёт или указывает Pascal/Delphi-проект.
2. Скрипт создаёт wiki по unit/class/method.
3. Wiki можно открыть в Obsidian.
4. Wiki индексируется в RAG backend.
5. OpenCode получает MCP-инструмент `markdown_rag_search`.
6. Агент может отвечать на вопросы по проекту, сначала находя релевантные сущности через RAG, а затем уточняя детали через исходники и `pasls`.

## 2. Общая структура проекта

finalversion/
  .config/
  AGENTS.md
  code/
    agent/
    mcp/
    pipeline/
    wiki/
  data/
    cache/
    input_project/
    logs/
    wiki_out/
  tools/
    bin/
    markdown-rag-mcp/
    pasdoc/
    pasls/
    xmlstarlet/

Смысл верхнеуровневых папок:
| Путь | Назначение |
|---|---|
| `.config/` | Локальные настройки проекта: пути, AI-провайдер, режимы генерации. |
| `AGENTS.md` | Инструкции для OpenCode-агента: как пользоваться RAG, pasls и файлами. |
| `code/` | Собственный код проекта: wiki generator, pipeline, MCP wrapper, фрагменты конфигов. |
| `data/` | Входные и выходные данные: исходники, wiki, кэш, логи. |
| `tools/` | Внешние программы и backend: PasDoc, xmlstarlet, pasls, markdown-rag-mcp, вспомогательные exe. |

Главный принцип разделения:

tools  = внешние программы;
code   = собственные скрипты и wrapper;
data   = входные/выходные данные и runtime-артефакты;
.config = локальная конфигурация.

## 3. Основные сценарии использования

### 3.1. Полная сборка wiki и RAG-индекса

Точка входа:
code/pipeline/build-wiki-rag.sh

Что делает:

1. читает `.config/rag-pipeline.local.conf`;
2. создаёт нужные папки;
3. при необходимости очищает `data/wiki_out/current`;
4. запускает/проверяет Docker Milvus;
5. вызывает wiki-generator `code/wiki/ai-descr-ai-v3-config-rag-md-v3.sh`;
6. индексирует итоговую wiki через `markdown-rag-mcp`;
7. выполняет контрольный semantic search;
8. сохраняет логи в `data/logs`.

Запуск:
cd "D:/Works/учёба/вкр/finalversion"
sh "code/pipeline/build-wiki-rag.sh"

### 3.2. Ручная проверка RAG после сборки

Точка входа:
code/pipeline/check-rag.sh

Пример:
sh "code/pipeline/check-rag.sh" FindBucket

Скрипт делает только поиск по уже построенному индексу. Он не пересоздаёт wiki и не переиндексирует данные.

### 3.3. Работа в Obsidian

Открывать как Obsidian vault:
data/wiki_out/current

Там лежат Markdown-файлы по unit/class, например:
Home.md
GpStringHash.md
GpStringHash.TGpStringHash.md
GpLockFreeQueue.md

### 3.4. Работа в OpenCode

OpenCode запускается из корня проекта `finalversion` или с явно подключёнными инструкциями.

Используются:
AGENTS.md
code/agent/opencode.fragment.json
code/mcp/markdown-rag-mcp-wrapper/server.py

Runtime-инструменты:
| MCP tool | Назначение |
|---|---|
| `markdown_rag_ping` | Проверить, что MCP wrapper доступен. |
| `markdown_rag_warmup` | Прогреть RAG backend и закэшировать RAGEngine. |
| `markdown_rag_search` | Искать по wiki/RAG. |
| `markdown_rag_reload_engine` | Сбросить кэш RAGEngine. |

## 4. Папка `.config`

Папка `.config` содержит локальные настройки и примеры. Эти файлы не являются логикой приложения: они только задают значения, которые читают скрипты.

### 4.1. `.config/ai-descr.local.conf`

Назначение: управляет AI-обогащением wiki.
Этот конфиг отвечает только за AI-provider, модель и режимы обогащения.

Текущая логика поддерживает два режима:
AI_PROVIDER="openrouter"
AI_PROVIDER="openai-compatible"

#### Поля
| Поле | Что делает |
|---|---|
| `AI_PROVIDER` | Выбирает AI-провайдера: `openrouter` или `openai-compatible`. |
| `AI_URL` | URL OpenAI-compatible endpoint. Используется только при `AI_PROVIDER="openai-compatible"`. В режиме `openrouter` игнорируется. |
| `OPENROUTER_API_KEY` | Ключ OpenRouter. Используется только при `AI_PROVIDER="openrouter"`. |
| `AI_MODEL` | Имя модели у выбранного провайдера. |
| `AI_TEMPERATURE` | Температура генерации. |
| `AI_MAX_TOKENS` | Лимит токенов ответа модели. |
| `AI_ENRICH_UNITS` | Генерировать ли AI-описания для unit-файлов. |
| `AI_ENRICH_CLASSES` | Генерировать ли AI-описания для классов. |
| `AI_ENRICH_METHODS` | Генерировать ли AI-описания для методов. |

#### Как работает переключение provider-а

Для OpenRouter:
AI_PROVIDER="openrouter"
OPENROUTER_API_KEY="sk-or-v1-..."
AI_MODEL="poolside/laguna-m.1:free"

В этом режиме `AI_URL` не важен, потому что URL OpenRouter задаётся внутри скрипта.
Для Ollama/LM Studio/vLLM или другого OpenAI-compatible endpoint:

AI_PROVIDER="openai-compatible"
AI_URL="http://127.0.0.1:11434/v1/chat/completions"
AI_MODEL="qwen2.5-coder:3b"

В этом режиме `OPENROUTER_API_KEY` не используется. Авторизация не нужна, если локальный сервер её не требует.

### 4.2. `.config/rag-pipeline.local.conf`

Назначение: центральный конфиг pipeline. Управляет путями, инструментами, Docker/Milvus, RAG-индексацией и sanity-check.
Этот файл отвечает за layout проекта и инфраструктуру.

#### Основные поля
| Поле | Что делает |
|---|---|
| `FINAL_ROOT` | Корень clean-проекта `finalversion`. От него строятся остальные пути. |
| `PROJECT_ROOT` | Папка с исходниками Pascal/Delphi. Именно её обрабатывает wiki-generator. |
| `WIKI_CODE_DIR` | Папка, где лежит wiki-generator. |
| `WIKI_SCRIPT` | Полный путь к `ai-descr-ai-v3-config-rag-md-v3.sh`. |
| `WIKI_DIR` | Стабильная итоговая папка wiki. Обычно `data/wiki_out/current`. |
| `AI_CONFIG` | Путь к `.config/ai-descr.local.conf`. |
| `PASDOC_PROG` | Путь к `pasdoc.exe`. |
| `XMLSTARLET_BIN` | Путь к `xml.exe` из xmlstarlet. |
| `JQ_BIN` | Путь к `jq.exe`. |
| `UV_EXE` | Путь к `uv.exe`. |
| `MARKDOWN_RAG_DIR` | Папка backend-а `markdown-rag-mcp`. |
| `MILVUS_COMPOSE_FILE` | Docker Compose файл для Milvus. |
| `MARKDOWN_RAG_WRAPPER_DIR` | Папка MCP wrapper. |
| `MARKDOWN_RAG_WRAPPER_SERVER` | Путь к `server.py` wrapper-а. |
| `PASLS_EXE` | Путь к `pasls.exe`. |
| `MCP_LANGUAGE_SERVER_EXE` | Путь к `mcp-language-server.exe`. |
| `LOG_DIR` | Папка логов pipeline и wrapper. |
| `LAST_WIKI_DIR_FILE` | Файл-маркер с последним путём wiki. |
| `CACHE_DIR` | Папка кэша AI-описаний. |
| `AUTO_START_MILVUS` | Запускать ли Milvus автоматически через Docker Compose. |
| `MILVUS_CONTAINER_NAME` | Имя контейнера Milvus, состояние которого проверяется. |
| `MILVUS_HEALTH_TIMEOUT_SECONDS` | Сколько ждать healthy-статус Milvus. |
| `CLEAN_WIKI_DIR` | Очищать ли `WIKI_DIR` перед генерацией. |
| `RAG_RECURSIVE` | Индексировать ли wiki рекурсивно. |
| `RAG_FORCE_REINDEX` | Делать ли принудительную переиндексацию. |
| `RAG_TEST_QUERY` | Запрос для контрольного поиска после индексации. |
| `RAG_SEARCH_LIMIT` | Количество результатов для контрольного поиска. |
| `RAG_SEARCH_THRESHOLD` | Порог похожести для контрольного поиска. |

`rag-pipeline.local.conf` — центральное место для путей.

### 4.2. example

конфиги примеры
code/wiki/ai-descr.openrouter.example.conf
code/wiki/ai-descr.openai-compatible.example.conf

## 5. Файл `AGENTS.md`

Назначение: базовые инструкции для OpenCode-агента.
Этот файл объясняет агенту, как работать с проектом:

1. отвечать на русском языке;
2. сначала использовать `markdown_rag_wrapper.markdown_rag_search`, если вопрос касается архитектуры, unit, class, method или связей;
3. самостоятельно выбирать `query`, `limit`, `threshold`, `include_metadata`;
4. использовать RAG как навигационный контекст, но не как единственный источник истины;
5. проверять реализацию через `pasls` или чтение файлов;
6. не выдумывать результат;
7. не изменять файлы без явного запроса;
8. если первый RAG-запрос завершился timeout, повторить один раз, потому что backend мог прогреться.

Файл нужен для того, чтобы пользователь мог задавать обычные вопросы:

Что делает TGpStringHash.FindBucket?

а агент сам выбирал инструменты и параметры.

## 6. Папка `code`

Папка `code` содержит собственную логику проекта.
code/
  agent/
  mcp/
  pipeline/
  wiki/

## 7. Папка `code/wiki`

Назначение: генерация Markdown wiki из Pascal/Delphi-кода.
Главный файл:
code/wiki/ai-descr-ai-v3-config-rag-md-v3.sh

### 7.1. `ai-descr-ai-v3-config-rag-md-v3.sh`

Это главный генератор wiki. Он:

1. читает AI-конфиг;
2. принимает пути от оркестратора через переменные окружения;
3. проверяет зависимости;
4. ищет Pascal/Delphi-файлы;
5. запускает PasDoc для каждого файла;
6. получает SimpleXML;
7. извлекает из XML unit/class/method/property/field;
8. при необходимости вызывает AI-provider для описаний;
9. сохраняет результаты AI в кэш;
10. создаёт Markdown-файлы для unit и class;
11. добавляет RAG-поисковые ключи;
12. создаёт `Home.md`;
13. проверяет структуру wiki.

### 7.3. Основные группы функций в wiki-generator

В скрипте много shell-функций. Ниже они сгруппированы по назначению.

#### Проверка окружения и зависимостей
| Функция | Назначение |
|---|---|
| `resolve_jq_bin` | Находит `jq`: сначала проверяет `JQ_BIN`, потом `jq.exe` рядом со скриптом, потом `jq` в PATH. |
| `check_dependencies` | Проверяет наличие PasDoc, xmlstarlet, PROJECT_ROOT и shell-команд `awk`, `curl`, `cygpath`, `find`, `grep`, `md5sum`, `mktemp`, `sed`, `jq`. |
| `error_exit` | Печатает ошибку и завершает скрипт. |
| `is_true_false` | Проверяет, что значение равно `true` или `false`. |
| `validate_number` | Проверяет числовое значение, например `0.1`. |
| `validate_positive_integer` | Проверяет положительное целое число. |
| `validate_ai_config` | Проверяет корректность AI-настроек: provider, model, temperature, max tokens, режимы enrich. |

#### Работа с путями и XML
| Функция | Назначение |
|---|---|
| `to_win_path` | Преобразует MSYS/Git Bash путь в Windows-путь через `cygpath -am`. Нужно для Windows exe. |
| `xmlstarlet_sel` | Обёртка над `xmlstarlet sel`, которая передаёт XML-файл в Windows-формате. |
| `get_pascal_file_list` | Возвращает список `.pas` и `.pp` файлов из `PROJECT_ROOT`. |
| `extract_unit_name` | Извлекает имя unit из исходника. Если не получилось — берёт имя файла. |
| `make_ascii_stage_file` | Создаёт безопасное временное имя файла в ASCII-пути. Нужно, чтобы Windows exe не ломались на кириллице. |
| `make_source_path_display` | Делает относительный путь для wiki, например `src/GpStringHash.pas`, вместо абсолютного Windows-пути. |
| `class_page_name` | Формирует имя Markdown-страницы класса: `UnitName.ClassName`. |
| `class_wikilink` | Формирует Obsidian-ссылку на страницу класса. |
| `join_nonempty_lines_csv` | Склеивает непустые строки в CSV-строку. |
| `xml_values_csv` | Извлекает значения из XML по XPath и склеивает их в CSV. Используется для RAG-поисковых ключей. |

#### Генерация RAG-поисковых ключей
| Функция | Назначение |
|---|---|
| `write_rag_key_if_not_empty` | Записывает строку вида `- key: value`, если value не пустое. |
| `add_unit_rag_search_keys` | Добавляет в unit-файл секцию `RAG-поисковые ключи`: kind, id, source_path, classes, types, variables, routines. |
| `add_class_rag_search_keys` | Добавляет в class-файл RAG-ключи: kind, id, unit, structure_type, source_path, ancestor, methods, fields, properties. |
| `add_duplicate_counters` | Добавляет счётчики к повторяющимся именам, чтобы различать перегруженные методы/конструкторы. |

#### Очистка и нормализация текста
| Функция | Назначение |
|---|---|
| `cleanup` | Удаляет временную рабочую директорию после завершения. |
| `decode_entities` | Декодирует XML/HTML entities: `&lt;`, `&gt;`, `&amp;`, `&quot;`, `&apos;`. |
| `normalize_inline` | Нормализует короткий inline-текст: убирает лишние пробелы и переводы строк. |
| `normalize_description` | Очищает описание из XML: декодирует entities, удаляет XML/HTML-теги, нормализует пробелы. |
| `text_or_placeholder` | Возвращает текст или `Нет описания`, если текст пустой. |

#### AI-provider, запросы и кэш
| Функция | Назначение |
|---|---|
| `resolve_ai_url` | Выбирает endpoint: фиксированный OpenRouter URL или `AI_URL` для openai-compatible. |
| `hash_string` | MD5-хэш строки. Используется для кэша. |
| `get_file_hash` | MD5-хэш исходного файла. Если файл изменился, кэш считается устаревшим. |
| `safe_cache_component` | Делает безопасный фрагмент имени файла кэша. |
| `get_cache_path` | Строит путь к cache-файлу с учётом исходника, provider-а, модели, prompt-а и параметров. |
| `load_from_cache` | Читает AI-описание из кэша. |
| `save_to_cache` | Сохраняет AI-описание в кэш. |
| `strip_ai_response` | Очищает ответ модели от лишних обёрток и пробелов. |
| `build_ai_request` | Формирует JSON-запрос к chat/completions endpoint. |
| `call_ai_provider` | Делает HTTP-запрос к OpenRouter или OpenAI-compatible endpoint через `curl`. |
| `extract_ai_content` | Извлекает текст ответа из JSON-ответа модели через `jq`. |
| `generate_ai_description` | Общая функция генерации описания: строит prompt, проверяет кэш, вызывает provider, сохраняет результат. |
| `needs_description` | Решает, нужно ли обогащать описание. Пустое или слишком короткое описание считается недостаточным. |
| `generate_ai_unit_description` | Генерирует prompt и описание для unit. |
| `generate_ai_class_description` | Генерирует prompt и описание для класса. |
| `generate_ai_method_description` | Генерирует prompt и описание для метода. |
| `enrich_unit_description` | Возвращает исходное описание unit или AI-обогащённое, если разрешено в конфиге и родное описание мало/отсутствует. |
| `enrich_class_description` | Аналогично для класса. |
| `enrich_method_description` | Аналогично для метода. |

#### Генерация Markdown-файлов
| Функция | Назначение |
|---|---|
| `create_unit_markdown` | Создаёт Markdown-файл unit: заголовок, source_path, описание, ссылки на классы, RAG-ключи. |
| `create_class_markdown` | Создаёт Markdown-файл класса: unit, source_path, visibility, ancestor, описание, RAG-ключи. |
| `add_properties` | Добавляет секцию свойств класса. |
| `generate_markdown_section` | Генерирует Markdown-секцию для метода/поля/переменной/сущности из XML. |
| `add_types_and_variables` | Добавляет секции типов и переменных unit-а. |
| `process_classes` | Обрабатывает все классы из XML и создаёт class-страницы. |
| `process_xml_file` | Обрабатывает SimpleXML одного unit-а и создаёт Markdown-файлы. |
| `process_single_pascal_file` | Полный цикл для одного `.pas/.pp`: подготовка пути, запуск PasDoc, обработка XML. |
| `create_index_file` | Создаёт `Home.md` со списком страниц wiki. |
| `validate_descriptions` | Предупреждает, если в Markdown остались `Нет описания`. |
| `validate_wiki_structure` | Проверяет wiki: пустые файлы, число unit-файлов и class-файлов. |

### 7.4. Основная логика выполнения wiki-generator

В конце файла выполняется последовательность:
check_dependencies
validate_ai_config
создание временных папок
trap cleanup EXIT
нормализация PROJECT_ROOT
вывод текущей конфигурации
получение списка Pascal-файлов
для каждого файла: process_single_pascal_file
create_index_file
validate_descriptions
validate_wiki_structure
вывод финального пути wiki

Главный результат:
data/wiki_out/current/*.md

## 8. Папка `code/pipeline`

Назначение: оркестрация всего процесса сборки wiki и RAG-индекса.

Файлы:
build-wiki-rag.sh
check-rag.sh
rag-pipeline.example.conf
README.md
RAG_ARCHITECTURE.md

### 8.1. `build-wiki-rag.sh`

Главный build-скрипт. Именно его нужно запускать для полного обновления wiki и RAG-индекса.

#### Функции

| Функция | Назначение |
|---|---|
| `error_exit` | Печатает ошибку и завершает скрипт. |
| `info` | Печатает информационное сообщение с префиксом `[pipeline]`. |
| `require_file` | Проверяет существование файла. |
| `require_dir` | Проверяет существование папки. |
| `require_cmd` | Проверяет наличие команды в PATH. |
| `to_win_path` | Конвертирует путь в Windows-формат через `cygpath`, если доступен. |
| `load_config` | Загружает `.config/rag-pipeline.local.conf` и проверяет обязательные переменные. |
| `start_milvus_if_needed` | Запускает Docker Compose для Milvus и ждёт `healthy/running` статус контейнера. |
| `prepare_output_dirs` | Создаёт `LOG_DIR`, `CACHE_DIR`, папку для маркера wiki; при необходимости очищает `WIKI_DIR`. |
| `run_wiki_generation` | Запускает `ai-descr-ai-v3-config-rag-md-v3.sh` с путями из pipeline-конфига. Пишет лог `wiki-build-*.log`. |
| `index_wiki` | Запускает `markdown-rag-mcp index` для `WIKI_DIR`. Пишет лог `rag-index-*.log`. Проверяет, что failed files = 0. |
| `check_rag_search` | Выполняет контрольный `markdown-rag-mcp search` и проверяет, что результат не пустой. |
| `main` | Главная последовательность: config → dirs → Milvus → wiki → index → search-check. |

#### Что передаёт в wiki-generator

`run_wiki_generation` передаёт через окружение:
AI_CONFIG
PROJECT_ROOT
WIKI_DIR
PASDOC_PROG
XMLSTARLET_BIN
JQ_BIN
CACHE_DIR

#### Что передаёт в markdown-rag-mcp

`index_wiki` запускает:
uv run markdown-rag-mcp index \
  --index-dir "$WIKI_DIR_WIN" \
  --no-recursive или --recursive \
  --force при необходимости

При этом выставляются переменные:
PYTHONIOENCODING=utf-8
PYTHONUTF8=1
UV_LINK_MODE=copy

Они нужны для корректного вывода Unicode/rich на Windows и стабильной установки/запуска через `uv`.

### 8.2. `check-rag.sh`

Лёгкий скрипт для проверки уже построенного индекса.
1. читает `rag-pipeline.local.conf`;
2. берёт query из первого аргумента или из `RAG_TEST_QUERY`;
3. берёт `limit` и `threshold` из конфига;
4. запускает `markdown-rag-mcp search`;
5. выводит JSON с результатами.

Скрипт не запускает PasDoc, не создаёт wiki и не индексирует её заново.

### 8.3. `rag-pipeline.example.conf`

Шаблон pipeline-конфига. Его можно использовать как образец для создания `.config/rag-pipeline.local.conf`.

### 8.4. `README.md`

Документация по запуску pipeline.

Описывает:
- структуру проекта;
- требуемые программы;
- установку `markdown-rag-mcp`;
- настройку AI и pipeline конфигов;
- полный запуск;
- ручную проверку RAG;
- подключение OpenCode.

### 8.5. `RAG_ARCHITECTURE.md`

Архитектурное описание проекта.
Объясняет:

- что входит в проект;
- pipeline генерации;
- runtime pipeline поиска;
- роли `wiki generator`, `markdown-rag-mcp`, `markdown-rag-mcp-wrapper`, OpenCode, pasls;
- почему индексация не является MCP-tool;
- что не входит в проект;
- текущие ограничения.

## 9. Папка `code/mcp/markdown-rag-mcp-wrapper`

Назначение: MCP-сервер для OpenCode, который предоставляет доступ к RAG-поиску.

Главный файл:
code/mcp/markdown-rag-mcp-wrapper/server.py

Wrapper не индексирует wiki и не генерирует embeddings. Он работает только с уже готовым индексом `markdown-rag-mcp/Milvus`.

### 9.1. Почему wrapper нужен

`markdown-rag-mcp` умеет искать по wiki, но OpenCode нужен MCP-инструмент. Поэтому создан тонкий MCP wrapper, который:

1. запускается как stdio MCP-сервер;
2. импортирует Python API backend-а;
3. кэширует `RAGEngine`;
4. принимает запросы от OpenCode;
5. возвращает компактный JSON.

### 9.2. Почему wrapper использует Python API, а не subprocess

Ранее пробовался вариант через CLI/subprocess:
uv run markdown-rag-mcp search ...

Он оказался менее стабильным для MCP, потому что CLI печатает progress bars, rich-таблицы и логи. В stdio MCP это может портить протокол.
Текущая версия использует Python API напрямую и перехватывает stdout/stderr backend-а в лог.

### 9.3. Helper-функции `server.py`

| Функция | Назначение |
|---|---|
| `_default_final_root` | Определяет корень `finalversion` относительно расположения `server.py`. |
| `_default_debug_log_path` | Возвращает путь к стандартному логу wrapper-а: `data/logs/markdown-rag-mcp-wrapper.log`. |
| `_env` | Читает переменную окружения или возвращает default. |
| `_backend_dir` | Возвращает путь к backend-у `markdown-rag-mcp`. |
| `_debug_log_path` | Возвращает путь к debug-log из env или default. |
| `_max_section_chars` | Читает лимит длины секции результата. |
| `_debug_log` | Пишет диагностическую строку в лог. Ошибки логирования не ломают MCP. |
| `_capture_backend_output` | Перехватывает stdout/stderr backend-а и пишет их в лог, чтобы не сломать MCP stdio. |
| `_validate_backend_paths` | Проверяет, что backend существует и похож на `markdown-rag-mcp`. |
| `_ensure_backend_import_path` | Добавляет `tools/markdown-rag-mcp/src` в `sys.path` как fallback. |
| `_truncate` | Обрезает слишком длинный `section_text`. |
| `_compact_result` | Преобразует backend `QueryResult` в компактный dict для OpenCode. |
| `_get_engine` | Инициализирует и кэширует `RAGEngine`. Использует lock, чтобы не запускать несколько инициализаций одновременно. |
| `_shutdown_engine` | Завершает текущий `RAGEngine` и очищает кэш. |

### 9.4. MCP tools `server.py`

| Tool | Назначение |
|---|---|
| `markdown_rag_ping` | Быстрая проверка доступности MCP-сервера. Не трогает RAG backend. |
| `markdown_rag_warmup` | Инициализирует backend imports и `RAGEngine`, чтобы последующие поиски были быстрыми. |
| `markdown_rag_search` | Основной поиск по wiki/RAG. Принимает `query`, `limit`, `threshold`, `include_metadata`. |
| `markdown_rag_reload_engine` | Сбрасывает кэш `RAGEngine`; следующий search/warmup инициализирует backend заново. |

### 9.5. Особенность cold start

Первый вызов `warmup` или `search` после запуска OpenCode может уйти в timeout из-за холодного импорта backend-а и загрузки модели embeddings.

Практическое поведение:
первый warmup может показать timeout;
при этом backend часто успевает прогреться;
следующий warmup/search работает быстро.

Именно поэтому в `AGENTS.md` указано: если первый RAG-вызов завершился timeout, повторить запрос один раз.

### 9.6. Логи wrapper-а

Стандартный лог:
data/logs/markdown-rag-mcp-wrapper.log

Туда попадают:
- вызовы `ping`, `warmup`, `search`, `reload`;
- этапы `_get_engine`;
- stdout/stderr backend-а;
- progress bars `sentence-transformers/tqdm`;
- ошибки инициализации и поиска.

## 10. Папка `code/agent`

Назначение: конфигурационные фрагменты для OpenCode.

### 10.1. `opencode.fragment.json`

Фрагмент `opencode.json`, который показывает, как подключить MCP-серверы.

В clean-конфигурации обычно нужны два MCP:
pasls
markdown_rag_wrapper

`pasls` нужен для Pascal/Delphi code intelligence.

`markdown_rag_wrapper` нужен для RAG-поиска по wiki.

Важно: wrapper запускается через окружение backend-а `markdown-rag-mcp`, например:
uv --directory finalversion/tools/markdown-rag-mcp run python finalversion/code/mcp/markdown-rag-mcp-wrapper/server.py

## 11. Папка `data`

Назначение: входные данные, результаты работы, кэш и логи.

### 11.1. `data/input_project`

Папка для исходного Pascal/Delphi-проекта.

В архиве есть пример:
data/input_project/GpDelphiUnits_very_mini

Именно исходники из `PROJECT_ROOT` обрабатываются wiki-generator-ом и используются `pasls`.

Если OpenCode должен уметь читать исходники, они должны быть доступны в workspace или явно разрешённой области.

### 11.2. `data/wiki_out`

Папка с результатом генерации wiki.

Ключевые элементы:

| Путь | Назначение |
|---|---|
| `data/wiki_out/current` | Стабильная текущая wiki. Открывается в Obsidian и индексируется в RAG. |
| `data/wiki_out/last_wiki_dir.txt` | Маркер последнего пути wiki. Сейчас содержит путь к `current`. |

Примеры wiki-файлов:
Home.md
GpStringHash.md
GpStringHash.TGpStringHash.md
GpStringHash.TGpStringHashEnumerator.md
GpLockFreeQueue.md

### 11.3. `data/wiki_out/current/.obsidian`

Настройки Obsidian vault. Благодаря этому `current` можно открыть как готовое хранилище Obsidian.

### 11.4. `data/cache`

Папка runtime-кэша.

| Путь | Назначение |
|---|---|
| `data/cache/ai-descriptions` | Кэш AI-описаний, чтобы не делать повторные запросы к модели. |

### 11.5. `data/logs`

Папка логов.
Типовые файлы:

| Файл | Что содержит |
|---|---|
| `wiki-build-*.log` | Лог генерации Markdown wiki. |
| `rag-index-*.log` | Лог индексации wiki в markdown-rag-mcp/Milvus. |
| `rag-search-check-*.log` | Лог контрольного поиска после индексации. |
| `markdown-rag-mcp-wrapper.log` | Лог MCP wrapper-а и backend stdout/stderr. |
| `markdown-rag-mcp-wrapper-manual.log` | Лог ручных диагностических запусков wrapper-а. |

## 12. Папка `tools`

Назначение: внешние программы и backend.

### 12.1. `tools/bin`

Вспомогательные исполняемые файлы.

Ожидаемые файлы:
jq.exe
mcp-language-server.exe

### 12.2. `tools/pasdoc`

PasDoc — внешний инструмент, который читает Pascal/Delphi-код и создаёт SimpleXML.

Используется в wiki-generator-е.

Главный ожидаемый файл:
tools/pasdoc/bin/pasdoc.exe

### 12.3. `tools/xmlstarlet`

xmlstarlet — внешний инструмент для XPath-запросов к SimpleXML.

Главный ожидаемый файл:
tools/xmlstarlet/xmlstarlet-1.6.1/xml.exe

### 12.4. `tools/pasls`

Pascal language server.

Используется через `mcp-language-server.exe` как MCP server для OpenCode.

Главный ожидаемый файл:
tools/pasls/pasls.exe

### 12.5. `tools/markdown-rag-mcp`

Внешний RAG backend.
Отвечает за:
- чтение Markdown;
- разбиение на секции/chunks;
- embeddings;
- работу с Milvus;
- semantic search.
Он используется как готовая внешняя зависимость.

Ключевые файлы backend-а:

| Файл/папка | Назначение |
|---|---|
| `pyproject.toml` | Python project config backend-а. |
| `uv.lock` | Lock-файл зависимостей. |
| `docker/docker-compose.yml` | Docker Compose для Milvus stack. |
| `src/markdown_rag_mcp` | Исходники backend-а. |
| `README.md`, `CLI.md`, `ARCHITECTURE.md` | Документация backend-а. |

## 13. Как данные проходят через систему

### 13.1. Build-time поток

PROJECT_ROOT
→ get_pascal_file_list
→ process_single_pascal_file
→ PasDoc SimpleXML
→ process_xml_file
→ create_unit_markdown / create_class_markdown
→ data/wiki_out/current/*.md
→ markdown-rag-mcp index
→ Milvus vector index
→ check_rag_search

Этот поток запускается `build-wiki-rag.sh`.

### 13.2. Runtime поток OpenCode

пользователь задаёт вопрос
→ OpenCode читает AGENTS.md
→ OpenCode вызывает markdown_rag_search
→ markdown-rag-mcp-wrapper использует cached RAGEngine
→ RAGEngine ищет в Milvus
→ wrapper возвращает найденные Markdown-секции
→ OpenCode при необходимости уточняет через pasls/исходники
→ OpenCode отвечает пользователю

## 14. Код

### Свой код

AGENTS.md
.config/*.conf
code/wiki/ai-descr-ai-v3-config-rag-md-v3.sh
code/pipeline/*.sh
code/mcp/markdown-rag-mcp-wrapper/server.py
code/agent/opencode.fragment.json

### Внешние инструменты

tools/markdown-rag-mcp
tools/pasdoc
tools/xmlstarlet
tools/pasls
tools/bin/jq.exe
tools/bin/mcp-language-server.exe
Docker Milvus stack


## 15. Типовые проблемы и куда смотреть

### 15.1. Wiki не создаётся

Смотреть:
data/logs/wiki-build-*.log

Проверить:

- `PROJECT_ROOT` существует;
- `PASDOC_PROG` существует;
- `XMLSTARLET_BIN` существует;
- `JQ_BIN` существует;
- Git Bash/MSYS2 содержит `awk`, `sed`, `grep`, `find`, `curl`, `cygpath`, `mktemp`, `md5sum`.

### 15.2. Индексация падает

Смотреть:
data/logs/rag-index-*.log

Проверить:

- Docker запущен;
- Milvus контейнер healthy;
- `MARKDOWN_RAG_DIR` указывает на backend;
- `UV_EXE` существует;
- wiki содержит `.md` файлы.

### 15.3. RAG search CLI не возвращает результаты

Смотреть:
data/logs/rag-search-check-*.log

Проверить:

- был ли выполнен index;
- правильный ли threshold;
- для идентификаторов Pascal/Delphi обычно нужен низкий threshold `0.1`;
- запрос лучше формулировать с идентификатором и контекстом, например `TGpStringHash FindBucket`.

### 15.4. OpenCode видит MCP, но search timeout

Смотреть:
data/logs/markdown-rag-mcp-wrapper.log

Вероятная причина: cold start backend-а. Решение:

1. вызвать `markdown_rag_warmup`;
2. если timeout — повторить `warmup` или выполнить `search`;
3. после прогрева `RAGEngine` search должен работать быстро.

### 15.5. Агент отвечает только по wiki, но не по исходникам

Проверить:
- OpenCode workspace действительно включает исходники;
- `PROJECT_ROOT` указывает на актуальную папку исходников;
- `pasls` workspace указывает на ту же кодовую базу;
- исходники лежат в `data/input_project/...` или другой доступной OpenCode области.

## 16. Краткая карта ответственности

.config/ai-descr.local.conf
  отвечает за AI-provider, модель и режимы обогащения

.config/rag-pipeline.local.conf
  отвечает за пути, инструменты, Milvus, RAG index/check

AGENTS.md
  отвечает за поведение OpenCode-агента

code/wiki/ai-descr-ai-v3-config-rag-md-v3.sh
  отвечает за превращение Pascal/Delphi + PasDoc XML в Markdown wiki

code/pipeline/build-wiki-rag.sh
  отвечает за полный build: wiki → index → search-check

code/pipeline/check-rag.sh
  отвечает за ручную проверку уже готового RAG-индекса

code/mcp/markdown-rag-mcp-wrapper/server.py
  отвечает за MCP-инструменты OpenCode для RAG-поиска

code/agent/opencode.fragment.json
  показывает, как подключить MCP-серверы к OpenCode

data/input_project
  хранит исходный Pascal/Delphi-проект

data/wiki_out/current
  хранит текущую Obsidian-compatible wiki

data/cache/ai-descriptions
  хранит кэш AI-описаний

data/logs
  хранит логи pipeline, индексации, поиска и wrapper-а

tools/markdown-rag-mcp
  внешний backend для embeddings, Milvus и semantic search

tools/pasdoc
  внешний генератор SimpleXML из Pascal/Delphi

tools/xmlstarlet
  внешний инструмент XPath/XML extraction

tools/pasls
  внешний Pascal language server

tools/bin
  вспомогательные exe: jq, mcp-language-server
