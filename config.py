import json
import glob
from pathlib import Path

# --- Feature flags ---
PIPELINE = {
    "schema_loader":      False,   # загружать схему базы в контекст LLM
    "use_cascade":        False,   # model cascade: gpt-4o-mini first, then main model if needed
}

# --- LLM ---
LLM_MODEL = "gpt-4o-mini"

LLM_MODELS: dict[str, str] = {
    "gpt-5.4-pro (completion-only, не работает)": "gpt-5.4-pro",
    "gpt-5.4 (мощная)":              "gpt-5.4",
    "gpt-5.4-mini (средняя)":        "gpt-5.4-mini",
    "gpt-4o-mini (лёгкая)":          "gpt-4o-mini",
    "o4-mini (думающая)":            "o4-mini",
}

# --- Databases ---
DATABASES_DIR = Path(__file__).parent / "databases"

# --- 1C binary (configurator) ---
def _detect_onec_bin() -> Path | None:
    # 1cv8.exe is the thick client; DESIGNER mode opens the configurator
    candidates = sorted(
        glob.glob(r"C:\Program Files (x86)\1cv8\*\bin\1cv8.exe"),
        reverse=True,  # latest version first
    )
    return Path(candidates[0]) if candidates else None

ONEC_BIN: Path | None = _detect_onec_bin()


def load_databases() -> dict[str, dict]:
    """Scan databases/ and return {db_key: config_dict}."""
    dbs = {}
    for config_file in DATABASES_DIR.glob("*/config.json"):
        key = config_file.parent.name
        with open(config_file, encoding="utf-8") as f:
            dbs[key] = json.load(f)
    return dbs
