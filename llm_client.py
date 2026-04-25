import os
from openai import OpenAI

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_KEY = os.getenv("PROXYAPI_KEY")
BASE_URL = os.getenv("PROXYAPI_BASE_URL", "https://api.proxyapi.ru/openai/v1")
MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

if not API_KEY:
    raise RuntimeError(
        "Не задана переменная окружения PROXYAPI_KEY. "
        "Скопируй .env.example в .env и пропиши свой ключ "
        "(или экспортируй переменную в окружении)."
    )

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


def ask_llm(prompt: str, system: str = "", model: str = MODEL) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    answer = ask_llm("Скажи 'подключение работает' и ничего больше.")
    print(answer)
