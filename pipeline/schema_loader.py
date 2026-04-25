from pathlib import Path

_cache: dict[str, str] = {}

_SCHEMA_FILE = "DBStructure/schema.md"


def schema_path(db_key: str) -> Path:
    return Path(__file__).parent.parent / "databases" / db_key / _SCHEMA_FILE


def load_schema(db_key: str, connection_string: str = "", force_export: bool = False) -> str:
    """Return compiled schema Markdown for the given database.

    - If schema.md exists and force_export=False: read from file (no 1C needed).
    - If schema.md missing or force_export=True: export XML via 1cv8.exe,
      compile to Markdown, save to disk.
    """
    if not force_export and db_key in _cache:
        return _cache[db_key]

    sf = schema_path(db_key)

    if not force_export and sf.exists():
        schema = sf.read_text(encoding="utf-8")
        _cache[db_key] = schema
        return schema

    if not connection_string:
        return ""

    from pipeline.xml_exporter import export_xml
    from pipeline.schema_compiler2 import compile_schema

    xml_dir = export_xml(db_key)
    schema = compile_schema(xml_dir)

    sf.parent.mkdir(parents=True, exist_ok=True)
    sf.write_text(schema, encoding="utf-8")

    _cache[db_key] = schema
    return schema
