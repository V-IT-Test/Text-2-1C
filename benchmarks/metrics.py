"""
Метрики для оценки качества NL-to-1C запросов.

EV  — Execution Validity (Валидность выполнения).
      1 = запрос выполнился в 1С без ошибки, 0 = ошибка исполнения.

EX  — Execution Accuracy (Точность выполнения).
      1 = результат полностью совпадает с эталоном (без учета порядка строк), 0 = несовпадение.

CM  — Component Matching (Совпадение компонентов).
      F1-мера по пересечению множеств ключевых слов языка запросов 1С (ВЫБРАТЬ, ИЗ, СГРУППИРОВАТЬ ПО и др.)
      и объектных ссылок (Справочник.Товары, Документ.ЗаказТовара.Состав и др.)
      между сгенерированным и эталонным запросом. Диапазон [0, 1].

SM  — Semantic Match (Семантическое соответствие).
      1 = LLM-судья (gpt-4.1-mini) считает, что результат отвечает на исходный вопрос, 0 = не отвечает.
      Вызывается только при EV=1 и EX=0 для экономии API-вызовов.

EXS — EX or SM (Итоговая семантическая корректность).
      1 если EX=1 или SM=1, иначе 0. Агрегирует точный и семантический критерии.
"""
import json
import re

# 1C query language keywords used in component matching

# 1C query language keywords used in component matching
_KEYWORDS = {
    # Excluded as semantically equivalent / default forms:
    #   КАК (alias optional), ВОЗР (default ASC),
    #   ВНЕШНЕЕ (ЛЕВОЕ ВНЕШНЕЕ ≡ ЛЕВОЕ), АВТОУПОРЯДОЧИВАНИЕ (optional directive)
    "ВЫБРАТЬ", "РАЗЛИЧНЫЕ", "ПЕРВЫЕ", "РАЗРЕШЕННЫЕ",
    "ИЗ", "ГДЕ", "ПО",
    "НЕ", "И", "ИЛИ", "ПОДОБНО", "В", "МЕЖДУ", "ЕСТЬ",
    "СГРУППИРОВАТЬ", "УПОРЯДОЧИТЬ", "ИМЕЮЩИЕ",
    "ИТОГИ", "ОБЩИЕ", "ОБЪЕДИНИТЬ", "ВСЕ",
    "СОЕДИНЕНИЕ", "ВНУТРЕННЕЕ", "ЛЕВОЕ", "ПРАВОЕ", "ПОЛНОЕ",
    "УБЫВ", "ИЕРАРХИЯ",
    # aggregates
    "СУММА", "КОЛИЧЕСТВО", "МИНИМУМ", "МАКСИМУМ", "СРЕДНЕЕ",
    # date functions
    "ДАТАВРЕМЯ", "ГОД", "МЕСЯЦ", "КВАРТАЛ", "ДЕНЬГОДА", "ДЕНЬНЕДЕЛИ",
    "ДЕНЬ", "ЧАС", "МИНУТА", "СЕКУНДА",
    "НАЧАЛОПЕРИОДА", "КОНЕЦПЕРИОДА", "ДОБАВИТЬКДАТЕ", "РАЗНОСТЬДАТ",
    # string functions
    "ПОДСТРОКА", "ДЛИНАСТРОКИ", "ВРЕГ", "НРЕГ",
    "СОКРЛП", "СОКРЛ", "СОКРП", "СТРНАЙТИ", "СТРЗАМЕНИТЬ",
    # CASE
    "ВЫБОР", "КОГДА", "ТОГДА", "ИНАЧЕ", "КОНЕЦ",
    # other
    "ЕСТЬNULL", "NULL", "ЗНАЧЕНИЕ", "ПРЕДСТАВЛЕНИЕ",
    "ТИП", "ССЫЛКА", "ВЫРАЗИТЬ", "ИСТИНА", "ЛОЖЬ",
}


# ── helpers ──────────────────────────────────────────────────────────────────

def _normalize_rows(rows: list[dict]) -> list[tuple]:
    """Sort rows as tuples for order-insensitive comparison."""
    tuples = [tuple(sorted(str(v) for v in row.values())) for row in rows]
    return sorted(tuples)


def _extract_components(query: str) -> set[str]:
    """Return keyword + dotted-reference tokens from a 1C query."""
    tokens = re.split(r"[\s,;()\n\t\r]+", query.upper())
    result: set[str] = set()
    for tok in tokens:
        tok = tok.strip(".")
        if not tok:
            continue
        if tok in _KEYWORDS:
            result.add(tok)
        elif "." in tok:
            # object references: Справочник.Товары, РегистрНакопления.ОстаткиТоваров.Остатки
            result.add(tok)
    return result


# ── public metrics ────────────────────────────────────────────────────────────

def execution_validity(error: str | None) -> float:
    """EV: 1 if the query executed without error, 0 otherwise."""
    return 0.0 if error else 1.0


def execution_accuracy(
    ref_rows: list[dict],
    gen_rows: list[dict],
    gen_error: str | None,
) -> float:
    """EX: 1 if result sets match (order-insensitive), 0 otherwise."""
    if gen_error:
        return 0.0
    return 1.0 if _normalize_rows(ref_rows) == _normalize_rows(gen_rows) else 0.0


def component_matching(ref_query: str, gen_query: str) -> float:
    """CM: F1 over shared keyword + object-reference tokens."""
    if not gen_query:
        return 0.0
    ref = _extract_components(ref_query)
    gen = _extract_components(gen_query)
    if not ref and not gen:
        return 1.0
    if not ref or not gen:
        return 0.0
    tp = len(ref & gen)
    precision = tp / len(gen)
    recall = tp / len(ref)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


# ── semantic match (LLM) ──────────────────────────────────────────────────────

_SM_SYSTEM = """Ты проверяешь, соответствует ли результат запроса вопросу пользователя.
Правила:
- 1 — результат ПОЛНОСТЬЮ отвечает на вопрос (данные верны и достаточны).
- 0 — результат НЕ отвечает (пусто, неверные данные, неполный ответ, ошибка).
- Игнорируй технические названия колонок, смотри только на смысл значений.
- Если вопрос про подсчёт — в результате должно быть число, а не список строк.
- Если вопрос про список — результат должен содержать ожидаемые сущности.
Отвечай одной цифрой: 1 или 0. Без пояснений."""


def semantic_match(question: str, gen_rows: list[dict], gen_error: str | None,
                   gen_query: str = "", model: str = "gpt-4.1-mini") -> float:
    """SM: 1 if LLM judges result rows to answer the user question, else 0.
    
    Optimisation: skipped if EV=0 (returns 0) or EX=1 (returns 1).
    """
    if gen_error:
        return 0.0
    if not gen_rows:
        return 0.0

    # Truncate rows to keep prompt small
    rows_str = json.dumps(gen_rows[:20], ensure_ascii=False, indent=2)
    if len(rows_str) > 2000:
        rows_str = rows_str[:2000] + "..."

    prompt = (
        f"Вопрос: {question}\n"
        f"Результат выполнения запроса:\n{rows_str}"
    )

    try:
        from llm_client import ask_llm
        answer = ask_llm(prompt, system=_SM_SYSTEM, model=model).strip()
        return 1.0 if answer.startswith("1") else 0.0
    except Exception:
        return 0.0
