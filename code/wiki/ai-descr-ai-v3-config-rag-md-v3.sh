#!/usr/bin/env sh

# Локальная генерация wiki из Pascal/Delphi файлов через PasDoc SimpleXML.
# Предполагается запуск в Git Bash / MSYS2.

set -u

# =============================
# КОНФИГУРАЦИЯ
# =============================
# По умолчанию скрипт читает локальный конфиг из текущей папки запуска.
# Можно указать другой файл:
#   AI_CONFIG="/path/to/ai-descr.local.conf" ./ai-descr-local-ai-v3-config.sh
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CONFIG_FILE="${AI_CONFIG:-${SCRIPT_DIR}/ai-descr.local.conf}"
CONFIG_LOADED="false"

# Значения, переданные извне оркестратором, должны иметь приоритет над AI_CONFIG.
# AI_CONFIG может содержать старые пути, поэтому сохраняем внешние значения до source.
ENV_PASDOC_PROG="${PASDOC_PROG:-}"
ENV_XMLSTARLET_BIN="${XMLSTARLET_BIN:-}"
ENV_JQ_BIN="${JQ_BIN:-}"
ENV_PROJECT_ROOT="${PROJECT_ROOT:-}"
ENV_WIKI_DIR="${WIKI_DIR:-}"
ENV_CACHE_DIR="${CACHE_DIR:-}"

if [ -f "$CONFIG_FILE" ]; then
    . "$CONFIG_FILE"
    CONFIG_LOADED="true"
elif [ -n "${AI_CONFIG:-}" ]; then
    echo "Ошибка: AI_CONFIG указан, но файл не найден: $CONFIG_FILE" >&2
    exit 1
fi

# Внешние значения имеют приоритет над AI_CONFIG.
[ -n "$ENV_PASDOC_PROG" ] && PASDOC_PROG="$ENV_PASDOC_PROG"
[ -n "$ENV_XMLSTARLET_BIN" ] && XMLSTARLET_BIN="$ENV_XMLSTARLET_BIN"
[ -n "$ENV_JQ_BIN" ] && JQ_BIN="$ENV_JQ_BIN"
[ -n "$ENV_PROJECT_ROOT" ] && PROJECT_ROOT="$ENV_PROJECT_ROOT"
[ -n "$ENV_WIKI_DIR" ] && WIKI_DIR="$ENV_WIKI_DIR"
[ -n "$ENV_CACHE_DIR" ] && CACHE_DIR="$ENV_CACHE_DIR"

# =============================
# НАСТРОЙКИ
# =============================
PASDOC_PROG="${PASDOC_PROG:-D:/Works/учёба/ВКР/code/wiki/pasdoc/bin/pasdoc.exe}"
XMLSTARLET_BIN="${XMLSTARLET_BIN:-D:/Works/учёба/ВКР/code/wiki/xmlstarlet-1.6.1-win32/xmlstarlet-1.6.1/xml.exe}"
JQ_BIN="${JQ_BIN:-}"
PROJECT_ROOT="${1:-${PROJECT_ROOT:-D:/Works/учёба/ВКР/GpDelphiUnits_mini/src}}"

NOW=$(date +%Y-%m-%d_%H-%M-%S)

# Временные директории — в ASCII-пути, чтобы Windows exe не сталкивались с кириллицей.
WORK_ROOT=$(mktemp -d /tmp/pasdoc_wiki_${NOW}_XXXXXX)
DOC_DIR="${WORK_ROOT}/docs_tmp"
STAGE_DIR="${WORK_ROOT}/stage"

# Итоговая wiki — рядом со скриптом.
WIKI_DIR="${WIKI_DIR:-${SCRIPT_DIR}/wiki_out_${NOW}}"

PASDOC_OUTPUT_FORMAT="simplexml"

# =============================
# НАСТРОЙКИ ИИ-ОБОГАЩЕНИЯ
# =============================
# AI_PROVIDER:
#   openrouter         — OpenRouter API: https://openrouter.ai/api/v1/chat/completions
#   openai-compatible — любой OpenAI-compatible endpoint: Ollama/LM Studio/vLLM/etc.
AI_PROVIDER="${AI_PROVIDER:-openrouter}"
AI_URL="${AI_URL:-}"
AI_MODEL="${AI_MODEL:-}"
AI_TEMPERATURE="${AI_TEMPERATURE:-0.1}"
AI_MAX_TOKENS="${AI_MAX_TOKENS:-1200}"

# По умолчанию обогащаем только крупные сущности. Методы можно включить отдельно,
# чтобы первый AI-прогон не превращался в десятки/сотни запросов.
AI_ENRICH_UNITS="${AI_ENRICH_UNITS:-true}"
AI_ENRICH_CLASSES="${AI_ENRICH_CLASSES:-true}"
AI_ENRICH_METHODS="${AI_ENRICH_METHODS:-false}"

# Кэш зависит от исходника, модели, provider-а, URL, параметров и версии промптов.
AI_PROMPT_VERSION="v2-short-descriptions"
AI_CACHE_SCHEMA_VERSION="ai-v3"
CACHE_DIR="${CACHE_DIR:-${HOME}/.cache/pasdoc_ai_descriptions}"

# Безопасный разделитель полей вместо '|'.
SEP=$(printf '\037')

# =============================
# ПРОВЕРКИ
# =============================
resolve_jq_bin() {
    # Если JQ_BIN задан явно, используем его.
    if [ -n "${JQ_BIN:-}" ]; then
        if [ -x "$JQ_BIN" ] || [ -f "$JQ_BIN" ]; then
            return 0
        fi
        echo "Ошибка: JQ_BIN указан, но файл не найден: $JQ_BIN" >&2
        exit 1
    fi

    # Частый случай для Git Bash/MSYS2: jq.exe лежит рядом со скриптом.
    if [ -f "${SCRIPT_DIR}/jq.exe" ]; then
        JQ_BIN="${SCRIPT_DIR}/jq.exe"
        return 0
    fi

    if [ -f "${SCRIPT_DIR}/jq" ]; then
        JQ_BIN="${SCRIPT_DIR}/jq"
        return 0
    fi

    if command -v jq >/dev/null 2>&1; then
        JQ_BIN="jq"
        return 0
    fi

    echo "Ошибка: jq не найден. Положите jq.exe рядом со скриптом, добавьте jq в PATH или задайте JQ_BIN=/path/to/jq.exe" >&2
    exit 1
}

check_dependencies() {
    [ -f "$PASDOC_PROG" ] || { echo "Ошибка: PasDoc не найден: $PASDOC_PROG"; exit 1; }
    [ -f "$XMLSTARLET_BIN" ] || { echo "Ошибка: xmlstarlet не найден: $XMLSTARLET_BIN"; exit 1; }
    [ -d "$PROJECT_ROOT" ] || { echo "Ошибка: PROJECT_ROOT не найден: $PROJECT_ROOT"; exit 1; }

    command -v awk >/dev/null 2>&1 || { echo "Ошибка: awk не найден"; exit 1; }
    command -v curl >/dev/null 2>&1 || { echo "Ошибка: curl не найден, AI-версия не может работать без curl"; exit 1; }
    command -v cygpath >/dev/null 2>&1 || { echo "Ошибка: cygpath не найден"; exit 1; }
    command -v find >/dev/null 2>&1 || { echo "Ошибка: find не найден"; exit 1; }
    command -v grep >/dev/null 2>&1 || { echo "Ошибка: grep не найден"; exit 1; }
    command -v md5sum >/dev/null 2>&1 || { echo "Ошибка: md5sum не найден"; exit 1; }
    resolve_jq_bin
    command -v mktemp >/dev/null 2>&1 || { echo "Ошибка: mktemp не найден"; exit 1; }
    command -v sed >/dev/null 2>&1 || { echo "Ошибка: sed не найден"; exit 1; }
}

# =============================
# ВСПОМОГАТЕЛЬНОЕ
# =============================
to_win_path() {
    cygpath -am "$1"
}

xmlstarlet_sel() {
    xml_file="$1"
    shift
    xml_file_win=$(to_win_path "$xml_file")
    "$XMLSTARLET_BIN" sel "$@" "$xml_file_win"
}

get_pascal_file_list() {
    find "$PROJECT_ROOT" -type f \( -iname "*.pas" -o -iname "*.pp" \) | sort
}

extract_unit_name() {
    file_path="$1"
    base_name=$(basename "$file_path")
    base_name=${base_name%.pas}
    base_name=${base_name%.pp}

    unit_name=$(grep -i "^[[:space:]]*unit[[:space:]]\+" "$file_path" \
        | head -1 \
        | sed -E 's/^[[:space:]]*[Uu][Nn][Ii][Tt][[:space:]]+//' \
        | sed 's/;.*//' \
        | xargs)

    [ -z "$unit_name" ] && unit_name="$base_name"
    echo "$unit_name"
}

make_ascii_stage_file() {
    src_path="$1"
    base_name=$(basename "$src_path")
    hash=$(printf '%s' "$src_path" | md5sum | cut -d' ' -f1)
    echo "${STAGE_DIR}/${hash}_${base_name}"
}

# Делает путь к исходнику переносимым для wiki.
# Например:
#   D:/.../GpDelphiUnits_mini/src/GpStringHash.pas -> src/GpStringHash.pas
make_source_path_display() {
    file_path=$(printf '%s' "$1" | sed 's#\\#/#g')
    root_path=$(printf '%s' "$PROJECT_ROOT" | sed 's#\\#/#g')
    root_path=${root_path%/}
    root_base=$(basename "$root_path")

    case "$file_path" in
        "$root_path"/*)
            rel_path=${file_path#"$root_path"/}
            printf '%s/%s\n' "$root_base" "$rel_path"
            ;;
        *)
            # Если файл почему-то вне PROJECT_ROOT, не тащим абсолютный путь в wiki.
            basename "$file_path"
            ;;
    esac
}

class_page_name() {
    unit_name="$1"
    class_name="$2"
    echo "${unit_name}.${class_name}"
}

class_wikilink() {
    unit_name="$1"
    class_name="$2"
    page_name=$(class_page_name "$unit_name" "$class_name")
    echo "[[${page_name}|${class_name}]]"
}


join_nonempty_lines_csv() {
    awk '
        NF {
            if (out != "") out = out ", "
            out = out $0
        }
        END { print out }
    '
}

xml_values_csv() {
    xml_file="$1"
    xpath="$2"
    value_expr="$3"

    [ -f "$xml_file" ] || error_exit "XML-файл не найден: $xml_file"

    values_file=$(mktemp "${WORK_ROOT}/xml_values_XXXXXX") || error_exit "не удалось создать временный файл xml_values"
    error_file=$(mktemp "${WORK_ROOT}/xml_values_err_XXXXXX") || error_exit "не удалось создать временный файл xml_values_err"

    # Эти списки используются только для RAG-поисковых ключей.
    # Отсутствие узлов здесь нормально: в unit может не быть types/variables/routines,
    # а в class может не быть fields/properties/methods.
    # Но настоящие ошибки xmlstarlet, например битый XPath или XML.
    xmlstarlet_sel "$xml_file" -t -m "$xpath" -v "$value_expr" -n > "$values_file" 2> "$error_file"
    status=$?

    if [ "$status" -ne 0 ] && [ -s "$error_file" ]; then
        echo "Ошибка: не удалось извлечь XML-значения: xpath=${xpath}, value=${value_expr}" >&2
        sed -n '1,20p' "$error_file" >&2
        rm -f "$values_file" "$error_file"
        exit 1
    fi

    join_nonempty_lines_csv < "$values_file"
    rm -f "$values_file" "$error_file"
}

write_rag_key_if_not_empty() {
    output_file="$1"
    key="$2"
    value="$3"

    [ -n "$value" ] && echo "- ${key}: ${value}" >> "$output_file"
}

add_unit_rag_search_keys() {
    md_file="$1"
    unit_name="$2"
    source_path="$3"
    xml_file="$4"

    classes=$(xml_values_csv "$xml_file" "//structure[@type='class']" "normalize-space(@name)")
    types=$(xml_values_csv "$xml_file" "//type" "normalize-space(@name)")
    variables=$(xml_values_csv "$xml_file" "//variable[not(parent::structure)]" "normalize-space(@name)")
    routines=$(xml_values_csv "$xml_file" "//routine[not(parent::structure)]" "normalize-space(@name)")

    cat >> "$md_file" <<EOF_MD
## RAG-поисковые ключи

- kind: unit
- id: ${unit_name}
- source_path: ${source_path}
EOF_MD

    write_rag_key_if_not_empty "$md_file" "classes" "$classes"
    write_rag_key_if_not_empty "$md_file" "types" "$types"
    write_rag_key_if_not_empty "$md_file" "variables" "$variables"
    write_rag_key_if_not_empty "$md_file" "routines" "$routines"
    echo "" >> "$md_file"
}

add_class_rag_search_keys() {
    class_md="$1"
    class_name="$2"
    unit_name="$3"
    source_path="$4"
    ancestor_name="$5"
    xml_file="$6"

    structure_type=$(xmlstarlet_sel "$xml_file" -t -v "normalize-space(//structure[@name='${class_name}']/@type)") || \
        error_exit "не удалось извлечь type для structure: ${unit_name}.${class_name}"
    structure_type=$(normalize_inline "$structure_type")
    [ -n "$structure_type" ] || error_exit "не удалось получить type для structure: ${unit_name}.${class_name}"

    methods=$(xml_values_csv "$xml_file" "//structure[@name='${class_name}']/routine" "normalize-space(@name)")
    fields=$(xml_values_csv "$xml_file" "//structure[@name='${class_name}']/variable" "normalize-space(@name)")
    properties=$(xml_values_csv "$xml_file" "//structure[@name='${class_name}']/property" "normalize-space(@name)")

    cat >> "$class_md" <<EOF_MD
## RAG-поисковые ключи

- kind: class
- id: ${unit_name}.${class_name}
- unit: ${unit_name}
- structure_type: ${structure_type}
- source_path: ${source_path}
EOF_MD

    write_rag_key_if_not_empty "$class_md" "ancestor" "$ancestor_name"
    write_rag_key_if_not_empty "$class_md" "methods" "$methods"
    write_rag_key_if_not_empty "$class_md" "fields" "$fields"
    write_rag_key_if_not_empty "$class_md" "properties" "$properties"
    echo "" >> "$class_md"
}

# Добавляет к строкам два служебных поля:
# 1) порядковый номер элемента среди элементов с тем же именем;
# 2) общее количество элементов с тем же именем.
# Это нужно для простых ID вида Create#2 только при повторяющихся именах.
add_duplicate_counters() {
    awk -v sep="$SEP" '
        BEGIN { FS = sep; OFS = sep }
        {
            line[NR] = $0
            name[NR] = $1
            count[$1]++
        }
        END {
            for (i = 1; i <= NR; i++) {
                current = name[i]
                seen[current]++
                print line[i], seen[current], count[current]
            }
        }
    '
}

cleanup() {
    [ -d "$WORK_ROOT" ] && rm -rf "$WORK_ROOT"
}

# =============================
# ОЧИСТКА ТЕКСТА ИЗ XML
# =============================
decode_entities() {
    printf '%s' "$1" | sed \
        -e 's/&lt;/</g' \
        -e 's/&gt;/>/g' \
        -e 's/&quot;/"/g' \
        -e "s/&apos;/'/g" \
        -e 's/&amp;/\&/g'
}

normalize_inline() {
    decoded=$(decode_entities "$1")
    printf '%s' "$decoded" | sed -E \
        -e 's/\r//g' \
        -e 's/[[:space:]]+/ /g' \
        -e 's/^ //' \
        -e 's/ $//'
}

normalize_description() {
    decoded=$(decode_entities "$1")
    printf '%s' "$decoded" | sed -E \
        -e 's/\r//g' \
        -e 's#</?[^>]+># #g' \
        -e 's/[[:space:]]+/ /g' \
        -e 's/^ //' \
        -e 's/ $//'
}

text_or_placeholder() {
    value="$1"
    if [ -z "$value" ]; then
        echo "Нет описания"
    else
        echo "$value"
    fi
}

# =============================
# AI-ОБОГАЩЕНИЕ
# =============================
error_exit() {
    echo "Ошибка: $1" >&2
    exit 1
}

is_true_false() {
    case "$1" in
        true|false) return 0 ;;
        *) return 1 ;;
    esac
}

validate_number() {
    printf '%s' "$1" | grep -Eq '^[0-9]+([.][0-9]+)?$'
}

validate_positive_integer() {
    printf '%s' "$1" | grep -Eq '^[1-9][0-9]*$'
}

resolve_ai_url() {
    case "$AI_PROVIDER" in
        openrouter)
            # Для OpenRouter endpoint фиксирован. AI_URL из окружения/конфига здесь намеренно игнорируется,
            # чтобы не получить противоречивую конфигурацию вроде:
            #   AI_PROVIDER=openrouter + AI_URL=http://127.0.0.1:11434/...
            echo "https://openrouter.ai/api/v1/chat/completions"
            ;;
        openai-compatible)
            [ -n "$AI_URL" ] || error_exit "для AI_PROVIDER=openai-compatible нужно задать AI_URL"
            echo "$AI_URL"
            ;;
        *)
            error_exit "неизвестный AI_PROVIDER: $AI_PROVIDER. Допустимо: openrouter, openai-compatible"
            ;;
    esac
}

validate_ai_config() {
    is_true_false "$AI_ENRICH_UNITS" || error_exit "AI_ENRICH_UNITS должен быть true или false"
    is_true_false "$AI_ENRICH_CLASSES" || error_exit "AI_ENRICH_CLASSES должен быть true или false"
    is_true_false "$AI_ENRICH_METHODS" || error_exit "AI_ENRICH_METHODS должен быть true или false"

    [ -n "$AI_MODEL" ] || error_exit "AI_MODEL не задан. Укажи model id выбранной модели провайдера, например через export AI_MODEL='<model-id>'"
    validate_number "$AI_TEMPERATURE" || error_exit "AI_TEMPERATURE должен быть числом, например 0.1"
    validate_positive_integer "$AI_MAX_TOKENS" || error_exit "AI_MAX_TOKENS должен быть положительным целым числом"

    AI_URL_RESOLVED=$(resolve_ai_url) || exit 1

    case "$AI_PROVIDER" in
        openrouter)
            [ -n "${OPENROUTER_API_KEY:-}" ] || error_exit "для AI_PROVIDER=openrouter нужно задать OPENROUTER_API_KEY"
            ;;
        openai-compatible)
            :
            ;;
    esac

    mkdir -p "$CACHE_DIR" || error_exit "не удалось создать CACHE_DIR: $CACHE_DIR"
}

hash_string() {
    printf '%s' "$1" | md5sum | cut -d' ' -f1
}

get_file_hash() {
    file_path="$1"
    if [ ! -f "$file_path" ]; then
        echo "Ошибка: не найден файл для AI/кэша: $file_path" >&2
        return 1
    fi
    md5sum "$file_path" | cut -d' ' -f1
}

safe_cache_component() {
    printf '%s' "$1" | sed -E 's/[^A-Za-z0-9_.-]+/_/g; s/^_+//; s/_+$//'
}

get_cache_path() {
    file_path="$1"
    unit_name="$2"
    item_type="$3"
    item_name="$4"
    prompt="$5"

    file_hash=$(get_file_hash "$file_path") || return 1
    prompt_hash=$(hash_string "$prompt")
    settings_hash=$(hash_string "${AI_CACHE_SCHEMA_VERSION}|${AI_PROMPT_VERSION}|${AI_PROVIDER}|${AI_URL_RESOLVED}|${AI_MODEL}|${AI_TEMPERATURE}|${AI_MAX_TOKENS}|${prompt_hash}")
    item_hash=$(hash_string "${unit_name}|${item_type}|${item_name}|${file_hash}|${settings_hash}")
    safe_prefix=$(safe_cache_component "${unit_name}_${item_type}_${item_name}")

    # Ограничиваем читаемый префикс, чтобы имена файлов кэша не становились слишком длинными.
    safe_prefix=$(printf '%.80s' "$safe_prefix")
    echo "${CACHE_DIR}/${safe_prefix}_${item_hash}.cache"
}

load_from_cache() {
    cache_file="$1"
    if [ -f "$cache_file" ]; then
        cat "$cache_file"
        return 0
    fi
    return 1
}

save_to_cache() {
    cache_file="$1"
    description="$2"
    printf '%s\n' "$description" > "$cache_file" || error_exit "не удалось записать AI-кэш: $cache_file"
}

strip_ai_response() {
    # Удаляем возможный reasoning-блок у reasoning-моделей и грубые markdown-обёртки.
    sed -e '/<think>/,/<\/think>/d' \
        -e 's/```[[:alnum:]_-]*//g' \
        -e 's/```//g' \
        -e 's/\r//g' \
        -e 's/^[[:space:]]*//' \
        -e 's/[[:space:]]*$//'
}

build_ai_request() {
    request_file="$1"
    prompt="$2"
    file_path="$3"

    "$JQ_BIN" -n \
        --arg model "$AI_MODEL" \
        --arg prompt "$prompt" \
        --rawfile source "$file_path" \
        --argjson temperature "$AI_TEMPERATURE" \
        --argjson max_tokens "$AI_MAX_TOKENS" \
        '{
            model: $model,
            messages: [
                {
                    role: "user",
                    content: ($prompt + "\n\nИсходный файл Delphi/Pascal:\n```pascal\n" + $source + "\n```")
                }
            ],
            temperature: $temperature,
            max_tokens: $max_tokens
        }' > "$request_file" || return 1
}

call_ai_provider() {
    request_file="$1"
    response_file="$2"

    case "$AI_PROVIDER" in
        openrouter)
            curl -sS -L -X POST "$AI_URL_RESOLVED" \
                -H "Content-Type: application/json" \
                -H "Authorization: Bearer ${OPENROUTER_API_KEY}" \
                -d "@$request_file" \
                -o "$response_file" \
                -w '%{http_code}'
            ;;
        openai-compatible)
            if [ -n "${AI_API_KEY:-}" ]; then
                curl -sS -L -X POST "$AI_URL_RESOLVED" \
                    -H "Content-Type: application/json" \
                    -H "Authorization: Bearer ${AI_API_KEY}" \
                    -d "@$request_file" \
                    -o "$response_file" \
                    -w '%{http_code}'
            else
                curl -sS -L -X POST "$AI_URL_RESOLVED" \
                    -H "Content-Type: application/json" \
                    -d "@$request_file" \
                    -o "$response_file" \
                    -w '%{http_code}'
            fi
            ;;
        *)
            return 1
            ;;
    esac
}

extract_ai_content() {
    response_file="$1"
    "$JQ_BIN" -r '
        .choices[0].message.content as $content
        | if ($content | type) == "string" then $content
          elif ($content | type) == "array" then ($content | map(.text? // empty) | join(""))
          else empty end
    ' "$response_file" 2>/dev/null | strip_ai_response
}

generate_ai_description() {
    prompt="$1"
    file_path="$2"
    unit_name="$3"
    item_type="$4"
    item_name="$5"

    cache_file=$(get_cache_path "$file_path" "$unit_name" "$item_type" "$item_name" "$prompt") || return 1
    if cached_desc=$(load_from_cache "$cache_file"); then
        echo "AI cache: ${unit_name}/${item_type}/${item_name}" >&2
        printf '%s\n' "$cached_desc"
        return 0
    fi

    echo "AI generate: ${unit_name}/${item_type}/${item_name}" >&2

    request_file=$(mktemp "${WORK_ROOT}/ai_request_XXXXXX.json") || return 1
    response_file=$(mktemp "${WORK_ROOT}/ai_response_XXXXXX.json") || return 1

    build_ai_request "$request_file" "$prompt" "$file_path" || {
        echo "Ошибка: не удалось сформировать JSON-запрос к ИИ" >&2
        return 1
    }

    http_code=$(call_ai_provider "$request_file" "$response_file") || {
        echo "Ошибка: запрос к ИИ-провайдеру не выполнен" >&2
        return 1
    }

    case "$http_code" in
        2*) ;;
        *)
            echo "Ошибка: ИИ-провайдер вернул HTTP $http_code" >&2
            sed -n '1,20p' "$response_file" >&2
            return 1
            ;;
    esac

    description=$(extract_ai_content "$response_file")
    if [ -z "$description" ] || [ "$description" = "null" ]; then
        echo "Ошибка: ИИ-провайдер вернул пустое описание для ${unit_name}/${item_type}/${item_name}" >&2
        sed -n '1,20p' "$response_file" >&2
        return 1
    fi

    save_to_cache "$cache_file" "$description"
    printf '%s\n' "$description"
}

needs_description() {
    desc="$1"
    min_length="${2:-20}"

    [ -z "$desc" ] && return 0
    [ "$desc" = "..." ] && return 0
    [ "$desc" = "Нет описания" ] && return 0
    [ ${#desc} -lt "$min_length" ] && return 0

    return 1
}

generate_ai_unit_description() {
    unit_name="$1"
    file_path="$2"

    prompt="Ты документируешь Pascal/Delphi-код для wiki разработчика. Дай краткое описание unit ${unit_name}. Опиши назначение модуля и основные сущности. Верни только готовое описание."
    generate_ai_description "$prompt" "$file_path" "$unit_name" "unit" "$unit_name"
}

generate_ai_class_description() {
    class_name="$1"
    unit_name="$2"
    file_path="$3"

    prompt="Ты документируешь Pascal/Delphi-код для wiki разработчика. Дай краткое описание класса ${class_name} из unit ${unit_name}. Опиши роль класса и его основную ответственность. Верни только готовое описание."
    generate_ai_description "$prompt" "$file_path" "$unit_name" "class" "$class_name"
}

generate_ai_method_description() {
    method_name="$1"
    class_name="$2"
    unit_name="$3"
    declaration="$4"
    file_path="$5"
    method_cache_key="${class_name}.${method_name}:${declaration}"

    prompt="Ты документируешь Pascal/Delphi-код для wiki разработчика. Дай краткое описание метода ${class_name}.${method_name} из unit ${unit_name}. Опиши его роль и работу. Если метод перегружен, ориентируйся именно на ${declaration} (объявление метода). Верни только готовое описание."
    generate_ai_description "$prompt" "$file_path" "$unit_name" "method" "$method_cache_key"
}

enrich_unit_description() {
    unit_name="$1"
    desc="$2"
    file_path="$3"

    if [ "$AI_ENRICH_UNITS" = true ] && needs_description "$desc" 20; then
        generate_ai_unit_description "$unit_name" "$file_path"
        return $?
    fi

    text_or_placeholder "$desc"
}

enrich_class_description() {
    class_name="$1"
    unit_name="$2"
    desc="$3"
    file_path="$4"

    if [ "$AI_ENRICH_CLASSES" = true ] && needs_description "$desc" 20; then
        generate_ai_class_description "$class_name" "$unit_name" "$file_path"
        return $?
    fi

    text_or_placeholder "$desc"
}

enrich_method_description() {
    method_name="$1"
    class_name="$2"
    unit_name="$3"
    declaration="$4"
    desc="$5"
    file_path="$6"

    if [ "$AI_ENRICH_METHODS" = true ] && needs_description "$desc" 12; then
        generate_ai_method_description "$method_name" "$class_name" "$unit_name" "$declaration" "$file_path"
        return $?
    fi

    text_or_placeholder "$desc"
}

# =============================
# GENERATE MARKDOWN
# =============================
create_unit_markdown() {
    md_file="$1"
    unit_name="$2"
    unit_desc="$3"
    source_path="$4"
    xml_file="$5"

    cat > "$md_file" <<EOF_MD
# Unit: ${unit_name}

**Исходник:** \`${source_path}\`

EOF_MD

    add_unit_rag_search_keys "$md_file" "$unit_name" "$source_path" "$xml_file"

    cat >> "$md_file" <<EOF_MD
## Общее описание
${unit_desc}

---

## Структуры (классы)
EOF_MD
}

create_class_markdown() {
    class_md="$1"
    class_name="$2"
    class_desc="$3"
    ancestor_name="$4"
    unit_name="$5"
    xml_file="$6"
    source_path="$7"
    ai_source_file="$8"

    class_vis=$(xmlstarlet_sel "$xml_file" -t -v "normalize-space(//structure[@name='${class_name}']/@visibility)" 2>/dev/null || true)
    class_vis=$(normalize_inline "$class_vis")
    class_vis=${class_vis:-public}

    cat > "$class_md" <<EOF_MD
# Класс: ${class_name}

**Наследник:** ${ancestor_name:-нет}
**Видимость:** ${class_vis}
**Источник:** [[${unit_name}]]
**Исходник:** \`${source_path}\`

EOF_MD

    add_class_rag_search_keys "$class_md" "$class_name" "$unit_name" "$source_path" "$ancestor_name" "$xml_file"

    cat >> "$class_md" <<EOF_MD
## Описание
${class_desc}

---

## Иерархия наследования
${class_name}$([ -n "${ancestor_name}" ] && echo " ← ${ancestor_name}")

---
EOF_MD

    echo "" >> "$class_md"
    echo "## Методы" >> "$class_md"
    echo "" >> "$class_md"

    routine_rows=$(mktemp "${WORK_ROOT}/routine_rows_XXXXXX") || error_exit "не удалось создать временный файл routine_rows"
    routine_counted_rows=$(mktemp "${WORK_ROOT}/routine_counted_rows_XXXXXX") || error_exit "не удалось создать временный файл routine_counted_rows"

    xmlstarlet_sel "$xml_file" -t \
        -m "//structure[@name='${class_name}']/routine" \
        -v "normalize-space(@name)" -o "$SEP" \
        -v "normalize-space(@declaration)" -o "$SEP" \
        -v "normalize-space(@visibility)" -o "$SEP" \
        -v "normalize-space(string(description/detailed))" -n 2>/dev/null > "$routine_rows"
    add_duplicate_counters < "$routine_rows" > "$routine_counted_rows"

    while IFS="$SEP" read -r name decl vis desc item_index item_count; do
        name=$(normalize_inline "$name")
        decl=$(normalize_inline "$decl")
        vis=$(normalize_inline "$vis")
        desc=$(normalize_description "$desc")
        desc=$(enrich_method_description "$name" "$class_name" "$unit_name" "$decl" "$desc" "$ai_source_file") || exit 1

        [ -z "$name" ] && continue

        method_id="${unit_name}.${class_name}.${name}"
        [ "${item_count:-0}" -gt 1 ] && method_id="${method_id}#${item_index}"

        echo "### Method: ${class_name}.${name}" >> "$class_md"
        echo "" >> "$class_md"
        echo "**ID:** \`${method_id}\`" >> "$class_md"
        [ -n "$decl" ] && echo "**Объявление:** \`$decl\`" >> "$class_md"
        [ -n "$vis" ] && echo "**Видимость:** $vis" >> "$class_md"
        echo "" >> "$class_md"
        echo "$desc" >> "$class_md"
        echo "" >> "$class_md"
    done < "$routine_counted_rows"

    generate_markdown_section "//structure[@name='${class_name}']/variable" "Поля" "$class_md" "$xml_file" "declaration"
    add_properties "$class_md" "$class_name" "$xml_file"

    cat >> "$class_md" <<EOF_MD

---

**Источник:** [[${unit_name}]]
EOF_MD
}

add_properties() {
    class_md="$1"
    class_name="$2"
    xml_file="$3"

    echo "" >> "$class_md"
    echo "## Свойства" >> "$class_md"
    echo "" >> "$class_md"

    xmlstarlet_sel "$xml_file" -t \
        -m "//structure[@name='${class_name}']/property" \
        -v "normalize-space(@name)" -o "$SEP" \
        -v "normalize-space(@type)" -o "$SEP" \
        -v "normalize-space(@reader)" -o "$SEP" \
        -v "normalize-space(@writer)" -o "$SEP" \
        -v "normalize-space(@visibility)" -o "$SEP" \
        -v "normalize-space(string(description/detailed))" -n 2>/dev/null | \
    add_duplicate_counters | \
    while IFS="$SEP" read -r name type reader writer vis desc item_index item_count; do
        name=$(normalize_inline "$name")
        type=$(normalize_inline "$type")
        reader=$(normalize_inline "$reader")
        writer=$(normalize_inline "$writer")
        vis=$(normalize_inline "$vis")
        desc=$(normalize_description "$desc")
        desc=$(text_or_placeholder "$desc")

        [ -z "$name" ] && continue

        echo "### $name" >> "$class_md"
        echo "" >> "$class_md"
        [ "${item_count:-0}" -gt 1 ] && echo "**ID:** \`${name}#${item_index}\`" >> "$class_md"
        [ -n "$type" ] && echo "**Тип:** $type" >> "$class_md"
        [ -n "$vis" ] && echo "**Видимость:** $vis" >> "$class_md"
        [ -n "$reader" ] && echo "**Reader:** $reader" >> "$class_md"
        [ -n "$writer" ] && echo "**Writer:** $writer" >> "$class_md"
        echo "" >> "$class_md"
        echo "$desc" >> "$class_md"
        echo "" >> "$class_md"
    done
}

generate_markdown_section() {
    xpath="$1"
    title="$2"
    output_file="$3"
    xml_file="$4"

    echo "" >> "$output_file"
    echo "## $title" >> "$output_file"
    echo "" >> "$output_file"

    xmlstarlet_sel "$xml_file" -t \
        -m "$xpath" \
        -v "normalize-space(@name)" -o "$SEP" \
        -v "normalize-space(@declaration)" -o "$SEP" \
        -v "normalize-space(@visibility)" -o "$SEP" \
        -v "normalize-space(string(description/detailed))" -n 2>/dev/null | \
    add_duplicate_counters | \
    while IFS="$SEP" read -r name decl vis desc item_index item_count; do
        name=$(normalize_inline "$name")
        decl=$(normalize_inline "$decl")
        vis=$(normalize_inline "$vis")
        desc=$(normalize_description "$desc")
        desc=$(text_or_placeholder "$desc")

        [ -z "$name" ] && continue

        echo "### $name" >> "$output_file"
        echo "" >> "$output_file"
        [ "${item_count:-0}" -gt 1 ] && echo "**ID:** \`${name}#${item_index}\`" >> "$output_file"
        [ -n "$decl" ] && echo "**Объявление:** \`$decl\`" >> "$output_file"
        [ -n "$vis" ] && echo "**Видимость:** $vis" >> "$output_file"
        echo "" >> "$output_file"
        echo "$desc" >> "$output_file"
        echo "" >> "$output_file"
    done
}

add_types_and_variables() {
    xml_file="$1"
    md_file="$2"
    source_path="$3"

    echo "" >> "$md_file"
    echo "## Типы" >> "$md_file"
    echo "" >> "$md_file"

    xmlstarlet_sel "$xml_file" -t \
        -m "//type" \
        -v "normalize-space(@name)" -o "$SEP" \
        -v "normalize-space(@declaration)" -o "$SEP" \
        -v "normalize-space(string(description/detailed))" -n 2>/dev/null | \
    add_duplicate_counters | \
    while IFS="$SEP" read -r name decl desc item_index item_count; do
        name=$(normalize_inline "$name")
        decl=$(normalize_inline "$decl")
        desc=$(normalize_description "$desc")
        desc=$(text_or_placeholder "$desc")

        [ -z "$name" ] && continue

        if [ "${item_count:-0}" -gt 1 ]; then
            echo "- **$name** \`${name}#${item_index}\` — \`$decl\`" >> "$md_file"
        else
            echo "- **$name** — \`$decl\`" >> "$md_file"
        fi
        echo "  - $desc" >> "$md_file"
        echo "" >> "$md_file"
    done

    echo "" >> "$md_file"
    echo "## Переменные уровня unit" >> "$md_file"
    echo "" >> "$md_file"

    xmlstarlet_sel "$xml_file" -t \
        -m "//variable[not(parent::structure)]" \
        -v "normalize-space(@name)" -o "$SEP" \
        -v "normalize-space(@declaration)" -o "$SEP" \
        -v "normalize-space(@visibility)" -o "$SEP" \
        -v "normalize-space(string(description/detailed))" -n 2>/dev/null | \
    add_duplicate_counters | \
    while IFS="$SEP" read -r name decl vis desc item_index item_count; do
        name=$(normalize_inline "$name")
        decl=$(normalize_inline "$decl")
        vis=$(normalize_inline "$vis")
        desc=$(normalize_description "$desc")
        desc=$(text_or_placeholder "$desc")

        [ -z "$name" ] && continue

        if [ "${item_count:-0}" -gt 1 ]; then
            echo "- **$name** \`${name}#${item_index}\` (\`${vis:-public}\`): \`$decl\`" >> "$md_file"
        else
            echo "- **$name** (\`${vis:-public}\`): \`$decl\`" >> "$md_file"
        fi
        echo "  - $desc" >> "$md_file"
    done

    echo "" >> "$md_file"
    echo "---" >> "$md_file"
    echo "*Сгенерировано из: ${source_path}*" >> "$md_file"
}

process_classes() {
    xml_file="$1"
    wiki_dir="$2"
    unit_name="$3"
    source_path="$4"
    md_file="$5"
    ai_source_file="$6"

    class_rows=$(mktemp "${WORK_ROOT}/class_rows_XXXXXX") || error_exit "не удалось создать временный файл class_rows"
    xmlstarlet_sel "$xml_file" -t \
        -m "//structure[@type='class']" \
        -v "normalize-space(@name)" -o "$SEP" \
        -v "normalize-space(string(description/detailed))" -o "$SEP" \
        -v "normalize-space(string(ancestor/@name))" -n 2>/dev/null > "$class_rows"

    while IFS="$SEP" read -r class_name class_desc ancestor_name; do
        class_name=$(normalize_inline "$class_name")
        class_desc=$(normalize_description "$class_desc")
        class_desc=$(enrich_class_description "$class_name" "$unit_name" "$class_desc" "$ai_source_file") || exit 1
        ancestor_name=$(normalize_inline "$ancestor_name")

        [ -z "$class_name" ] && continue

        page_name=$(class_page_name "$unit_name" "$class_name")
        class_link=$(class_wikilink "$unit_name" "$class_name")
        class_md="$wiki_dir/${page_name}.md"

        # Имя class-файла уже содержит unit, поэтому коллизии одноимённых классов из разных unit не сливаются.
        create_class_markdown "$class_md" "$class_name" "$class_desc" "$ancestor_name" "$unit_name" "$xml_file" "$source_path" "$ai_source_file"
        {
            echo "### Class: ${class_name}"
            echo ""
            echo "**Ссылка:** ${class_link}"
            echo "**Наследник:** ${ancestor_name:-нет}"
            echo "${class_desc}"
            echo ""
        } >> "$md_file"
    done < "$class_rows"
}

process_xml_file() {
    xml_file="$1"
    wiki_dir="$2"
    unit_name="$3"
    pascal_file="$4"
    ai_source_file="$5"

    source_path=$(make_source_path_display "$pascal_file")
    md_file="$wiki_dir/${unit_name}.md"
    unit_desc=$(xmlstarlet_sel "$xml_file" -t -v "normalize-space(string(/unit/description/detailed))" 2>/dev/null || true)
    unit_desc=$(normalize_description "$unit_desc")
    unit_desc=$(enrich_unit_description "$unit_name" "$unit_desc" "$ai_source_file") || exit 1

    create_unit_markdown "$md_file" "$unit_name" "$unit_desc" "$source_path" "$xml_file"
    process_classes "$xml_file" "$wiki_dir" "$unit_name" "$source_path" "$md_file" "$ai_source_file"
    add_types_and_variables "$xml_file" "$md_file" "$source_path"
}

process_single_pascal_file() {
    file_path="$1"
    doc_dir="$2"
    wiki_dir="$3"

    unit_name=$(extract_unit_name "$file_path")
    base_name=$(basename "$file_path")
    base_name=${base_name%.pas}
    base_name=${base_name%.pp}

    staged_file=$(make_ascii_stage_file "$file_path")
    cp "$file_path" "$staged_file" || error_exit "не удалось скопировать файл в staging: $file_path"

    pasdoc_list="$doc_dir/temp_${base_name}.inc"
    xml_output_dir="$doc_dir/xml_temp_${base_name}"
    pasdoc_log="$xml_output_dir/pasdoc.log"

    mkdir -p "$xml_output_dir"

    staged_file_win=$(to_win_path "$staged_file")
    pasdoc_list_win=$(to_win_path "$pasdoc_list")
    xml_output_dir_win=$(to_win_path "$xml_output_dir")

    printf '%s\n' "$staged_file_win" > "$pasdoc_list"

    "$PASDOC_PROG" \
        --output "$xml_output_dir_win" \
        --format="$PASDOC_OUTPUT_FORMAT" \
        --source "$pasdoc_list_win" \
        --define HAS_GRAPHVIZ=false > "$pasdoc_log" 2>&1 || true

    xml_file=$(find "$xml_output_dir" -type f -name "*.xml" | head -1)

    if [ -f "$xml_file" ]; then
        process_xml_file "$xml_file" "$wiki_dir" "$unit_name" "$file_path" "$staged_file"
        echo "OK: $unit_name"
    else
        echo "WARN: XML не сгенерирован для $file_path"
        if [ -f "$pasdoc_log" ]; then
            echo "----- PasDoc log: $pasdoc_log -----"
            sed -n '1,80p' "$pasdoc_log"
            echo "-----------------------------------"
        fi
    fi

    rm -f "$pasdoc_list"
    rm -f "$staged_file"
    rm -rf "$xml_output_dir"
}

create_index_file() {
    wiki_dir="$1"
    home_file="$wiki_dir/Home.md"

    cat > "$home_file" <<EOF_MD
# Документация проекта

## Unit'ы (модули)
EOF_MD

    find "$wiki_dir" -maxdepth 1 -type f -name "*.md" ! -name "Home.md" | sort | while read -r md; do
        if grep -q '^# Unit:' "$md"; then
            name=$(basename "$md" .md)
            [ -n "$name" ] && echo "- [[${name}]]" >> "$home_file"
        fi
    done

    cat >> "$home_file" <<EOF_MD

## Классы
EOF_MD

    find "$wiki_dir" -maxdepth 1 -type f -name "*.md" ! -name "Home.md" | sort | while read -r md; do
        if grep -q '^# Класс:' "$md"; then
            page_name=$(basename "$md" .md)
            class_title=$(sed -n 's/^# Класс: //p' "$md" | head -1)
            class_title=${class_title:-$page_name}
            echo "- [[${page_name}|${class_title}]]" >> "$home_file"
        fi
    done
}

validate_descriptions() {
    wiki_dir="$1"

    echo "Проверка описаний..."

    find "$wiki_dir" -maxdepth 1 -type f -name "*.md" ! -name "Home.md" ! -name ".md" | while read -r md; do
        if grep -q 'Нет описания' "$md"; then
            echo "  ПРЕДУПРЕЖДЕНИЕ: $md содержит пропущенные описания"
        fi
    done
}

validate_wiki_structure() {
    wiki_dir="$1"

    echo "Проверка структуры wiki..."

    empty_md_count=$(find "$wiki_dir" -maxdepth 1 -type f -name "*.md" -size 0 | wc -l | xargs)
    if [ "$empty_md_count" -gt 0 ]; then
        echo "  ПРЕДУПРЕЖДЕНИЕ: найдены пустые markdown-файлы: $empty_md_count"
    fi

    unit_count=$(find "$wiki_dir" -maxdepth 1 -type f -name "*.md" ! -name "Home.md" -exec grep -l '^# Unit:' {} \; | wc -l | xargs)
    class_count=$(find "$wiki_dir" -maxdepth 1 -type f -name "*.md" ! -name "Home.md" -exec grep -l '^# Класс:' {} \; | wc -l | xargs)

    echo "  Unit-файлов: $unit_count"
    echo "  Class-файлов: $class_count"
}

# =============================
# ОСНОВНАЯ ЛОГИКА
# =============================
check_dependencies
validate_ai_config
mkdir -p "$DOC_DIR" "$STAGE_DIR" "$WIKI_DIR" "$CACHE_DIR"
trap cleanup EXIT

# Нормализуем PROJECT_ROOT после проверки существования, чтобы относительные пути были стабильнее.
PROJECT_ROOT=$(printf '%s' "$PROJECT_ROOT" | sed 's#\\#/#g')
PROJECT_ROOT=${PROJECT_ROOT%/}

echo "CONFIG_FILE: $CONFIG_FILE"
echo "CONFIG_LOADED: $CONFIG_LOADED"
echo "PROJECT_ROOT: $PROJECT_ROOT"
echo "PASDOC_PROG: $PASDOC_PROG"
echo "XMLSTARLET_BIN: $XMLSTARLET_BIN"
echo "JQ_BIN: $JQ_BIN"
echo "WORK_ROOT: $WORK_ROOT"
echo "DOC_DIR: $DOC_DIR"
echo "STAGE_DIR: $STAGE_DIR"
echo "WIKI_DIR: $WIKI_DIR"
echo "AI_PROVIDER: $AI_PROVIDER"
echo "AI_URL: $AI_URL_RESOLVED"
echo "AI_MODEL: $AI_MODEL"
echo "AI_ENRICH_UNITS: $AI_ENRICH_UNITS"
echo "AI_ENRICH_CLASSES: $AI_ENRICH_CLASSES"
echo "AI_ENRICH_METHODS: $AI_ENRICH_METHODS"
echo "CACHE_DIR: $CACHE_DIR"
echo ""

total=0
pascal_file_list=$(mktemp "${WORK_ROOT}/pascal_files_XXXXXX") || error_exit "не удалось создать временный список Pascal-файлов"
get_pascal_file_list > "$pascal_file_list" || error_exit "не удалось получить список Pascal-файлов"

while read -r pascal_file; do
    [ -z "$pascal_file" ] && continue
    total=$((total + 1))
    echo "[$total] Обработка: $pascal_file"
    process_single_pascal_file "$pascal_file" "$DOC_DIR" "$WIKI_DIR"
done < "$pascal_file_list"

create_index_file "$WIKI_DIR"
validate_descriptions "$WIKI_DIR"
validate_wiki_structure "$WIKI_DIR"

echo ""
echo "Готово. Wiki создана в: $WIKI_DIR"
