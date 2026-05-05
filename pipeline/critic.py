from llm_client import ask_llm

_CRITIC_SYSTEM = """Ты критик 1С-запросов. Проверяй сгенерированный запрос по двум осям:

1. Соответствие намерению пользователя — правильные таблицы, условия, группировки, агрегации?
2. Корректность синтаксиса 1С — ВЫБРАТЬ/ИЗ/ГДЕ, русские агрегаты (СУММА/КОЛИЧЕСТВО и т.д.),
   двойные кавычки для строк, ЗНАЧЕНИЕ() для перечислений, ПЕРВЫЕ вместо TOP/LIMIT,
   КАК вместо AS, виртуальные таблицы регистров (СрезПоследних), отсутствие SQL-конструкций.

Если запрос корректен — ответь ТОЛЬКО одним словом: OK
Если есть проблемы — опиши их кратко по пунктам (без исправленного запроса)."""


def review_query(
    user_query: str,
    schema_context: str,
    query: str,
    model: str = "",
    log_fn=None,
    use_full_rules: bool = False,
) -> tuple[bool, str]:
    """Critique a generated 1C query.

    Returns (is_ok, critique_text). If is_ok=True, critique_text is empty.
    """
    def log(msg):
        if log_fn:
            log_fn(msg)

    system = _CRITIC_SYSTEM
    if use_full_rules:
        from pipeline.query_translator import SYSTEM_ADVANCED
        system = SYSTEM_ADVANCED + "\n\nТвоя задача сейчас — ТОЛЬКО проверить сгенерированный запрос ниже. Если запрос корректен — ответь ТОЛЬКО одним словом: OK. Если есть проблемы — опиши их кратко по пунктам (без исправленного запроса)."

    parts = []
    if schema_context:
        parts.append(f"Схема базы данных:\n{schema_context}")
    parts.append(f"Запрос пользователя: {user_query}")
    parts.append(f"Сгенерированный 1С-запрос:\n{query}")
    prompt = "\n\n".join(parts)

    kw = {"model": model} if model else {}
    response = ask_llm(prompt, system=system, **kw).strip()

    is_ok = response.upper().startswith("OK")
    if not is_ok:
        log(f"Критик: найдены замечания — {response[:150]}")
    return is_ok, response
