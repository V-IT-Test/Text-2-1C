"""One-time script: parse question_list.txt → databases/demo/benchmark.json"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "question_list.txt"
OUTPUT = ROOT / "databases" / "demo" / "benchmark.json"


def parse(filepath: Path) -> list[dict]:
    lines = filepath.read_text(encoding="utf-8").splitlines()
    lines = lines[1:]  # skip header "# ЯЗЫК ЗАПРОСОВ File=..."

    entries = []
    current_id = None
    current_question = None
    query_lines: list[str] = []

    question_re = re.compile(r"^(\d+)\.\s*(.+)")

    for line in lines:
        m = question_re.match(line.strip())
        if m:
            if current_id is not None:
                entries.append({
                    "id": current_id,
                    "question": current_question,
                    "reference_query": "\n".join(query_lines).strip(),
                })
            current_id = int(m.group(1))
            current_question = m.group(2).strip()
            query_lines = []
        elif current_id is not None:
            query_lines.append(line.rstrip())

    if current_id is not None:
        entries.append({
            "id": current_id,
            "question": current_question,
            "reference_query": "\n".join(query_lines).strip(),
        })

    return entries


def main():
    entries = parse(INPUT)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Saved {len(entries)} questions to {OUTPUT}")
    for e in entries:
        q = e['question'].encode('cp1251', errors='replace').decode('cp1251')
        print(f"  #{e['id']:2d}: {q[:65]}")


if __name__ == "__main__":
    main()
