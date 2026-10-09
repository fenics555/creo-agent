# -*- coding: utf-8 -*-
"""plm_scan.py — вынесено из plm_reader.py распилом (см. СПЕКА_РАСПИЛА_PLM_READER.md)."""
from plm_reader import (
    DEFAULT_SETTINGS,
    MODELFILE,
    VERSION_RE,
    datetime,
    db_rows_map,
    kind,
    load_cache,
    norm_path,
    os,
    outline_mm,
    parameters,
    provenance,
    read_bytes,
    real_value,
    save_cache,
    sections,
)


def match_filter(row, cols, pattern):
    """Подходит ли строка под фильтр: КАЖДОЕ слово — в любом показанном столбце (без учёта регистра)."""
    words = [w for w in (pattern or "").lower().split() if w]
    if not words:
        return True
    blob = " ".join(str(row.get(c, "")) for c in cols).lower()
    return all(w in blob for w in words)
def _compose_par(par, rule):
    """Шаблон по словарю параметров: `{ИМЯ}` — значение, `"текст"` — литерал (кавычки не выводятся)."""
    out, i, n = [], 0, len(rule)
    while i < n:
        c = rule[i]
        if c == "{":
            j = rule.find("}", i)
            if j < 0:
                break
            v = first_param(par, [rule[i + 1:j].strip()])
            if v:
                out.append(str(v))
            i = j + 1
        elif c == '"':
            j = rule.find('"', i + 1)
            if j < 0:
                break
            out.append(rule[i + 1:j])
            i = j + 1
        elif c == "+":
            i += 1
        elif c.isspace():
            out.append(" ")                    # пробел в правиле = пробел в выводе
            i += 1
        else:
            j = i
            while j < n and rule[j] not in '{+"':
                j += 1
            out.append(rule[i:j])
            i = j
    return " ".join("".join(out).split())
def first_param(par, keys):
    """Первое непустое: имя параметра ИЛИ ШАБЛОН `{ИМЯ} "текст" +` (кавычки не выводятся)."""
    upper = {str(k).upper(): v for k, v in par.items()}
    for k in keys:
        k = (k or "").strip()
        if not k:
            continue
        if "{" in k or '"' in k:
            v = _compose_par(par, k)
            if v:
                return v
            continue
        v = par.get(k) or upper.get(k.upper())
        if v:
            return str(v)
    return ""
def scan_file(path, settings):
    from plm_history import history      # ленивый импорт: разрывает цикл scan↔history (скилл §24)
    raw = read_bytes(path, settings.get("max_size_mb", 24))    # V86: умолчание24 = DEFAULT
    if raw is None:
        return None
    sec = sections(raw)
    par = parameters(raw, sec)
    hist = history(raw)
    is_part = ".prt." in path.lower()
    role, parent = provenance(raw, is_part)
    vol = real_value(raw, "volume") or real_value(raw, "mtrl_volume")
    last = hist[-1] if hist else None
    return {
        "Файл": os.path.basename(path),
        "Тип": kind(raw),
        "Обозначение": first_param(par, settings.get("param_designation", DEFAULT_SETTINGS["param_designation"])),
        "Наименование": first_param(par, settings.get("param_name", DEFAULT_SETTINGS["param_name"])),
        "Материал": first_param(par, settings.get("param_material", DEFAULT_SETTINGS["param_material"])),
        "Объём, мм³": ("%.0f" % vol) if vol else "",
        "Габарит, мм": ", ".join("%.1f" % v for v in outline_mm(raw, sec)),
        "Роль": role,
        "Родитель": parent,
        "Ревизия": last[0] if last else "",
        "Дата": last[1].replace(tzinfo=datetime.timezone.utc).astimezone().strftime("%d.%m.%Y %H:%M")
                if last and last[1] else "",
        "Пользователь": last[2] if last else "",
        "Записей": len(hist),
        "Версия Creo": last[4] if last else "",
        "_path": path,
    }
def version_key(path):
    """Ключ изделия (папка, база, тип) и номер версии; None — если имя не похоже на модель."""
    m = VERSION_RE.match(os.path.basename(path))
    if not m:
        return None
    return (os.path.dirname(path).lower(), m.group(1).lower(), m.group(2).lower(),
            int(m.group(3)))
def pick_latest(paths, latest_only=True):
    """[(путь, всего_версий)]: при latest_only у изделия оставляем одну — старшую версию."""
    groups, plain = {}, []
    for p in paths:
        k = version_key(p)
        if not k:
            plain.append((p, 1))
            continue
        groups.setdefault(k[:3], []).append((k[3], p))
    out = []
    for lst in groups.values():
        lst.sort()
        if latest_only:
            out.append((lst[-1][1], len(lst)))
        else:
            for _, p in lst:
                out.append((p, len(lst)))
    out += plain
    return out
def scan_folder(folder, settings, progress=None, on_row=None, stop_cb=None, stats=None, walk_cb=None):
    rows, paths = [], []
    if settings.get("recurse", True):
        for dp, _, files in os.walk(folder):
            for f in files:
                if MODELFILE.search(f):
                    paths.append(os.path.join(dp, f))
                    if walk_cb and len(paths) % 200 == 0:
                        walk_cb(len(paths), False)
    else:
        for f in os.listdir(folder):
            if MODELFILE.search(f):
                paths.append(os.path.join(folder, f))
    if walk_cb:
        walk_cb(len(paths), True)             # обход закончен: всего найдено N моделей
    chosen = pick_latest(sorted(paths), settings.get("latest_only", True))
    cache = load_cache()                      # строки, прочитанные самим ридером (полные)
    known = db_rows_map(folder)               # ЕДИНАЯ БАЗА: что уже прочитано движком и не менялось
    fresh, read_n, from_cache = {}, 0, 0
    for n, (p, total) in enumerate(chosen, 1):
        if stop_cb and stop_cb():
            if stats is not None:
                stats["stopped"] = True
            break
        if progress:
            progress(n, len(chosen), p)
        try:
            st = os.stat(p)
        except OSError:
            continue
        old = cache.get(p)
        r = None
        if old and int(old.get("size", -1)) == st.st_size and abs(float(old.get("mtime", 0)) - st.st_mtime) < 1.0:
            r = old.get("row")                # НЕ изменился: берём из своего кэша (полная строка)
            from_cache += 1
        elif p in known and int(known[p][1] or 0) == st.st_size \
                and abs(float(known[p][2] or 0) - st.st_mtime) < 1.0:
            r = known[p][0]                   # НЕ изменился: берём из ЕДИНОЙ БАЗЫ — файл НЕ читаем
            from_cache += 1
        else:
            try:
                r = scan_file(p, settings)
            except Exception:
                r = None
            if r:
                fresh[p] = {"size": st.st_size, "mtime": st.st_mtime, "row": r}
            read_n += 1
        if r:
            r = dict(r)
            r["Версий"] = total
            rows.append(r)
            if on_row:
                on_row(r)
    if fresh:
        cache.update(fresh)
        save_cache(cache)
    if stats is not None:
        stats["read"] = read_n
        stats["cache"] = from_cache
        stats["rows"] = len(rows)
    return rows
def path_under(path, roots):
    """Путь внутри одного из корней (без учёта регистра, по границе папки).
    roots — путь ИЛИ список путей; безопасен к кривым строкам."""
    if isinstance(roots, str):
        roots = [roots]
    try:
        p = os.path.normcase(os.path.abspath(path))
    except Exception:
        return False
    for r in roots or []:
        try:
            rn = os.path.normcase(os.path.abspath(r)).rstrip("\\/")
        except Exception:
            continue
        if not rn:
            continue
        if p == rn or p.startswith(rn + "\\"):
            return True
    return False
def roots_of(folder, folder2=""):
    """Корни окна: основная папка + «Папка2» — только существующие, без дублей."""
    out = []
    for x in (folder, folder2):
        x = norm_path(x) if x else ""
        if x and x not in out:
            out.append(x)
    return out
def scan_roots(folder, folder2="", extra=None):
    """Корни СКАНА: поля окна («Папка1», «Папка2») + добавочные пути из настроек, без дублей."""
    out = roots_of(folder, folder2)
    for x in (extra or []):
        x = norm_path(x) if x else ""
        if x and x not in out:
            out.append(x)
    return out
def exclude_list(paths=None):
    """Папки-исключения в рабочем виде (нормализованные пути, без пустых)."""
    out = []
    for p in (paths or []):
        p = norm_path(str(p)) if str(p or "").strip() else ""
        if p and p not in out:
            out.append(p)
    return out
