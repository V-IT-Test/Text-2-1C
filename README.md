# Text → 1C Query

Преобразование запросов пользователя на естественном языке в запросы
к базам данных 1С с использованием больших языковых моделей.

Магистерская работа: исследование подходов к задаче преобразования
естественного языка в запросы 1С (аналог Text-to-SQL) методами
in-context learning без дообучения моделей.
Каркас построен как ablation-стенд: каждый подход реализован отдельным
модулем и включается/выключается тумблером в UI, что позволяет сравнивать
эффект от каждой техники по отдельности.

## Возможности

- Перевод текста на русском в синтаксис языка запросов 1С.
- Опциональная подгрузка схемы базы (Markdown, ~3 КБ вместо мегабайтов XML).
- Schema linking — фильтрация схемы LLM-агентом перед генерацией.
- Value-based linking — обогащение схемы примерами реальных значений из базы.
- Chain-of-Thought и Query Plan — режимы пошагового рассуждения.
- Critic-агент — отдельная LLM-проверка сгенерированного запроса.
- Execution feedback — автоматическая отправка ошибок 1С обратно в LLM
  для исправления (до 2 итераций).
- Три уровня системного промпта (базовый / полный продвинутый / краткий продвинутый).
- Выбор модели LLM из UI (gpt-4o-mini, gpt-5.4, o4-mini, DeepSeek и др.).

## Стек

- **Python 3.11** (две сборки — 64-bit и 32-bit, см. ниже)
- **Streamlit** — UI
- **OpenAI Python SDK** — клиент к OpenAI-совместимому прокси (proxyapi.ru)
- **pywin32** — мост к COM-объекту `V83.COMConnector` для выполнения запросов
- **1С:Предприятие 8.3** (8.3.20+) — целевая платформа

## Архитектура двух venv

64-битный Python не может загрузить 32-битную DLL `comcntr.dll` от 1С.
Решение — два изолированных окружения:

```
ui/app.py  (venv64, 64-bit)
  → pipeline/executor.py     spawns subprocess →  executor_bridge.py  (venv, 32-bit)
                                                        ↓ COM
                                                   1C database
```

Связь между процессами — JSON через stdin/stdout.

## Установка

### 1. Клонирование

```bash
git clone <url>
cd Text_2_1CQuery
```

### 2. Окружения

Нужно **два** venv-а: 64-битный для UI/LLM и 32-битный для COM-моста.

```bash
# 64-битный (основной)
py -3.11 -m venv venv64
venv64\Scripts\activate
pip install -r requirements.txt
deactivate

# 32-битный (для COM-моста к 1С)
"C:\Program Files (x86)\Python311-32\python.exe" -m venv venv
venv\Scripts\activate
pip install -r requirements-32bit.txt
deactivate
```

### 3. Регистрация COM-объекта 1С

```cmd
C:\Windows\SysWOW64\regsvr32 "C:\Program Files (x86)\1cv8\<версия>\bin\comcntr.dll"
```

### 4. API-ключ

```bash
copy .env.example .env
# открой .env и пропиши свой PROXYAPI_KEY
```

### 5. Конфигурация базы

В `databases/<имя_базы>/config.json` должен быть путь к файлу базы 1С:

```json
{
    "name": "Тестовая база",
    "connection_string": "File=\"C:\\Users\\<имя>\\Documents\\1CBASE\\<база>\";"
}
```

### 6. Запуск

```bash
venv64\Scripts\activate
streamlit run ui/app.py
```

В UI выбрать базу и нажать «Выгрузить XML» — это запустит конфигуратор 1С,
который выгрузит описание метаданных в `databases/<база>/XMLConfiguration/`,
после чего пайплайн скомпилирует сжатую Markdown-схему в `DBStructure/schema.md`.

## Структура проекта

| Путь | Назначение |
|------|------------|
| `ui/app.py` | Streamlit-интерфейс: тумблеры пайплайна, выбор модели, лог |
| `pipeline/query_translator.py` | Ядро перевода: системные промпты, режимы CoT/QueryPlan, критик, execution feedback |
| `pipeline/schema_loader.py` | Кэширование/выгрузка схемы |
| `pipeline/xml_exporter.py` | Запуск `1cv8.exe DESIGNER /DumpConfigToFiles` |
| `pipeline/schema_compiler2.py` | Парсинг XML → компактный Markdown |
| `pipeline/schema_linker.py` | LLM-фильтр объектов схемы под конкретный запрос |
| `pipeline/value_fetcher.py` | Подкачка примеров значений из базы (без LLM) |
| `pipeline/critic.py` | LLM-критик сгенерированного запроса |
| `pipeline/executor.py` | Запуск 32-битного моста, парсинг JSON-ответа |
| `executor_bridge.py` | 32-битный COM-мост: получает JSON, отдаёт строки |
| `llm_client.py` | Обёртка OpenAI-клиента, ключ из `.env` |
| `config.py` | Список моделей, фиче-флаги, обнаружение `1cv8.exe` |
| `evolvhist/` | История форматов компактной схемы (для сравнения в работе) |
| `databases/<key>/` | Конфиг базы, выгруженная XML, скомпилированная Markdown-схема |
