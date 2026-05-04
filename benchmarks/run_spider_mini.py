"""
Execute all 50 query_1C entries from spider_data/mini_spider/questions.json
against the corresponding 1C databases and save results.

Usage (from project root, venv64 active):
    python benchmarks/run_spider_mini.py
"""
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

QUESTIONS_FILE = ROOT / "spider_data" / "mini_spider" / "questions.json"
RESULTS_DIR = ROOT / "benchmarks" / "results"

MAX_ROWS_IN_JSON = 20  # cap stored rows per query to keep JSON readable


def load_conn(db_id: str) -> str:
    cfg_path = ROOT / "databases" / db_id / "config.json"
    if not cfg_path.exists():
        raise FileNotFoundError(f"No config.json for db_id='{db_id}' at {cfg_path}")
    with open(cfg_path, encoding="utf-8") as f:
        return json.load(f)["connection_string"]


def main() -> None:
    from pipeline.executor import execute

    with open(QUESTIONS_FILE, encoding="utf-8") as f:
        questions = json.load(f)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = RESULTS_DIR / f"spider_mini_execution_{ts}.json"
    csv_path  = RESULTS_DIR / f"spider_mini_execution_{ts}.csv"

    records = []
    ok_count = 0

    for idx, q in enumerate(questions, start=1):
        db_id    = q["db_id"]
        query_1c = q["query_1C"]
        question = q["question"]
        difficulty = q.get("difficulty", "")

        sys.stdout.write(f"[{idx:2d}/50] {question[:55]:<55} ... ")
        sys.stdout.flush()

        status = "OK"
        error  = None
        rows: list[dict] = []
        row_count = 0

        try:
            conn = load_conn(db_id)
        except FileNotFoundError as e:
            status = "NO_DB"
            error  = str(e)

        if status == "OK":
            try:
                rows = execute(conn, query_1c)
                row_count = len(rows)
                ok_count += 1
                print(f"OK  ({row_count} rows)")
            except Exception as e:
                status = "ERROR"
                error  = str(e)
                print(f"ERR  {error[:80]}")
        else:
            print(f"NO_DB  {error[:80]}")

        records.append({
            "id":         idx,
            "db_id":      db_id,
            "difficulty": difficulty,
            "question":   question,
            "query_1C":   query_1c,
            "status":     status,
            "row_count":  row_count,
            "rows":       rows[:MAX_ROWS_IN_JSON],
            "error":      error,
        })

    # ── save JSON ──────────────────────────────────────────────────────────────
    json_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # ── save CSV (without raw rows) ────────────────────────────────────────────
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["id", "db_id", "difficulty", "question", "query_1C",
                        "status", "row_count", "error"],
        )
        writer.writeheader()
        for r in records:
            writer.writerow({k: r[k] for k in writer.fieldnames})

    # ── summary ────────────────────────────────────────────────────────────────
    by_status: dict[str, int] = {}
    for r in records:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1

    print(f"\n{'=' * 60}")
    print(f"Total: {len(records)}   OK: {ok_count}   "
          + "  ".join(f"{k}: {v}" for k, v in sorted(by_status.items()) if k != "OK"))
    print(f"JSON : {json_path}")
    print(f"CSV  : {csv_path}")


if __name__ == "__main__":
    main()
