import re
from llm_client import ask_llm

_LINKER_SYSTEM = (
    "Ты помогаешь выбрать нужные объекты схемы базы 1С для запроса пользователя. "
    "По запросу пользователя и полной схеме базы назови список объектов, "
    "которые понадобятся для формирования запроса. "
    "Возвращай только список технических имён объектов, каждый на новой строке, "
    "без пояснений и заголовков. Например:\n"
    "Документ.ПриемНаРаботу\n"
    "Справочник.Сотрудники\n"
    "Перечисление.ПричиныИзмененияСостояний"
)

_OBJECT_PREFIX = re.compile(
    r"^(Документ|Справочник|РегистрСведений|РегистрНакопления|РегистрБухгалтерии|Перечисление)\."
)


def filter_schema(user_query: str, full_schema: str, log_fn=None) -> str:
    """Ask LLM which schema objects are needed, return filtered schema text."""
    if not full_schema.strip():
        return full_schema

    def log(msg):
        if log_fn:
            log_fn(msg)

    prompt = f"Схема базы данных:\n{full_schema}\n\nЗапрос пользователя: {user_query}"
    response = ask_llm(prompt, system=_LINKER_SYSTEM)
    log(f"Schema linking: LLM выбрал объекты: {response.strip()[:200]}")

    needed = set()
    for line in response.splitlines():
        name = line.strip().lstrip("•-*0123456789.) ").strip()
        if _OBJECT_PREFIX.match(name):
            needed.add(name.lower())

    if not needed:
        log("Schema linking: объекты не определены, используется полная схема.")
        return full_schema

    filtered = _filter_schema_text(full_schema, needed)
    log(f"Schema linking: передано {len(needed)} объект(ов) вместо полной схемы.")
    return filtered


def _filter_schema_text(schema: str, needed: set) -> str:
    """Return schema with only the objects whose technical names are in `needed`."""
    lines = schema.splitlines()
    result_lines: list[str] = []
    pending_section: str | None = None  # section header waiting to see if it has content
    current_obj_lines: list[str] = []
    current_obj_relevant = False

    def flush_obj():
        if current_obj_relevant:
            result_lines.extend(current_obj_lines)

    for line in lines:
        if line.startswith("## ") or line.startswith("# "):
            # Flush previous object
            flush_obj()
            current_obj_lines = []
            current_obj_relevant = False
            # Defer section header — write it only when we write a relevant object
            pending_section = line
        elif _OBJECT_PREFIX.match(line):
            flush_obj()
            current_obj_lines = [line]
            match = re.match(r"^(\S+)", line)
            obj_name = match.group(1).lower() if match else ""
            current_obj_relevant = obj_name in needed
            if current_obj_relevant and pending_section is not None:
                result_lines.append(pending_section)
                pending_section = None
        elif line.startswith("  ") or line == "":
            # Continuation of current object's attributes
            if current_obj_lines:
                current_obj_lines.append(line)
            # else: blank line between sections, skip
        else:
            # Non-indented non-object line (e.g. "# Схема базы данных 1С")
            flush_obj()
            current_obj_lines = []
            current_obj_relevant = False
            result_lines.append(line)

    flush_obj()

    # Remove trailing blank lines
    while result_lines and result_lines[-1].strip() == "":
        result_lines.pop()

    return "\n".join(result_lines)
