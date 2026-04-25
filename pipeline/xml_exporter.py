"""
Exports 1C configuration to XMLConfiguration/ folder using 1cv8c.exe.

The configurator command used:
    1cv8c.exe CONFIG /F<db_path> /DumpConfigToFiles <out_dir> /N<user> /P<pass>

For file-based databases the connection string looks like:
    File="C:\\path\\to\\db";
We parse the path from that string.

Usage (standalone):
    python pipeline/xml_exporter.py <db_key>
    python pipeline/xml_exporter.py testbd
"""
import re
import subprocess
import sys
from pathlib import Path

# project root is one level up from this file
_ROOT = Path(__file__).parent.parent

sys.path.insert(0, str(_ROOT))
from config import ONEC_BIN, DATABASES_DIR, load_databases


def _db_path_from_connection_string(conn: str) -> str:
    """Extract filesystem path from a file-based 1C connection string.

    Supports:
        File="C:\\path\\db";
        File='C:\\path\\db';
    """
    m = re.search(r'File=["\']([^"\']+)["\']', conn, re.IGNORECASE)
    if not m:
        raise ValueError(
            f"Не удалось извлечь путь к базе из строки подключения: {conn!r}\n"
            "Поддерживается только файловый режим: File=\"...\""
        )
    return m.group(1)


def export_xml(db_key: str, *, username: str = "", password: str = "") -> Path:
    """Run 1cv8c.exe DumpConfigToFiles for the given database.

    Returns the path to the XMLConfiguration folder.
    Raises RuntimeError if 1cv8c.exe is not found or the command fails.
    """
    if ONEC_BIN is None or not ONEC_BIN.exists():
        raise RuntimeError(
            "1cv8c.exe не найден. Проверьте установку 1С или переменную ONEC_BIN в config.py."
        )

    databases = load_databases()
    if db_key not in databases:
        raise KeyError(f"База '{db_key}' не найдена в databases/. Проверьте наличие config.json.")

    conn_string = databases[db_key]["connection_string"]
    db_path = _db_path_from_connection_string(conn_string)

    out_dir = DATABASES_DIR / db_key / "XMLConfiguration"
    out_dir.mkdir(parents=True, exist_ok=True)

    # DESIGNER = configurator mode; /F must be a separate argument (Cyrillic paths break when concatenated)
    cmd = [
        str(ONEC_BIN),
        "DESIGNER",
        "/F", db_path,
        "/DumpConfigToFiles", str(out_dir),
        "/DisableStartupMessages",
        "/DisableStartupDialogs",
    ]
    if username:
        cmd += ["/N", username]
    if password:
        cmd += ["/P", password]

    print(f"[xml_exporter] Запуск: {' '.join(cmd)}", flush=True)

    result = subprocess.run(
        cmd,
        capture_output=True,
        timeout=300,  # 5 minutes should be enough for small configs
    )

    stdout = result.stdout.decode("cp1251", errors="replace") if result.stdout else ""
    stderr = result.stderr.decode("cp1251", errors="replace") if result.stderr else ""

    if stdout.strip():
        print(f"[xml_exporter] stdout:\n{stdout}", flush=True)
    if stderr.strip():
        print(f"[xml_exporter] stderr:\n{stderr}", flush=True)

    # 1cv8c.exe returns 0 on success; non-zero means error
    if result.returncode != 0:
        raise RuntimeError(
            f"1cv8c.exe завершился с кодом {result.returncode}.\n"
            f"stdout: {stdout}\nstderr: {stderr}"
        )

    # Verify that at least Configuration.xml was created
    if not (out_dir / "Configuration.xml").exists():
        raise RuntimeError(
            f"DumpConfigToFiles завершился без ошибки, но Configuration.xml не найден в {out_dir}.\n"
            f"stdout: {stdout}\nstderr: {stderr}"
        )

    print(f"[xml_exporter] Готово: {out_dir}", flush=True)
    return out_dir


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python pipeline/xml_exporter.py <db_key>")
        print("Доступные базы:", list(load_databases().keys()))
        sys.exit(1)

    key = sys.argv[1]
    try:
        path = export_xml(key)
        print(f"XMLConfiguration сохранена в: {path}")
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)
