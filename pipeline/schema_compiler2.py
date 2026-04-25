"""
Compiles 1C XMLConfiguration into compact schema text for LLM context.

Improvements over schema_compiler.py:
- Synonyms are included (critical for NL matching)
- InformationRegisters: Dimensions / Resources / Attributes are distinguished
- Enums: all values are listed
- Periodicity → shows available virtual tables (СрезПоследних / СрезПервых)
- Full type mapping including xs:decimal, xs:string, xs:boolean

Usage:
    python pipeline/schema_compiler2.py <path_to_XMLConfiguration>
    python pipeline/schema_compiler2.py              # uses ./XMLConfiguration
"""
import xml.etree.ElementTree as ET
from pathlib import Path

MD = "{http://v8.1c.ru/8.3/MDClasses}"
V8 = "{http://v8.1c.ru/8.1/data/core}"

# --- type mapping -----------------------------------------------------------

_CFG_PREFIX_MAP = {
    "CatalogRef":    "Справочник",
    "DocumentRef":   "Документ",
    "EnumRef":       "Перечисление",
    "CCTRef":        "ПланВидовХарактеристик",
    "ChartOfAccountsRef": "ПланСчетов",
    "BusinessProcessRef": "БизнесПроцесс",
    "TaskRef":       "Задача",
}

_PRIMITIVE_MAP = {
    f"{V8}String":   "Строка",
    f"{V8}Number":   "Число",
    f"{V8}Date":     "Дата",
    f"{V8}Boolean":  "Булево",
    "xs:string":     "Строка",
    "xs:decimal":    "Число",
    "xs:boolean":    "Булево",
    "xs:date":       "Дата",
    "xs:dateTime":   "Дата",
}

_PERIODICITY_LABELS = {
    "Nonperiodical":      None,
    "RecorderPosition":   "позиция регистратора",
    "Day":                "день",
    "Month":              "месяц",
    "Quarter":            "квартал",
    "Year":               "год",
}

# --- standard attributes per object kind ------------------------------------

_STD_ATTRS = {
    "Document":             "Ссылка, Номер, Дата, Проведен, ПометкаУдаления",
    "Catalog":              "Ссылка, Код, Наименование, ПометкаУдаления",
    "InformationRegister":  "Период (если периодический)",
    "AccumulationRegister": "Период",
    "Enum":                 "",
    "ChartsOfCharacteristicTypes": "Ссылка, Код, Наименование",
}

# --- XML helpers ------------------------------------------------------------

def _text(el, tag: str) -> str:
    child = el.find(tag)
    return (child.text or "").strip() if child is not None else ""


def _synonym(props_el) -> str:
    """Extract Russian synonym from Properties element."""
    syn = props_el.find(f"{MD}Synonym")
    if syn is None:
        return ""
    for item in syn.findall(f"{V8}item"):
        lang = item.find(f"{V8}lang")
        content = item.find(f"{V8}content")
        if lang is not None and lang.text == "ru" and content is not None:
            return (content.text or "").strip()
    return ""


def _parse_type(type_el) -> str:
    if type_el is None:
        return "?"
    types = []
    for t in type_el.findall(f"{V8}Type"):
        raw = (t.text or "").strip()
        if raw.startswith("cfg:"):
            raw = raw[4:]
            matched = False
            for prefix, ru in _CFG_PREFIX_MAP.items():
                if raw.startswith(prefix + "."):
                    types.append(ru + "." + raw[len(prefix) + 1:])
                    matched = True
                    break
            if not matched:
                types.append(raw)
        elif raw in _PRIMITIVE_MAP:
            types.append(_PRIMITIVE_MAP[raw])
        else:
            mapped = _PRIMITIVE_MAP.get(raw)
            if mapped:
                types.append(mapped)
            else:
                short = raw.split(":")[-1] if ":" in raw else raw
                types.append(short)
    return " | ".join(types) if types else "?"


def _attr_line(props_el) -> str | None:
    name = _text(props_el, f"{MD}Name")
    if not name:
        return None
    syn = _synonym(props_el)
    type_el = props_el.find(f"{MD}Type")
    t = _parse_type(type_el)
    label = f"{name} ({syn})" if syn and syn != name else name
    return f"{label}: {t}"


# --- per-object-type parsers ------------------------------------------------

def _parse_tabular_sections(child_objects_el) -> list[str]:
    lines = []
    if child_objects_el is None:
        return lines
    for ts in child_objects_el.findall(f"{MD}TabularSection"):
        props = ts.find(f"{MD}Properties")
        if props is None:
            continue
        name = _text(props, f"{MD}Name")
        syn = _synonym(props)
        label = f"{name} ({syn})" if syn and syn != name else name
        ts_attrs = []
        ts_children = ts.find(f"{MD}ChildObjects")
        if ts_children is not None:
            for attr in ts_children.findall(f"{MD}Attribute"):
                ap = attr.find(f"{MD}Properties")
                if ap is not None:
                    line = _attr_line(ap)
                    if line:
                        ts_attrs.append(line)
        if ts_attrs:
            lines.append(f"  Табличная часть {label}: {'; '.join(ts_attrs)}")
        else:
            lines.append(f"  Табличная часть {label}")
    return lines


def _parse_document(xml_path: Path) -> str | None:
    tree = _safe_parse(xml_path)
    if tree is None:
        return None
    root = tree.getroot()
    doc_el = root.find(f"{MD}Document")
    if doc_el is None:
        return None
    props = doc_el.find(f"{MD}Properties")
    if props is None:
        return None
    name = _text(props, f"{MD}Name")
    syn = _synonym(props)
    label = f"{name} ({syn})" if syn and syn != name else name

    lines = [f"Документ.{label}"]
    lines.append(f"  Стандартные реквизиты: {_STD_ATTRS['Document']}")

    children = doc_el.find(f"{MD}ChildObjects")
    attrs = []
    if children is not None:
        for attr in children.findall(f"{MD}Attribute"):
            ap = attr.find(f"{MD}Properties")
            if ap is not None:
                line = _attr_line(ap)
                if line:
                    attrs.append(line)
    if attrs:
        lines.append(f"  Реквизиты: {'; '.join(attrs)}")
    lines.extend(_parse_tabular_sections(children))
    return "\n".join(lines)


def _parse_catalog(xml_path: Path) -> str | None:
    tree = _safe_parse(xml_path)
    if tree is None:
        return None
    root = tree.getroot()
    cat_el = root.find(f"{MD}Catalog")
    if cat_el is None:
        return None
    props = cat_el.find(f"{MD}Properties")
    if props is None:
        return None
    name = _text(props, f"{MD}Name")
    syn = _synonym(props)
    label = f"{name} ({syn})" if syn and syn != name else name

    lines = [f"Справочник.{label}"]
    lines.append(f"  Стандартные реквизиты: {_STD_ATTRS['Catalog']}")

    children = cat_el.find(f"{MD}ChildObjects")
    attrs = []
    if children is not None:
        for attr in children.findall(f"{MD}Attribute"):
            ap = attr.find(f"{MD}Properties")
            if ap is not None:
                line = _attr_line(ap)
                if line:
                    attrs.append(line)
    if attrs:
        lines.append(f"  Реквизиты: {'; '.join(attrs)}")
    lines.extend(_parse_tabular_sections(children))
    return "\n".join(lines)


def _parse_information_register(xml_path: Path) -> str | None:
    tree = _safe_parse(xml_path)
    if tree is None:
        return None
    root = tree.getroot()
    reg_el = root.find(f"{MD}InformationRegister")
    if reg_el is None:
        return None
    props = reg_el.find(f"{MD}Properties")
    if props is None:
        return None
    name = _text(props, f"{MD}Name")
    syn = _synonym(props)
    label = f"{name} ({syn})" if syn and syn != name else name

    periodicity_key = _text(props, f"{MD}InformationRegisterPeriodicity")
    periodicity_label = _PERIODICITY_LABELS.get(periodicity_key)

    lines = [f"РегистрСведений.{label}"]
    if periodicity_label:
        lines.append(f"  Периодичность: {periodicity_label}")

    children = reg_el.find(f"{MD}ChildObjects")
    dims, resources, reg_attrs = [], [], []
    if children is not None:
        for dim in children.findall(f"{MD}Dimension"):
            dp = dim.find(f"{MD}Properties")
            if dp is not None:
                line = _attr_line(dp)
                if line:
                    dims.append(line)
        for res in children.findall(f"{MD}Resource"):
            rp = res.find(f"{MD}Properties")
            if rp is not None:
                line = _attr_line(rp)
                if line:
                    resources.append(line)
        for attr in children.findall(f"{MD}Attribute"):
            ap = attr.find(f"{MD}Properties")
            if ap is not None:
                line = _attr_line(ap)
                if line:
                    reg_attrs.append(line)

    if dims:
        lines.append(f"  Измерения: {'; '.join(dims)}")
    if resources:
        lines.append(f"  Ресурсы: {'; '.join(resources)}")
    if reg_attrs:
        lines.append(f"  Реквизиты: {'; '.join(reg_attrs)}")

    if periodicity_label:
        lines.append("  Виртуальные таблицы: СрезПоследних, СрезПервых")

    return "\n".join(lines)


def _parse_accumulation_register(xml_path: Path) -> str | None:
    tree = _safe_parse(xml_path)
    if tree is None:
        return None
    root = tree.getroot()
    reg_el = root.find(f"{MD}AccumulationRegister")
    if reg_el is None:
        return None
    props = reg_el.find(f"{MD}Properties")
    if props is None:
        return None
    name = _text(props, f"{MD}Name")
    syn = _synonym(props)
    label = f"{name} ({syn})" if syn and syn != name else name

    reg_kind = _text(props, f"{MD}RegisterType")  # Balance | Turnover

    lines = [f"РегистрНакопления.{label}"]
    if reg_kind == "Balance":
        lines.append("  Вид: остатки")
        lines.append("  Виртуальные таблицы: Остатки, Обороты, ОстаткиИОбороты")
    elif reg_kind == "Turnover":
        lines.append("  Вид: обороты")
        lines.append("  Виртуальные таблицы: Обороты")

    children = reg_el.find(f"{MD}ChildObjects")
    dims, resources, reg_attrs = [], [], []
    if children is not None:
        for dim in children.findall(f"{MD}Dimension"):
            dp = dim.find(f"{MD}Properties")
            if dp is not None:
                line = _attr_line(dp)
                if line:
                    dims.append(line)
        for res in children.findall(f"{MD}Resource"):
            rp = res.find(f"{MD}Properties")
            if rp is not None:
                line = _attr_line(rp)
                if line:
                    resources.append(line)
        for attr in children.findall(f"{MD}Attribute"):
            ap = attr.find(f"{MD}Properties")
            if ap is not None:
                line = _attr_line(ap)
                if line:
                    reg_attrs.append(line)

    if dims:
        lines.append(f"  Измерения: {'; '.join(dims)}")
    if resources:
        lines.append(f"  Ресурсы: {'; '.join(resources)}")
    if reg_attrs:
        lines.append(f"  Реквизиты: {'; '.join(reg_attrs)}")

    return "\n".join(lines)


def _parse_enum(xml_path: Path) -> str | None:
    tree = _safe_parse(xml_path)
    if tree is None:
        return None
    root = tree.getroot()
    enum_el = root.find(f"{MD}Enum")
    if enum_el is None:
        return None
    props = enum_el.find(f"{MD}Properties")
    if props is None:
        return None
    name = _text(props, f"{MD}Name")
    syn = _synonym(props)
    label = f"{name} ({syn})" if syn and syn != name else name

    values = []
    children = enum_el.find(f"{MD}ChildObjects")
    if children is not None:
        for ev in children.findall(f"{MD}EnumValue"):
            ep = ev.find(f"{MD}Properties")
            if ep is None:
                continue
            vname = _text(ep, f"{MD}Name")
            vsyn = _synonym(ep)
            values.append(f"{vname} ({vsyn})" if vsyn and vsyn != vname else vname)

    lines = [f"Перечисление.{label}"]
    if values:
        lines.append(f"  Значения: {', '.join(values)}")
    return "\n".join(lines)


# --- top-level compiler -----------------------------------------------------

def _safe_parse(xml_path: Path):
    try:
        return ET.parse(xml_path)
    except ET.ParseError:
        return None


_FOLDER_PARSERS = [
    ("Documents",             "## Документы",             _parse_document),
    ("Catalogs",              "## Справочники",            _parse_catalog),
    ("InformationRegisters",  "## Регистры сведений",      _parse_information_register),
    ("AccumulationRegisters", "## Регистры накопления",    _parse_accumulation_register),
    ("Enums",                 "## Перечисления",           _parse_enum),
]


def compile_schema(xml_config_dir: str | Path) -> str:
    xml_config_dir = Path(xml_config_dir)
    sections = ["# Схема базы данных 1С\n"]

    for folder_name, header, parser in _FOLDER_PARSERS:
        folder = xml_config_dir / folder_name
        if not folder.exists():
            continue
        objects = []
        for xml_file in sorted(folder.glob("*.xml")):
            text = parser(xml_file)
            if text:
                objects.append(text)
        if objects:
            sections.append(header)
            sections.extend(objects)
            sections.append("")

    return "\n".join(sections).strip()


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "XMLConfiguration"
    print(compile_schema(path))
