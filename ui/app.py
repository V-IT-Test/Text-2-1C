import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from config import load_databases, PIPELINE, DATABASES_DIR, LLM_MODELS
from pipeline.schema_loader import load_schema
from pipeline.query_translator import translate, translate_with_feedback
from pipeline.executor import execute

st.set_page_config(page_title="Text → 1C Query", layout="wide")
st.markdown("""
<style>
/* Narrower sidebar */
[data-testid="stSidebar"] { min-width: 220px !important; max-width: 220px !important; }
/* Smaller text inside sidebar */
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stToggle label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span { font-size: 0.78rem !important; }
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { font-size: 0.9rem !important; }
/* Compact dataframe */
[data-testid="stDataFrame"] table { font-size: 0.75rem !important; }
[data-testid="stDataFrame"] th,
[data-testid="stDataFrame"] td { padding: 2px 6px !important; white-space: nowrap; }
</style>
""", unsafe_allow_html=True)
st.title("Преобразование текстового запроса в язык запросов 1С")

databases = load_databases()
db_names = {v["name"]: k for k, v in databases.items()}


def schema_file_path(db_key: str) -> Path:
    return DATABASES_DIR / db_key / "DBStructure" / "schema.md"


# --- Боковая панель ---
with st.sidebar:
    st.header("Настройки")

    db_name = st.selectbox("База данных", list(db_names.keys()))

    selected_model_label = st.selectbox("Модель LLM", list(LLM_MODELS.keys()), index=2)  # default: gpt-4o-mini
    selected_model = LLM_MODELS[selected_model_label]

    db_key = db_names[db_name]
    conn_str = databases[db_key]["connection_string"]
    schema_exists = schema_file_path(db_key).exists()

    if st.button("Выгрузить XML", help="Выгрузить XML из 1С и сформировать сжатую схему базы"):
        with st.spinner("Экспортирую конфигурацию из 1С (может занять минуту)..."):
            try:
                load_schema(db_key, conn_str, force_export=True)
                st.success("Схема выгружена и сформирована.")
                schema_exists = True
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка экспорта: {e}")

    if not schema_exists:
        st.caption("⚠️ Схема не загружена. Нажмите «Выгрузить XML».")

    st.markdown("---")
    st.subheader("Модули пайплайна")

    use_schema = st.toggle(
        "Передавать схему в LLM",
        value=PIPELINE["schema_loader"] and schema_exists,
        disabled=not schema_exists,
        help="Недоступно — сначала нажмите «Выгрузить XML»" if not schema_exists else None,
    )
    def _on_advanced_change():
        if st.session_state.use_advanced_prompt:
            st.session_state.use_advanced_short = False

    def _on_advanced_short_change():
        if st.session_state.use_advanced_short:
            st.session_state.use_advanced_prompt = False

    use_advanced_prompt = st.toggle(
        "Продвинутый промпт (полный)",
        value=True,
        key="use_advanced_prompt",
        on_change=_on_advanced_change,
        help="Полная версия: все конструкции языка запросов 1С + 7 развёрнутых примеров",
    )
    use_advanced_short = st.toggle(
        "Продвинутый промпт (краткий)",
        key="use_advanced_short",
        on_change=_on_advanced_short_change,
        help="Сжатая версия продвинутого промпта — быстрее и дешевле, но без детальных примеров",
    )

    def _on_cot_change():
        if st.session_state.use_cot:
            st.session_state.use_query_plan = False

    def _on_query_plan_change():
        if st.session_state.use_query_plan:
            st.session_state.use_cot = False

    use_cot = st.toggle(
        "Chain-of-Thought",
        key="use_cot",
        on_change=_on_cot_change,
        help="LLM рассуждает пошагово перед генерацией запроса (1 вызов LLM)",
    )
    use_query_plan = st.toggle(
        "Query Plan",
        key="use_query_plan",
        on_change=_on_query_plan_change,
        help="Сначала строится план на русском, затем по нему запрос (2 вызова LLM)",
    )

    use_schema_linking = st.toggle(
        "Schema linking",
        disabled=not schema_exists,
        help="Доп. вызов LLM перед генерацией: выбирает только нужные объекты схемы. Недоступно без схемы." if not schema_exists else "Доп. вызов LLM определяет, какие объекты схемы нужны для запроса, и фильтрует schema.md",
    )
    use_value_linking = st.toggle(
        "Value-based linking",
        disabled=not schema_exists,
        help="Недоступно без схемы." if not schema_exists else "Перед генерацией запрашивает из 1С примеры значений справочников и добавляет их в схему",
    )
    use_critic = st.toggle(
        "Критик-агент",
        help="После генерации отдельный вызов LLM проверяет логику запроса и при необходимости исправляет его",
    )
    use_execution_feedback = st.toggle(
        "Execution feedback",
        help="Запрос автоматически тестируется в 1С после генерации; при ошибке LLM исправляет его (до 2 попыток)",
    )
    use_cascade = st.toggle(
        "Model cascade",
        value=PIPELINE["use_cascade"],
        help="Если выбрана модель мощнее gpt-4o-mini: сначала генерируем gpt-4o-mini, выполняем, проверяем SM. Если результат верен — не тратим основную модель.",
    )

if "query_editor" not in st.session_state:
    st.session_state.query_editor = ""
if "logs" not in st.session_state:
    st.session_state.logs = []

# --- Основная область ---
col_left, col_right = st.columns([2, 1]) if use_ambiguity else (st.container(), None)

with col_left:
    user_query = st.text_area(
        "Запрос на естественном языке",
        height=100,
        placeholder="Например: покажи всех принятых на работу в 2026 году",
    )

    if st.button("Сгенерировать запрос 1С", type="primary"):
        if not user_query.strip():
            st.warning("Введите запрос.")
        else:
            st.session_state.logs = []
            _log_placeholder = st.empty()

            def add_log(msg):
                st.session_state.logs.append(msg)
                _log_placeholder.code(
                    "\n".join(f"[{i+1:02d}] {m}" for i, m in enumerate(st.session_state.logs)),
                    language=None,
                )

            with st.spinner("Перевожу запрос..."):
                schema_context = load_schema(db_key) if use_schema else ""
                if use_schema and schema_context:
                    add_log("Схема выгружена из файла.")
                if use_execution_feedback:
                    query, iterations = translate_with_feedback(
                        user_query,
                        conn_str,
                        schema_context,
                        advanced_prompt=use_advanced_prompt,
                        advanced_short=use_advanced_short,
                        use_cot=use_cot,
                        use_query_plan=use_query_plan,
                        use_schema_linking=use_schema_linking,
                        use_value_linking=use_value_linking,
                        use_critic=use_critic,
                        model=selected_model,
                        log_fn=add_log,
                    )
                    st.session_state.query_editor = query
                else:
                    st.session_state.query_editor = translate(
                        user_query,
                        schema_context,
                        advanced_prompt=use_advanced_prompt,
                        advanced_short=use_advanced_short,
                        use_cot=use_cot,
                        use_query_plan=use_query_plan,
                        use_schema_linking=use_schema_linking,
                        use_value_linking=use_value_linking,
                        use_critic=use_critic,
                        conn_str=conn_str,
                        model=selected_model,
                        log_fn=add_log,
                    )

    st.subheader("Сформированный запрос 1С")
    edited_query = st.text_area(
        "Можно отредактировать перед выполнением",
        height=150,
        key="query_editor",
    )

    if st.button("Выполнить запрос в 1С"):
        if not edited_query.strip():
            st.warning("Запрос пустой.")
        else:
            with st.spinner("Выполняю запрос в 1С..."):
                try:
                    rows = execute(conn_str, edited_query)
                    st.subheader(f"Результат ({len(rows)} записей)")
                    if rows:
                        st.dataframe(rows, use_container_width=True)
                    else:
                        st.info("Нет данных.")
                except Exception as e:
                    st.error(f"Ошибка выполнения: {e}")

    if st.session_state.logs:
        with st.expander("Лог выполнения", expanded=True):
            st.code("\n".join(f"[{i+1:02d}] {msg}" for i, msg in enumerate(st.session_state.logs)), language=None)

if use_ambiguity and col_right is not None:
    with col_right:
        st.subheader("Чат для уточнений")

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        chat_input = st.chat_input("Напишите уточнение...")
        if chat_input:
            from llm_client import ask_llm
            st.session_state.chat_history.append({"role": "user", "content": chat_input})
            answer = ask_llm(chat_input)
            st.session_state.chat_history.append({"role": "assistant", "content": answer})
            st.rerun()
