# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Goal

Master's thesis: **"Преобразование естественного языка в язык запросов 1С"**
(Natural Language to 1C Query Language conversion)

The project converts free-form Russian text into valid 1C:Enterprise 8.3 query language (similar to SQL) via LLM. The research angle involves experimenting with different pipeline configurations and comparing their effectiveness (ablation study).

See [research/methods_discussion.md](research/methods_discussion.md) for the ranked list of 14 improvement techniques — the backbone of the thesis ablation study. Methods #1–#6 are already implemented as toggleable pipeline modules.

## Environment

- **OS:** Windows 10 Pro x64
- **Two venvs** (both required):
  - `venv` — 32-bit Python 3.11, has `pywin32`. Used only for the COM bridge.
  - `venv64` — 64-bit Python, has `streamlit`, `openai`. Used for the UI and everything else.
- **1C version:** 8.3.27.1936 (Developer edition)
- **1C COM DLL:** `C:\Program Files (x86)\1cv8\8.3.27.1936\bin\comcntr.dll` (registered via `C:\Windows\SysWOW64\regsvr32`)
- **1C configurator binary:** `C:\Program Files (x86)\1cv8\8.3.27.1936\bin\1cv8.exe` (auto-detected by `config.py`)
  - `1cv8.exe DESIGNER` — opens configurator. **Not** `1cv8c.exe` (thin client) and **not** `CONFIG` keyword.
  - `/F` path must be a **separate argument**, not concatenated — Cyrillic paths break otherwise.
- **1C test database:** `C:\Users\Дарья\Documents\1CBASE\TestBD` (file-based, no server)

## Running the project

```bash
# Run the UI (always from venv64)
venv64\Scripts\activate
streamlit run ui/app.py
```

The 32-bit `venv` is used automatically by `pipeline/executor.py` via subprocess — never activate it manually for the UI.

## Architecture

### Two-venv bridge pattern
64-bit UI/LLM code cannot load the 32-bit COM DLL. Solution: `pipeline/executor.py` spawns `executor_bridge.py` as a subprocess using the 32-bit `venv` Python. Communication is via stdin/stdout JSON.

```
ui/app.py  (venv64)
  → pipeline/executor.py     spawns subprocess →  executor_bridge.py  (venv, 32-bit)
                                                        ↓ COM
                                                   1C database
```

### Pipeline modules

All modules are independently toggleable in the UI sidebar. Each corresponds to a thesis experiment method.

```
UserInput
    → [SchemaLoader]        # exports XML from 1C, compiles to compact Markdown
    → [AmbiguityResolver]   # optional: ask user clarifying questions
    → [SchemaLinker]        # LLM selects relevant schema objects, filters schema.md
    → [ValueFetcher]        # queries live DB for sample rows, enriches schema context
    → LLMTranslator         # core: NL text → 1C query language
        ↳ modes: basic prompt / advanced prompt / CoT / QueryPlan
    → [ExecutionFeedback]   # auto-executes query, feeds errors back to LLM (up to 2 retries)
    → 1CExecutor            # execute final query via COM bridge, return rows
```

**Order of schema enrichment inside `translate()`:**
1. `filter_schema()` (schema linking) — LLM selects relevant objects, reduces schema
2. `enrich_schema_with_values()` (value fetching) — fetches sample rows only from filtered objects
3. Final prompt is built and sent to LLM

### LLM translation modes (query_translator.py)

All modes are mutually-exclusive or stackable as noted:

| Toggle | Behaviour | LLM calls |
|--------|-----------|-----------|
| Basic prompt | Minimal system prompt | 1 |
| Advanced prompt | Full 1C syntax rules in system prompt | 1 |
| Chain-of-Thought | Adds step-by-step reasoning suffix; extracts `<query>` tag | 1 |
| Query Plan | Two-step: plan in Russian → query from plan (mutually exclusive with CoT) | 2 |
| Schema linking | Extra LLM call to select relevant schema objects | +1 |
| Value-based linking | Script queries DB for sample rows (no LLM) | 0 extra LLM |
| Execution feedback | Execute → on error: re-ask LLM with error text, max 2 retries | +0–2 |

### Available LLM models (config.py `LLM_MODELS`)

| Label | Model ID | Tier |
|-------|----------|------|
| gpt-5.4 (мощная) | `gpt-5.4` | Premium |
| gpt-5.4-mini (средняя) | `gpt-5.4-mini` | Standard |
| gpt-4o-mini (лёгкая) | `gpt-4o-mini` | Standard — **default** |
| o4-mini (думающая) | `o4-mini` | Reasoning — ~10× cost |

API endpoint: proxyapi.ru (OpenAI-compatible). `ask_llm(prompt, system, model)` accepts an optional `model` override; falls back to `gpt-4o-mini`.

### Schema pipeline (SchemaLoader)

1. `pipeline/xml_exporter.py` — calls `1cv8.exe DESIGNER /F <path> /DumpConfigToFiles` to export XMLConfiguration into `databases/<db_key>/XMLConfiguration/`
2. `pipeline/schema_compiler2.py` — parses XML files, produces compact Markdown schema (~3 KB vs MB of XML)
3. `pipeline/schema_loader.py` — orchestrates export → compile → cache. Saves result to `databases/<db_key>/DBStructure/schema.md`

Schema storage layout (all inside the project, not inside the 1C database directory):
```
databases/<db_key>/
  config.json               ← connection string, display name
  XMLConfiguration/         ← gitignored, generated by 1cv8.exe DESIGNER
  DBStructure/
    schema.md               ← compiled compact Markdown schema, can be committed
```

The UI button «Выгрузить XML» triggers re-export. Schema-dependent toggles are disabled until `schema.md` exists.

### Schema format (v1, see evolvhist/)

The compiled schema includes per object:
- Technical name + Russian synonym: `РегистрСведений.ЦеныНоменклатуры (Цены номенклатуры)`
- For registers: **Dimensions** / **Resources** / **Attributes** are separated
- For periodic registers: available virtual tables (`СрезПоследних`, `СрезПервых`)
- For enums: all values with synonyms
- Type mapping: `xs:decimal` → `Число`, `cfg:CatalogRef.X` → `Справочник.X`, etc.
- When value-based linking is active: `Примеры данных (N шт.): [col=val, ...]; ...` appended per object

## Key files

| File | Purpose |
|------|---------|
| `config.py` | Feature flags (`PIPELINE`), `LLM_MODELS` dict, `ONEC_BIN` auto-detection, `load_databases()` |
| `llm_client.py` | OpenAI-compatible client via proxyapi.ru, `ask_llm(prompt, system, model)` |
| `executor_bridge.py` | 32-bit COM bridge: reads JSON from stdin, returns rows via stdout |
| `pipeline/executor.py` | Spawns bridge subprocess, passes query, returns rows |
| `pipeline/query_translator.py` | Builds LLM prompt, orchestrates all translation modes, calls `ask_llm()` |
| `pipeline/schema_linker.py` | LLM-based schema filtering: selects relevant objects for the query |
| `pipeline/value_fetcher.py` | Fetches sample rows (`SELECT FIRST 4 *`) from all filtered DB objects |
| `pipeline/xml_exporter.py` | Calls `1cv8.exe DESIGNER` to dump XMLConfiguration |
| `pipeline/schema_compiler2.py` | Parses XMLConfiguration XML → compact Markdown schema |
| `pipeline/schema_loader.py` | Orchestrates export/compile/cache, reads `schema.md` |
| `ui/app.py` | Streamlit UI (venv64): sidebar toggles, model selector, live logs, query editor, results |
| `evolvhist/` | History of schema format variants (for thesis comparison) |
| `research/` | Thesis research notes: methods ranking, experiment plans, source references |

## 1C-specific notes

- **Язык запросов** (query language) ≠ **встроенный язык** (scripting language). LLM must generate only query language: `ВЫБРАТЬ ... ИЗ ... ГДЕ ...`. Never assignments, loops, or object methods.
- COM connection: `V83.COMConnector`. Always `del connection` in `finally` to release the file lock.
- `executor_bridge._to_json()` converts COM values to JSON-serializable types with this fallback chain:
  1. Python primitives and datetime — direct conversion
  2. `val.Пустая()` → `None` (empty reference, avoids returning type metadata as value)
  3. `Наименование` / `Код` / `Представление` / `НаименованиеПолное` — catalogs and most refs
  4. `Номер` + `Дата` → `"№000001 от 15.03.2026"` — document references (`Регистратор`)
  5. `val.Метаданные().Синоним` / `.Имя` — enum values (`ПричинаИзмененияСостояния`)
  6. `str(val)` — last resort
- `1cv8.exe` output is cp1251 on Windows — decode accordingly.
- Enum values in queries must use `ЗНАЧЕНИЕ(Перечисление.X.Y)` syntax — never compare with strings.
- Periodic info registers must use `СрезПоследних()` / `СрезПервых()` virtual tables.
