import json
import subprocess
from pathlib import Path

BRIDGE_PYTHON = str(Path(__file__).parent.parent / "venv" / "Scripts" / "python.exe")
BRIDGE_SCRIPT = str(Path(__file__).parent.parent / "executor_bridge.py")


def execute(connection_string: str, query_text: str) -> list[dict]:
    """Execute a 1C query via 32-bit bridge process, return results as list of dicts."""
    payload = json.dumps({"connection_string": connection_string, "query_text": query_text}, ensure_ascii=False)

    proc = subprocess.run(
        [BRIDGE_PYTHON, BRIDGE_SCRIPT],
        input=payload.encode("utf-8"),
        capture_output=True,
    )

    stdout = proc.stdout.decode("utf-8") if proc.stdout else ""
    stderr = proc.stderr.decode("utf-8") if proc.stderr else ""

    if not stdout.strip():
        raise RuntimeError(f"Bridge вернул пустой ответ.\nSTDERR: {stderr}")

    result = json.loads(stdout)
    if not result["ok"]:
        raise RuntimeError(result["error"])

    return result["rows"]
