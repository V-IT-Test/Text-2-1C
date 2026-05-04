"""
Batch benchmark runner for NL-to-1C evaluation.

Commands:
    # Step 1 – execute all reference queries and save ground truth
    python benchmarks/runner.py --generate-reference

    # Step 2 – run a specific experiment (requires --generate-reference done first)
    python benchmarks/runner.py --run schema_only

    # Run every experiment defined in the config
    python benchmarks/runner.py --run-all

    # Print per-experiment summary table (EV / EX / CM)
    python benchmarks/runner.py --report

    # Build per-model question matrix, save JSON + CSV
    python benchmarks/runner.py --question-matrix
"""
import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEFAULT_CONFIG = ROOT / "benchmarks" / "benchmark_config.yaml"


# ── config helpers ────────────────────────────────────────────────────────────

def _load_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_benchmark(cfg: dict) -> list[dict]:
    path = ROOT / cfg["benchmark_file"]
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_reference(cfg: dict) -> dict[int, dict]:
    path = ROOT / cfg["reference_results"]
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return {e["id"]: e for e in json.load(f)}


def _conn_str(cfg: dict, db_id: str = None) -> str:
    from config import load_databases
    dbs = load_databases()
    key = db_id or cfg.get("database", "")
    if not key or key not in dbs:
        raise KeyError(f"Database key '{key}' not found in databases/*/config.json")
    return dbs[key]["connection_string"]


# Schema cache for multi-DB benchmarks
_schema_cache: dict[str, str] = {}

def _ensure_schema(cfg: dict, conn: str, db_id: str = None) -> str:
    """Load schema.md, auto-exporting from 1C if it doesn't exist yet."""
    from pipeline.schema_loader import load_schema, schema_path
    key = db_id or cfg.get("database", "")
    if not key:
        return ""
    if key in _schema_cache:
        return _schema_cache[key]
    if not schema_path(key).exists():
        print(f"Schema not found for '{key}' — exporting from 1C (this may take a minute)...")
    schema = load_schema(key, conn)
    _schema_cache[key] = schema
    return schema


# ── generate reference ────────────────────────────────────────────────────────

def generate_reference(cfg: dict) -> None:
    """Execute every reference query and persist ground-truth rows."""
    from pipeline.executor import execute

    benchmark = _load_benchmark(cfg)
    out = ROOT / cfg["reference_results"]
    out.parent.mkdir(parents=True, exist_ok=True)

    # Cache connections per db_id
    conn_cache: dict[str, str] = {}
    
    results = []
    ok = 0
    for entry in benchmark:
        qid = entry["id"]
        db_id = entry.get("db_id", cfg.get("database", ""))
        sys.stdout.write(f"[{qid:2d}/{len(benchmark)}] {entry['question'][:55]}... ")
        sys.stdout.flush()
        try:
            if db_id not in conn_cache:
                conn_cache[db_id] = _conn_str(cfg, db_id)
            conn = conn_cache[db_id]
            rows = execute(conn, entry["reference_query"])
            results.append({
                "id": qid,
                "db_id": db_id,
                "question": entry["question"],
                "reference_query": entry["reference_query"],
                "rows": rows,
                "error": None,
            })
            ok += 1
            print(f"OK ({len(rows)} rows)")
        except Exception as e:
            results.append({
                "id": qid,
                "db_id": db_id,
                "question": entry["question"],
                "reference_query": entry["reference_query"],
                "rows": [],
                "error": str(e),
            })
            print(f"ERROR: {e}")

    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDone: {ok}/{len(results)} succeeded. Saved to {out}")


# ── run experiment ────────────────────────────────────────────────────────────

def run_experiment(cfg: dict, exp_name: str) -> None:
    """Generate queries via LLM for one experiment config and compute metrics."""
    exp = next((e for e in cfg["experiments"] if e["name"] == exp_name), None)
    if exp is None:
        sys.exit(f"Experiment '{exp_name}' not found in config.")

    from pipeline.query_translator import translate, translate_with_feedback
    from pipeline.executor import execute
    from benchmarks.metrics import execution_validity, execution_accuracy, component_matching, semantic_match

    benchmark = _load_benchmark(cfg)
    ref = _load_reference(cfg)

    # Cache connections and schemas per db_id
    conn_cache: dict[str, str] = {}
    schema_cache: dict[str, str] = {}
    use_schema = exp.get("use_schema", False)

    use_ef = exp.get("use_exec_feedback", False)
    n_total = len(benchmark)

    question_results = []
    for entry in benchmark:
        qid = entry["id"]
        db_id = entry.get("db_id", cfg.get("database", ""))
        sys.stdout.write(f"[{qid:2d}/{n_total}] {entry['question'][:50]}... ")
        sys.stdout.flush()

        # Per-entry connection
        if db_id not in conn_cache:
            conn_cache[db_id] = _conn_str(cfg, db_id)
        conn = conn_cache[db_id]

        # Per-entry schema
        if use_schema and db_id not in schema_cache:
            schema_cache[db_id] = _ensure_schema(cfg, conn, db_id)
        schema = schema_cache.get(db_id, "")

        shared = dict(
            schema_context=schema,
            advanced_prompt=exp.get("advanced_prompt", False),
            advanced_short=exp.get("advanced_short", False),
            use_cot=exp.get("use_cot", False),
            use_query_plan=exp.get("use_query_plan", False),
            use_schema_linking=exp.get("use_schema_linking", False),
            use_value_linking=exp.get("use_value_linking", False),
            use_critic=exp.get("use_critic", False),
            model=exp.get("model", ""),
        )

        ref_rows = ref.get(qid, {}).get("rows", [])
        gen_query = ""
        gen_error = None
        gen_rows: list[dict] = []

        try:
            if use_ef:
                gen_query, _ = translate_with_feedback(
                    entry["question"], conn, **shared
                )
            else:
                gen_query = translate(entry["question"], conn_str=conn, **shared)
        except Exception as e:
            gen_error = f"LLM error: {e}"

        if gen_query and not gen_error:
            try:
                gen_rows = execute(conn, gen_query)
            except Exception as e:
                gen_error = str(e)

        ev = execution_validity(gen_error)
        ex = execution_accuracy(ref_rows, gen_rows, gen_error)
        cm = component_matching(entry["reference_query"], gen_query)
        # SM: call LLM only if EV=1 and EX=0; otherwise derive
        if ev == 0:
            sm = 0.0
        elif ex == 1:
            sm = 1.0
        else:
            sm = semantic_match(entry["question"], gen_rows, gen_error, gen_query)
        exs = 1.0 if (ex == 1 or sm == 1) else 0.0

        question_results.append({
            "id": qid,
            "db_id": db_id,
            "question": entry["question"],
            "reference_query": entry["reference_query"],
            "generated_query": gen_query,
            "ev": ev,
            "ex": ex,
            "cm": round(cm, 4),
            "sm": sm,
            "exs": exs,
            "error": gen_error,
        })
        print(f"EV={ev:.0f} EX={ex:.0f} CM={cm:.2f} SM={sm:.0f} EXS={exs:.0f}")

    n = len(question_results)
    summary = {
        "ev": round(sum(r["ev"] for r in question_results) / n, 4),
        "ex": round(sum(r["ex"] for r in question_results) / n, 4),
        "cm": round(sum(r["cm"] for r in question_results) / n, 4),
        "sm": round(sum(r["sm"] for r in question_results) / n, 4),
        "exs": round(sum(r["exs"] for r in question_results) / n, 4),
    }
    print(f"\nSummary: EV={summary['ev']:.3f}  EX={summary['ex']:.3f}  CM={summary['cm']:.3f}  SM={summary['sm']:.3f}  EXS={summary['exs']:.3f}")

    results_dir = ROOT / "benchmarks" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = results_dir / f"{exp_name}_{ts}.json"
    out.write_text(
        json.dumps(
            {
                "run_name": exp_name,
                "model": exp.get("model", "gpt-4o-mini"),
                "config": exp,
                "timestamp": datetime.now().isoformat(),
                "questions": question_results,
                "summary": summary,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Saved to {out}")


# ── question matrix ──────────────────────────────────────────────────────────

def _config_key(config_dict: dict) -> str:
    """Derive a pipeline configuration key from enabled modules."""
    parts = []
    if config_dict.get("use_schema"): parts.append("+schema")
    if config_dict.get("advanced_prompt"): parts.append("+adv")
    elif config_dict.get("advanced_short"): parts.append("+short")
    if config_dict.get("use_cot"): parts.append("+cot")
    if config_dict.get("use_query_plan"): parts.append("+qp")
    if config_dict.get("use_schema_linking"): parts.append("+sl")
    if config_dict.get("use_value_linking"): parts.append("+vl")
    if config_dict.get("use_critic"): parts.append("+critic")
    if config_dict.get("use_exec_feedback"): parts.append("+ef")
    return "".join(parts) if parts else "base"


def _print_module_matrix(
    config_label: str, models: list[str], questions: list[dict]
) -> None:
    """Print a matrix: rows=questions, columns=models, right=EV/EX counters, bottom=averages."""
    n_models = len(models)
    col_w = max(max((len(m) for m in models), default=4), 5)
    Q = 40
    ev_col_w = 3
    ex_col_w = 3

    # Header
    model_header = " ".join(f"{m:^{col_w}}" for m in models)
    line = f" {'#':>2} | {'Question':<{Q}} | {model_header} | EV | EX | SM |EXS"
    sep = "-" * len(line)
    print(f"\nPipeline: {config_label}  ({len(questions)} questions, {n_models} models)")
    print(sep)
    print(line)
    print(sep)

    # Compute per-model EV/EX/SM sums
    model_ev_sum = {m: 0.0 for m in models}
    model_ex_sum = {m: 0.0 for m in models}
    model_sm_sum = {m: 0.0 for m in models}
    model_exs_sum = {m: 0.0 for m in models}
    model_count = {m: 0 for m in models}

    for q in questions:
        cells = []
        ev_ok = 0
        ex_ok = 0
        sm_ok = 0
        exs_ok = 0
        n_tested = 0
        for m in models:
            r = q["results"].get(m)
            if r is None:
                cells.append(f"{'—':^{col_w}}")
            else:
                ex_val = r["ex"]
                symbol = "1" if ex_val == 1 else "0"
                cells.append(f"{symbol:^{col_w}}")
                model_ev_sum[m] += r["ev"]
                model_ex_sum[m] += r["ex"]
                model_sm_sum[m] += r.get("sm", 0)
                model_exs_sum[m] += r.get("exs", 0)
                model_count[m] += 1
                if r["ev"] == 1:
                    ev_ok += 1
                if r["ex"] == 1:
                    ex_ok += 1
                if r.get("sm", 0) == 1:
                    sm_ok += 1
                if r.get("exs", 0) == 1:
                    exs_ok += 1
                n_tested += 1

        ev_str = f"{ev_ok}/{n_tested}" if n_tested else "—"
        ex_str = f"{ex_ok}/{n_tested}" if n_tested else "—"
        sm_str = f"{sm_ok}/{n_tested}" if n_tested else "—"
        exs_str = f"{exs_ok}/{n_tested}" if n_tested else "—"
        cells_str = " ".join(cells)
        print(f" {q['id']:>2} | {q['question'][:Q]:<{Q}} | {cells_str} | {ev_str:>3} | {ex_str:>3} | {sm_str:>3} | {exs_str:>3}")

    # Bottom summary row
    def _fmt(v):
        s = f"{v:.2f}"
        return s.replace("0.",".").replace("1.00","1.0")
    
    print(sep)
    summary_cells = []
    for m in models:
        cnt = model_count[m]
        ex_avg = model_ex_sum[m] / cnt if cnt else 0
        summary_cells.append(_fmt(ex_avg)[:col_w])
    ev_total = sum(model_ev_sum[m] for m in models)
    ex_total = sum(model_ex_sum[m] for m in models)
    sm_total = sum(model_sm_sum[m] for m in models)
    exs_total = sum(model_exs_sum[m] for m in models)
    total_cnt = sum(model_count[m] for m in models)
    ev_all = ev_total / total_cnt if total_cnt else 0
    ex_all = ex_total / total_cnt if total_cnt else 0
    sm_all = sm_total / total_cnt if total_cnt else 0
    exs_all = exs_total / total_cnt if total_cnt else 0

    cells_str = " ".join(f"{c:^{col_w}}" for c in summary_cells)
    print(f" {'':>2} | {'AVG':<{Q}} | {cells_str} | {ev_all:.2f} | {ex_all:.2f} | {sm_all:.2f} | {exs_all:.2f}")
    print(sep)


def question_matrix(cfg: dict) -> None:
    """Build/update persistent matrix: one file with all pipeline configs, models, runs."""
    results_dir = ROOT / "benchmarks" / "results"
    matrices_dir = ROOT / "benchmarks" / "matrices"
    matrix_file = matrices_dir / "matrix_all.json"
    matrices_dir.mkdir(parents=True, exist_ok=True)

    if not results_dir.exists() or not any(results_dir.glob("*.json")):
        print("No experiment results found. Run --run or --run-all first.")
        return

    benchmark = _load_benchmark(cfg)

    # Load existing persistent matrix (if any)
    persistent: dict = {}
    if matrix_file.exists():
        persistent = json.loads(matrix_file.read_text(encoding="utf-8"))

    # Scan result files and group by (config_key, model, version)
    from collections import defaultdict
    config_data: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))

    for f in sorted(results_dir.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        model = data.get("model", "unknown")
        exp_cfg = data.get("config", {})
        ck = _config_key(exp_cfg)
        config_data[ck][model].append({
            "ts": data.get("timestamp", ""),
            "run_name": data.get("run_name", ""),
            "questions": {q["id"]: q for q in data["questions"]},
        })

    # Merge into persistent storage
    for ck in sorted(config_data):
        if ck not in persistent:
            persistent[ck] = {}
        for m in sorted(config_data[ck].keys()):
            runs = config_data[ck][m]
            if m not in persistent[ck]:
                persistent[ck][m] = []
            # Replace or append: match by run_name + ts to avoid duplicates
            for run in runs:
                found = False
                for i, existing in enumerate(persistent[ck][m]):
                    if existing.get("ts") == run["ts"] and existing.get("run_name") == run["run_name"]:
                        persistent[ck][m][i] = run
                        found = True
                        break
                if not found:
                    persistent[ck][m].append(run)

    # Print matrices
    for ck in sorted(persistent):
        if not persistent[ck]:
            continue
        # Build column labels with versioning
        col_labels: list[str] = []
        col_refs: list[tuple[str, int]] = []
        for m in sorted(persistent[ck].keys()):
            runs = persistent[ck][m]
            if len(runs) == 1:
                col_labels.append(m)
                col_refs.append((m, 0))
            else:
                for vi in range(len(runs)):
                    col_labels.append(f"{m} v{vi+1}")
                    col_refs.append((m, vi))

        matrix_qs: list[dict] = []
        for entry in benchmark:
            qid = entry["id"]
            q_results = {}
            for (m, vi), label in zip(col_refs, col_labels):
                qd = persistent[ck][m][vi]["questions"].get(qid)
                q_results[label] = {"ev": qd["ev"], "ex": qd["ex"], "cm": qd["cm"],
                                     "sm": qd.get("sm", 0), "exs": qd.get("exs", 0)} if qd else None
            matrix_qs.append({
                "id": qid,
                "question": entry["question"],
                "results": q_results,
            })

        _print_module_matrix(ck, col_labels, matrix_qs)

    # Save persistent matrix
    matrix_file.write_text(json.dumps(persistent, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nMatrix saved: {matrix_file}")


# ── report ────────────────────────────────────────────────────────────────────

def show_report(_cfg: dict) -> None:
    """Print a metrics matrix from the latest saved result per experiment."""
    results_dir = ROOT / "benchmarks" / "results"
    if not results_dir.exists() or not any(results_dir.glob("*.json")):
        print("No saved results found.")
        return

    latest: dict[str, dict] = {}
    for f in results_dir.glob("*.json"):
        data = json.loads(f.read_text(encoding="utf-8"))
        name = data["run_name"]
        if name not in latest or data["timestamp"] > latest[name]["timestamp"]:
            latest[name] = data

    col = 38
    header = f"{'Configuration':<{col}} {'Model':<18} {'EV':>6} {'EX':>6} {'CM':>6} {'SM':>6} {'EXS':>6}"
    print(header)
    print("-" * len(header))
    for name, data in sorted(latest.items()):
        s = data["summary"]
        print(
            f"{name:<{col}} {data.get('model', '?'):<18}"
            f" {s['ev']:>6.3f} {s['ex']:>6.3f} {s['cm']:>6.3f} {s.get('sm', 0):>6.3f} {s.get('exs', 0):>6.3f}"
        )


# ── entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="NL-to-1C benchmark runner")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to benchmark_config.yaml")
    parser.add_argument("--benchmark-file", default=None, help="Override benchmark_file from YAML")
    parser.add_argument("--reference-results", default=None, help="Override reference_results from YAML")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--generate-reference", action="store_true",
        help="Execute reference queries and save ground truth",
    )
    group.add_argument(
        "--run", metavar="EXPERIMENT",
        help="Run one experiment by name (e.g. schema_only)",
    )
    group.add_argument(
        "--run-all", action="store_true",
        help="Run every experiment defined in the config",
    )
    group.add_argument(
        "--report", action="store_true",
        help="Print per-experiment summary table (EV / EX / CM)",
    )
    group.add_argument(
        "--question-matrix", action="store_true",
        help="Build per-model EX question matrix, save JSON + CSV to benchmarks/matrices/",
    )
    args = parser.parse_args()

    cfg = _load_config(Path(args.config))
    if args.benchmark_file:
        cfg["benchmark_file"] = args.benchmark_file
    if args.reference_results:
        cfg["reference_results"] = args.reference_results

    if args.generate_reference:
        generate_reference(cfg)
    elif args.run:
        run_experiment(cfg, args.run)
        print("\n" + "=" * 60 + "\nMATRIX\n" + "=" * 60)
        question_matrix(cfg)
    elif args.run_all:
        for exp in cfg["experiments"]:
            print(f"\n{'=' * 60}\nRunning: {exp['name']}\n{'=' * 60}")
            run_experiment(cfg, exp["name"])
        print("\n" + "=" * 60 + "\nMATRIX\n" + "=" * 60)
        question_matrix(cfg)
    elif args.report:
        show_report(cfg)
    elif args.question_matrix:
        question_matrix(cfg)


if __name__ == "__main__":
    main()
