"""
32-bit bridge: receives connection_string and query_text via stdin (JSON),
executes the 1C query via COM, returns results via stdout (JSON).

Run only with 32-bit Python that has pywin32 installed.
"""
import sys
import json
import datetime


def _to_json(val):
    """Convert a 1C COM value to a JSON-serializable Python type."""
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val
    if isinstance(val, str):
        return val
    if isinstance(val, datetime.datetime):
        return val.strftime("%d.%m.%Y %H:%M:%S")
    if isinstance(val, datetime.date):
        return val.strftime("%d.%m.%Y")
    # Empty reference — return None instead of type metadata
    try:
        if val.Пустая():
            return None
    except Exception:
        pass
    # Catalog / document reference — try common string properties
    for attr in ("Наименование", "Код", "Представление", "НаименованиеПолное"):
        try:
            result = getattr(val, attr)
            if isinstance(result, str) and result.strip():
                return result
        except Exception:
            pass
    # Document reference — Номер + Дата
    try:
        номер = val.Номер
        if isinstance(номер, str) and номер.strip():
            try:
                дата = val.Дата
                if isinstance(дата, (datetime.date, datetime.datetime)):
                    return f"№{номер} от {дата.strftime('%d.%m.%Y')}"
            except Exception:
                pass
            return f"№{номер}"
    except Exception:
        pass
    # Enum value — Метаданные().Синоним / .Имя
    try:
        meta = val.Метаданные()
        for mattr in ("Синоним", "Имя"):
            try:
                result = getattr(meta, mattr)
                if isinstance(result, str) and result.strip():
                    return result
            except Exception:
                pass
    except Exception:
        pass
    # Last resort
    try:
        return str(val)
    except Exception:
        return ""


def main():
    payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    connection_string = payload["connection_string"]
    query_text = payload["query_text"]

    import win32com.client
    connector = win32com.client.Dispatch("V83.COMConnector")
    connection = connector.Connect(connection_string)
    try:
        query = connection.NewObject("Запрос")
        query.Text = query_text
        result = query.Execute()
        table = result.Unload()

        columns = [col.Name for col in table.Columns]
        rows = []
        for row in table:
            r = {}
            for col in columns:
                val = getattr(row, col)
                r[col] = _to_json(val)
            rows.append(r)

        print(json.dumps({"ok": True, "rows": rows, "columns": columns}, ensure_ascii=True))
    finally:
        del connection

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=True))
