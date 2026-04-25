import re
from pipeline.executor import execute

# All queryable object types (Перечисления already in schema as static values)
_OBJECT_RE = re.compile(
    r"^((?:Документ|Справочник|РегистрСведений|РегистрНакопления|РегистрБухгалтерии)\.\w+)",
    re.MULTILINE,
)

# Standard fields that don't carry useful example data for the LLM
_SKIP_FIELDS = {"Ссылка", "ПометкаУдаления"}


def enrich_schema_with_values(
    schema_md: str,
    conn_str: str,
    top_n: int = 4,
    log_fn=None,
) -> str:
    """Fetch sample rows for every queryable object and append to its schema block."""
    def log(msg):
        if log_fn:
            log_fn(msg)

    objects = _OBJECT_RE.findall(schema_md)
    if not objects:
        return schema_md

    enriched = schema_md
    for obj in objects:
        try:
            rows = execute(conn_str, f"ВЫБРАТЬ ПЕРВЫЕ {top_n} * ИЗ {obj}")
            if rows:
                enriched = _insert_sample_rows(enriched, obj, rows)
                log(f"Value-based: {obj} → {len(rows)} записей")
            else:
                log(f"Value-based: {obj} — нет данных")
        except Exception as e:
            log(f"Value-based: {obj} — ошибка: {str(e)[:120]}")

    return enriched


def _format_rows(rows: list[dict]) -> str:
    parts = []
    for row in rows:
        fields = ", ".join(
            f"{k}={v}"
            for k, v in row.items()
            if k not in _SKIP_FIELDS and v not in (None, "", False)
        )
        if fields:
            parts.append(f"[{fields}]")
    return "; ".join(parts)


def _insert_sample_rows(schema_md: str, obj: str, rows: list[dict]) -> str:
    sample_line = f"  Примеры данных ({len(rows)} шт.): {_format_rows(rows)}"
    lines = schema_md.splitlines()
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith(obj) and (
            len(line) == len(obj) or line[len(obj)] in (" ", "\t")
        ):
            result.append(line)
            i += 1
            while i < len(lines) and lines[i].startswith("  "):
                result.append(lines[i])
                i += 1
            result.append(sample_line)
        else:
            result.append(line)
            i += 1
    return "\n".join(result)
