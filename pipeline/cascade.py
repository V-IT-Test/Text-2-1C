"""
Model cascade: cheap-first routing.

If the main model is more expensive than gpt-4o-mini, try gpt-4o-mini first.
If it produces EV=1 and (EX=1 or SM=1), skip the main model.
"""
from typing import Any

CASCADE_MODEL = "gpt-4o-mini"


def try_cascade(
    question: str,
    conn: str,
    ref_rows: list[dict],
    shared: dict[str, Any],
    main_model: str,
    use_ef: bool,
) -> dict[str, Any] | None:
    """Try gpt-4o-mini first. Returns result dict if cascade succeeded, None otherwise.

    Result keys: gen_query, gen_rows, cascade_exs_val, cascade_ex_val
    """
    from pipeline.query_translator import translate, translate_with_feedback
    from pipeline.executor import execute
    from benchmarks.metrics import execution_validity, execution_accuracy, semantic_match

    if not main_model or main_model == CASCADE_MODEL:
        return None

    cascade_shared = dict(shared, model=CASCADE_MODEL)
    try:
        if use_ef:
            c_query, _ = translate_with_feedback(question, conn, **cascade_shared)
        else:
            c_query = translate(question, conn_str=conn, **cascade_shared)
    except Exception:
        return None

    if not c_query:
        return None

    c_error = None
    try:
        c_rows = execute(conn, c_query)
    except Exception as e:
        c_rows = []
        c_error = str(e)

    c_ev = execution_validity(c_error)
    c_ex = execution_accuracy(ref_rows, c_rows, c_error)
    cascade_ex_val = c_ex

    if c_ev == 1 and c_ex == 1:
        return {
            "gen_query": c_query,
            "gen_rows": c_rows,
            "cascade_exs_val": 1.0,
            "cascade_ex_val": cascade_ex_val,
        }
    elif c_ev == 1 and c_ex == 0:
        c_sm = semantic_match(question, c_rows, None, c_query)
        cascade_exs_val = 1.0 if c_sm == 1 else 0.0
        if c_sm == 1:
            return {
                "gen_query": c_query,
                "gen_rows": c_rows,
                "cascade_exs_val": cascade_exs_val,
                "cascade_ex_val": cascade_ex_val,
            }
        return {
            "gen_query": "",
            "gen_rows": [],
            "cascade_exs_val": cascade_exs_val,
            "cascade_ex_val": cascade_ex_val,
            "_cascade_failed": True,
        }

    return {
        "gen_query": "",
        "gen_rows": [],
        "cascade_exs_val": 0.0,
        "cascade_ex_val": cascade_ex_val,
        "_cascade_failed": True,
    }
