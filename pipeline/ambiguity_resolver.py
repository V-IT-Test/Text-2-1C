from llm_client import ask_llm

SYSTEM = (
    "Ты помощник, который уточняет запросы пользователя к базе данных 1С. "
    "Если запрос однозначен — ответь 'OK'. "
    "Если есть неоднозначность — задай один уточняющий вопрос."
)


def resolve(user_query: str) -> str:
    """Return clarifying question or 'OK' if query is unambiguous."""
    return ask_llm(user_query, system=SYSTEM)
