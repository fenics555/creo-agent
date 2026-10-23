# -*- coding: utf-8 -*-
"""plm_graph.py — PDM-Консоль: автономная HTML-страница графа изделий (без Creo).

Собирает из БАЗЫ plm_reader (таблицы snapshots/links/derived) один файл
`CREO_GRAPH.html` рядом с базой: список моделей с поиском/фильтрами, превью,
состав/входимость, SVG-граф с цветными связями (6 категорий).

Канон дома:
  * только stdlib; никаких внешних CDN — страница работает без интернета;
  * самопроверка JS перед выпуском (дисбаланс скобок / дубли функций → ОТКАЗ);
  * ничего не меняет в базе — только читает.

Запуск из инструмента:  «PDM-Консоль» → открывается в браузере.
Из командной строки:    python plm_graph.py [--no-open]
"""
import json
import os
import re
import sys
from collections import Counter as _Counter
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DST = os.path.join(HERE, "CREO_GRAPH.html")
# Режим изображений из настроек (auto/pict/draw/none) — ставится в main/collect.
_media_mode = "auto"
# Предел чтения файлов и бюджет времени (сек) — из настроек; защита от зависания на сети Z:.
_media_max = 25000
_scan_budget = 120.0
count_media = 0                     # сколько превью уже в кэше (глобально)
# Шаблон страницы: рядом с инструментом (переносимость), при отсутствии — из env.
TEMPLATE = os.path.join(HERE, "plm_graph_page.html")

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import engine                      # рядом с этим файлом — самодостаточно
except Exception:                      # noqa: BLE001
    engine = None


# ---------------------------------------------------------------- данные из базы
def _norm(name):
    """Стем модели из имени файла/модели (как в engine)."""
    s = (name or "").strip()
    low = s.lower()
    for suf in (".prt.", ".asm.", ".prt", ".asm", ".drw."):
        i = low.find(suf)
        if i > 0:
            return s[:i].upper()
    return s.upper()


def _media_cache_path():
    return os.path.join(HERE, "db", "media_cache.json")


def _load_media_cache():
    """Кэш: путь файла → (превью1, превью2). Чтобы НЕ читать файлы каждый раз (сеть Z:).

    Первый прогон — собирает и сохраняет; последующие берут готовое мгновенно.
    """
    p = _media_cache_path()
    if os.path.isfile(p):
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return {k: tuple(v) for k, v in data.items()}
        except Exception:              # noqa: BLE001
            pass
    return {}


def _save_media_cache(cache):
    try:
        d = os.path.dirname(_media_cache_path())
        if not os.path.isdir(d):
            os.makedirs(d)
        with open(_media_cache_path(), "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
    except Exception:                  # noqa: BLE001
        pass


def collect_by_path(media_dir=None):
    """Узлы по ПУТИ файла (правильная модель: одноимённые в разных папках — РАЗНЫЕ узлы).

    Проверка _diag_collide.py: 80% связей неоднозначны по имени (KIR-401-60X67-01 — 23 пути).
    Ключ узла = путь. Имя хранится отдельно (для отображения и поиска).
    Связи links(parent, child) хранят ИМЕНА → связываем с узлами через индекс имя→пути
    (если имя одно — прямая связь; если их несколько — берём все варианты как отдельные рёбра).
    """
    if engine is None:
        return None, None
    try:
        con = engine.connect()
    except Exception:                  # noqa: BLE001
        return None, None
    nodes, edges = {}, []
    import hashlib
    import time
    by_name = defaultdict(list)         # имя → [ключ-путь, …]
    cache = _load_media_cache()         # путь → (i, i2) — НЕ читаем файл повторно
    t0 = time.time()
    budget = float(_scan_budget)        # сек: ограничение на чтение файлов (настройка)
    read_files = 0
    cnt_media = len(cache)              # ЛОКАЛЬНЫЙ счётчик (глобальный нельзя менять без global)
    # Уже собранные файлы в media\ — их хэши можно проверить БЕЗ чтения Creo (быстро)
    have_media = set()
    if media_dir and os.path.isdir(media_dir):
        try:
            have_media = {f.lower() for f in os.listdir(media_dir)}
        except OSError:
            have_media = set()
    try:
        for row in con.execute("SELECT model, path, volume, material, creo, role, size, "
                               "name, designation FROM snapshots"):
            path = row[1] or ""
            if not path:
                continue
            key = path                        # КЛЮЧ = ПУТЬ (одноимённые не склеиваются)
            name = _norm(row[0]) or _norm(path.split("\\")[-1])
            if not name:
                continue
            by_name[name].append(key)
            creo = (row[4] or "")
            v = creo if creo.upper().startswith("CREO") else (("Creo " + creo) if creo else "")
            img = img2 = ""
            kind = "?"
            mfg = False
            # КЭШ: если файл уже читали — берём готовые превью, к диску не идём
            if path in cache:
                img, img2 = cache[path]
            elif media_dir and cnt_media < int(_media_max) \
                    and (time.time() - t0) < budget and os.path.isfile(path):
                try:
                    read_files += 1
                    raw = open(path, "rb").read()
                    found = cut_preview(raw, "all")
                    if _media_mode == "pict":
                        found = [f for f in found if f[1] == "jpg"]
                    elif _media_mode == "draw":
                        found = [f for f in found if f[1] == "bmp"]
                    if not os.path.isdir(media_dir):
                        os.makedirs(media_dir)
                    for i2, item in enumerate(found[:2]):
                        if not item or not item[0]:
                            continue
                        blob, ex = item
                        fname = hashlib.sha256(blob).hexdigest()[:20] + "." + ex
                        dstp = os.path.join(media_dir, fname)
                        if not os.path.exists(dstp):
                            with open(dstp, "wb") as f:
                                f.write(blob)
                        if i2 == 0:
                            img = fname
                        else:
                            img2 = fname
                    mt = PAT_TYPE.search(raw[:400])
                    if mt:
                        kind = mt.group(1).decode("latin-1")
                    mfg = b"ASSEM_MFG" in raw[:400]
                    if not v:
                        mv = RE_CREO.search(raw[:3000])
                        v = ("Creo " + mv.group(1).decode()) if mv else (
                            "ProE/Wildfire" if RE_PROE.search(raw[:3000]) else "")
                except OSError:
                    pass
            nodes[key] = {"k": kind, "v": v, "m": mfg, "i": img, "i2": img2,
                          "s": int(row[6] or 0), "p": path, "role": (row[5] or "").upper(),
                          "n": name, "d": (row[8] or "")}
            if img or img2:
                cache[path] = (img, img2)
                cnt_media += 1
        # связи: имена → пути (все варианты; если имя одно — одно ребро)
        for row in con.execute("SELECT parent, child, qty FROM links"):
            for pk in by_name.get(_norm(row[0]), []):
                for ck in by_name.get(_norm(row[1]), []):
                    if pk != ck:
                        edges.append({"from": pk, "to": ck, "type": "деталь", "channel": "db"})
        for row in con.execute("SELECT child, base, kind FROM derived"):
            k0 = (row[2] or "").lower()
            kind2 = "копия" if "коп" in k0 else "заготовка"
            for ck in by_name.get(_norm(row[0]), []):
                for bk in by_name.get(_norm(row[1]), []):
                    if ck != bk:
                        edges.append({"from": ck, "to": bk, "type": kind2, "channel": "db"})
    except Exception as e:             # noqa: BLE001
        # НЕ ГЛУШИМ: раньше исключение съедалось и откат шёл на неверную модель
        # (ключ = имя) — из-за этого граф строился «не тот». Теперь видно.
        print("ОШИБКА collect_by_path: %s: %s" % (type(e).__name__, e), flush=True)
        import traceback
        traceback.print_exc()
        return None, None
    finally:
        try:
            con.close()
        except Exception:              # noqa: BLE001
            pass
    _save_media_cache(cache)
    print("кэш превью: %d записей (прочитано файлов за прогон: %d, %.0f с)"
          % (len(cache), read_files, time.time() - t0), flush=True)
    return (nodes, edges) if nodes else (None, None)


def collect_from_db(media_dir=None):
    """Узлы и рёбра из базы plm_reader (+ превью и размеры из файлов, если доступны).

    Схема (engine.SCHEMA): snapshots(path, model, folder, size, volume, material, name,
    designation, rev, author, revdate, role, seen, hist, creo, created);
    links(parent, child, qty, source); derived(child, base, kind, source).

    media_dir задан → из КАЖДОГО файла вырезается превью (по сигнатуре, SHA-256) и
    кладётся в media_dir. Возвращает (nodes, edges) или (None, None), если базы нет.
    """
    if engine is None:
        return None, None
    try:
        con = engine.connect()
    except Exception:                  # noqa: BLE001
        return None, None
    nodes, edges = {}, []
    import hashlib
    try:
        for row in con.execute("SELECT model, path, volume, material, creo, role, size "
                               "FROM snapshots"):
            model = _norm(row[0]) or _norm((row[1] or "").split("\\")[-1])
            if not model:
                continue
            role = (row[5] or "").upper()
            creo = (row[4] or "")
            v = ""
            if creo:
                v = creo if creo.upper().startswith("CREO") else ("Creo " + creo)
            path = row[1] or ""
            img = ""
            img2 = ""                                  # второй вид (чертёж), если есть
            # ПРЕВЬЮ: собираем КАРТИНКУ и ЧЕРТЁЖ (оба, если есть) — по требованию владельца
            mode = (media_dir and _media_mode) or "none"
            if media_dir and mode != "none" and path and os.path.isfile(path) \
                    and not nodes.get(model, {}).get("i"):
                try:
                    raw = open(path, "rb").read()
                    # ВАЖНО: в файлах бывает ТОЛЬКО JPEG (даже у .drw) — собираем всё найденное
                    found = cut_preview(raw, "all")
                    if mode == "pict":
                        found = [f for f in found if f[1] == "jpg"]
                    elif mode == "draw":
                        found = [f for f in found if f[1] == "bmp"]
                    data, ext = found[0] if found else (b"", "")
                    if len(found) > 1:
                        d2 = found[1]
                    else:
                        d2 = (b"", "")
                    if not os.path.isdir(media_dir):
                        os.makedirs(media_dir)
                    for blob, ex, key in ((data, ext, "i"), (d2[0], d2[1], "i2")):
                        if not blob:
                            continue
                        fname = hashlib.sha256(blob).hexdigest()[:20] + "." + ex
                        dst = os.path.join(media_dir, fname)
                        if not os.path.exists(dst):
                            with open(dst, "wb") as f:
                                f.write(blob)
                        if key == "i":
                            img = fname
                        else:
                            img2 = fname
                    if not v:
                        mv = RE_CREO.search(raw[:3000])
                        v = ("Creo " + mv.group(1).decode()) if mv else (
                            "ProE/Wildfire" if RE_PROE.search(raw[:3000]) else "")
                    kind = "?"
                    mt = PAT_TYPE.search(raw[:400])
                    if mt:
                        kind = mt.group(1).decode("latin-1")
                    mfg = b"ASSEM_MFG" in raw[:400]
                except OSError:
                    kind, mfg = "?", False
            else:
                kind, mfg = "?", False
            if not img and model in nodes:          # уже есть узел с превью — не затираем
                continue
            nodes[model] = {"k": kind, "v": v, "m": mfg, "i": img, "i2": img2,
                            "s": int(row[6] or 0), "p": path.split("\\")[-1],
                            "role": role}
        for row in con.execute("SELECT parent, child, qty FROM links"):
            p, c = _norm(row[0]), _norm(row[1])
            if p and c and p != c and p in nodes and c in nodes:
                edges.append({"from": p, "to": c, "type": "деталь", "channel": "db"})
        for row in con.execute("SELECT child, base, kind FROM derived"):
            c, b = _norm(row[0]), _norm(row[1])
            k = (row[2] or "").lower()
            kind = "копия" if "коп" in k else "заготовка"
            if b and c and b != c and c in nodes and b in nodes:
                edges.append({"from": c, "to": b, "type": kind, "channel": "db"})
    except Exception:                  # noqa: BLE001
        pass
    finally:
        try:
            con.close()
        except Exception:              # noqa: BLE001
            pass
    return (nodes, edges) if nodes else (None, None)
# ------------------------------------------------------- превью и связи из файлов
PAT_COMP = re.compile("компонент id (\\d+) \\(([^)]{1,64}\\.(?:PRT|ASM))\\)".encode("utf-8"))
PAT_DN = re.compile(rb"d \d+ \(([A-Za-z0-9_\-\.]{2,60}?\.(?:PRT|ASM))\)", re.I)
PAT_COMPIDS = re.compile(rb"@comp_ids", re.I)
PAT_TYPE = re.compile(rb"#UGC:\d+\s+([A-Z/_]+)")
PAT_NAME = re.compile(rb"([A-Za-z0-9][A-Za-z0-9_\-\.]{3,47}\.(?:PRT|ASM))", re.I)
RE_CREO = re.compile(rb"#Creo\s+TM\s+([0-9]+(?:\.[0-9]+)?)")
RE_PROE = re.compile(rb"[Pp]ro/?[Ee]ngineer", re.I)
_SOF = [bytes([0xFF, c]) for c in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                                   0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF)]


def jpeg_size(d):
    """(ширина, высота) JPEG по SOF. (0,0) — не валидный JPEG (мусор)."""
    i, n = 2, len(d)
    while i < n - 9:
        if d[i] != 0xFF:
            i += 1
            continue
        mk = d[i:i + 2]
        if mk in _SOF:
            return int.from_bytes(d[i + 7:i + 9], "big"), int.from_bytes(d[i + 5:i + 7], "big")
        if mk == b"\xff\xd8" or 0xD0 <= d[i + 1] <= 0xD9:
            i += 2
            continue
        ln = int.from_bytes(d[i + 2:i + 4], "big")
        if ln < 2:
            return 0, 0
        i += 2 + ln
    return 0, 0


def _find_jpg(raw):
    """Первый ВАЛИДНЫЙ JPEG (сигнатура + проверка маркера SOF). (bytes,'jpg')|(b'','')."""
    j = -1
    while True:
        j = raw.find(b"\xff\xd8\xff", j + 1)
        if j < 0:
            return b"", ""
        e = raw.find(b"\xff\xd9", j + 3)
        if e <= 0:
            continue
        cand = raw[j:e + 2]
        if len(cand) < 2048:
            continue
        w, h = jpeg_size(cand)
        if w and h and 16 <= w <= 4096 and 16 <= h <= 4096:
            return cand, "jpg"


def _find_bmp(raw):
    """Первый ВАЛИДНЫЙ BMP (размер и WxH из заголовка). (bytes,'bmp')|(b'','')."""
    b = -1
    while True:
        b = raw.find(b"BM", b + 1)
        if b < 0 or b + 26 > len(raw):
            return b"", ""
        size = int.from_bytes(raw[b + 2:b + 6], "little")
        w = int.from_bytes(raw[b + 18:b + 22], "little", signed=True)
        h = int.from_bytes(raw[b + 22:b + 26], "little", signed=True)
        if 1024 <= size <= len(raw) - b and 16 <= abs(w) <= 4096 and 16 <= abs(h) <= 4096:
            return raw[b:b + size], "bmp"


def cut_preview(raw, want="both"):
    """Превью из файла: ПО СИГНАТУРЕ (TOC-офсет DwgData НЕ ведёт к картинке!).

    want: "both" — что найдётся (важно: в файлах бывает ТОЛЬКО JPEG, даже у .drw);
          "jpg" | "bmp" — строго этот формат; "all" — вернуть список ВСЕХ найденных.
    Возвращает (bytes, 'jpg'|'bmp') или (b'', ''); для "all" — [(bytes, ext), …].
    """
    if want == "all":
        out = []
        j, e = _find_jpg(raw)
        if j:
            out.append((j, e))
        b, e = _find_bmp(raw)
        if b:
            out.append((b, e))
        return out
    j, e1 = _find_jpg(raw)
    b, e2 = _find_bmp(raw)
    if want == "jpg":
        return (j, e1)
    if want == "bmp":
        return (b, e2)
    return (j, e1) if j else (b, e2)


def collect_from_snapshots(media_dir=None):
    """Узлы и рёбра, читая ФАЙЛЫ (без базы). media_dir — куда класть превью (SHA-256)."""
    if engine is None:
        return None, None
    try:
        paths = engine.all_models()        # [(модель, путь)] — если есть
    except Exception:                      # noqa: BLE001
        paths = []
    if not paths:
        return None, None
    import hashlib
    nodes, edges = {}, []
    for model, path in paths:
        m = _norm(model)
        if not m or not path or not os.path.isfile(path):
            continue
        try:
            raw = open(path, "rb").read()
        except OSError:
            continue
        mt = PAT_TYPE.search(raw[:400])
        kind = mt.group(1).decode("latin-1") if mt else "?"
        mv = RE_CREO.search(raw[:3000])
        ver = ("Creo " + mv.group(1).decode()) if mv else (
            "ProE/Wildfire" if RE_PROE.search(raw[:3000]) else "")
        img = ""
        if media_dir:
            data, ext = cut_preview(raw)
            if data:
                if not os.path.isdir(media_dir):
                    os.makedirs(media_dir)
                img = hashlib.sha256(data).hexdigest()[:20] + "." + ext
                dst = os.path.join(media_dir, img)
                if not os.path.exists(dst):
                    with open(dst, "wb") as f:
                        f.write(data)
        nodes[m] = {"k": kind, "v": ver, "m": b"ASSEM_MFG" in raw[:400], "i": img,
                    "s": len(raw), "p": os.path.basename(path)}
        refs, seen = [], set()
        for cid, nm in PAT_COMP.findall(raw):
            s = nm.decode("utf-8", "replace")
            r = _norm(s)
            if r and r != m and r not in seen:
                seen.add(r)
                refs.append(r)
        if not refs:
            for nm in PAT_DN.findall(raw):
                r = _norm(nm.decode("latin-1"))
                if r and r != m and r not in seen:
                    seen.add(r)
                    refs.append(r)
        if not refs and PAT_COMPIDS.search(raw):
            for nm in PAT_NAME.findall(raw):
                r = _norm(nm.decode("latin-1"))
                if r and r != m and r not in seen:
                    seen.add(r)
                    refs.append(r)
        for r in refs:
            edges.append({"from": m, "to": r, "type": "деталь", "channel": "file"})
    return (nodes, edges) if nodes else (None, None)


# ---------------------------------------------------------------- самопроверка JS
def selfcheck(html):
    """Проверка перед выпуском (грабля 23.10.2026: дубль функции → ПУСТОЕ ОКНО).

    Без неё страница молча открывается пустой: JS падает на синтаксисе.
    Проверяем: баланс {}, отсутствие дублей функций, остатков литералов,
    экранированных \\uXXXX.
    """
    m = re.search(r"<script>(.*)</script>", html, re.S)
    if not m:
        return ["нет <script>"]
    js = m.group(1)
    errs = []
    code = re.sub(r'"(\\.|[^"\\])*"', '""', js)
    code = re.sub(r"'(\\.|[^'\\])*'", "''", code)
    code = re.sub(r"//[^\n]*", "", code)
    deep = 0
    for ch in code:
        if ch == "{":
            deep += 1
        elif ch == "}":
            deep -= 1
    if deep != 0:
        errs.append("дисбаланс фигурных скобок в JS: %+d" % deep)
    fns = re.findall(r"function\s+([A-Za-z_$][\w$]*)\s*\(", js)
    for name, cnt in _Counter(fns).items():
        if cnt > 1:
            errs.append("дубль функции %s (%d раз) — окно останется ПУСТЫМ" % (name, cnt))
    for lit in ("__DATA__", "__STATS__", "__MEDIA__", "__DEPTH__", "__NODESMAX__",
                "__CHILDMAX__", "__LISTMAX__", "__LINKSMAX__", "__CARDH__", "__THUMB__"):
        if lit in html:
            errs.append("не подставлен литерал %s" % lit)
    esc = re.findall(r"\\u00[0-9a-fA-F]{2}", js)
    if esc:
        errs.append("экранированные \\uXXXX в JS: %d" % len(esc))
    # ГРАБЛЯ 23.10.2026: граф пуст, если уровень считать как строку (depth * "d" = NaN).
    if re.search(r"\*\s*dir\b", js) and 'var dir' not in js and 'const sign' not in js:
        errs.append("граф: уровень считается как depth * dir (строка) → NaN → пустой граф")
    # Проверка картинок делается В PYTHON (plm_graph), а не в JS — поэтому здесь только
    # убеждаемся, что страница знает про два превью (i и i2).
    if '"i2"' not in js and "n.i2" not in js:
        errs.append("граф: страница не показывает второй вид (чертёж)")
    return errs


# --------------------------------------------------------------------- HTML-страница
def load_settings():
    """Настройки графа из settings.json (правило дома: НЕ зашивать в код).

    Ключи: graph_depth, graph_nodes_max, graph_children_max, graph_list_max,
    graph_links_max, graph_card_h, graph_thumb, graph_media, graph_open_browser.
    Недостающие берутся из plm_settings.DEFAULT_SETTINGS.
    """
    # Умолчания графа. 23.10.2026: лимиты ПОДНЯТЫ по слову владельца («графа нет») —
    # при depth 3 / children 25 / nodes 120 на экран попадало 55 узлов из ветки на 344 связи,
    # и граф выглядел «пустым». Настройки читаются из settings.json, если ключи там есть.
    cfg = {"graph_depth": 4, "graph_nodes_max": 400, "graph_children_max": 60,
           "graph_list_max": 800, "graph_links_max": 120, "graph_card_h": 230,
           "graph_thumb": 40, "graph_media": True, "graph_image_mode": "auto",
           "graph_media_limit": 25000, "graph_scan_budget": 120, "graph_page_nodes": 12000,
           "graph_open_browser": True}
    try:
        import plm_settings
        cfg.update({k: v for k, v in plm_settings.load_settings_file().items() if k in cfg})
    except Exception:                  # noqa: BLE001
        try:
            p = os.path.join(HERE, "settings", "settings.json")
            if os.path.isfile(p):
                raw = json.load(open(p, encoding="utf-8"))
                cfg.update({k: v for k, v in raw.items() if k in cfg})
        except Exception:              # noqa: BLE001
            pass
    return cfg


def build_html(nodes, edges, media_dir, stats_extra=None):
    """Собирает автономную страницу (0 CDN) и возвращает текст HTML."""
    out_, in_ = defaultdict(list), defaultdict(list)
    for e in edges:
        out_[e["from"]].append(e)
        in_[e["to"]].append(e)
    # КОМПАКТНО: в страницу идут только узлы, у которых ЕСТЬ связи или превью,
    # плюс ограничение объёма (иначе 46 МБ — браузер не отрисует).
    cfg0 = load_settings()
    limit_nodes = int(cfg0.get("graph_page_nodes", 12000))
    # ОТСЕВ ШАБЛОНОВ и служебных: они «входят в тысячи сборок» и портят список
    # (SBORKA_MM — 3682, SBORKA_MFG — 1975, MM_PART — 1847, папки ШАБЛОНЫ/НАСТРОЙКИ).
    SVC = re.compile(r"^(SBORKA_MM|SBORKA_MFG|MFG_NC|MFG_NC_NEW|INLBS_MFG_NC|MM_PART|MM_ASSY|"
                     r"MM_|TEMPLATE|REGEN_BACKUP|NONE|NULL)$", re.I)
    SVC_DIR = re.compile(r"(ШАБЛОН|НАСТРОЙК|TEMPLATE|\\СИСТЕМН)", re.I)

    def _svc(k):
        v = nodes[k]
        nm = (v.get("n") or "").upper()
        return bool(SVC.match(nm)) or bool(SVC_DIR.search(v.get("p") or ""))

    live = [k for k, v in nodes.items()
            if (out_.get(k) or in_.get(k) or v.get("i")) and not _svc(k)]
    live.sort(key=lambda k: -(len(out_.get(k, ())) + len(in_.get(k, ()))))
    keep = set(live[:limit_nodes])
    idx = {k: i for i, k in enumerate(sorted(keep))}      # ключ → номер (коротко)
    nd = {}
    for m, v in nodes.items():
        if m not in keep:
            continue
        # m — КЛЮЧ (путь); nm — имя для показа и поиска; folder — папка (чтобы различить одноимённые)
        full = v.get("p", "") or m
        nm = v.get("n") or _norm(full.split("\\")[-1])
        folder = full.rsplit("\\", 2)[-2] if "\\" in full else ""
        nd[idx[m]] = {"k": v.get("k", "?"), "v": v.get("v", ""), "m": bool(v.get("m")),
                      "i": v.get("i", ""), "i2": v.get("i2", ""),
                      "s": v.get("s", 0), "nm": nm, "dir": folder,
                      "o": [[idx[e["to"]], e["type"]] for e in out_.get(m, [])
                            if e["to"] in idx],
                      "n": [[idx[e["from"]], e["type"]] for e in in_.get(m, [])
                            if e["from"] in idx]}
    # статистика — ПО СТРАНИЦЕ (в неё попадает часть узлов), а не по всей базе
    n_img = sum(1 for v in nd.values() if v.get("i"))
    n_e = sum(len(v.get("o") or []) for v in nd.values())
    st = {"nodes": len(nd), "edges": n_e, "media": n_img, "no_img": len(nd) - n_img,
          "all_nodes": len(nodes), "all_edges": len(edges)}
    if stats_extra:
        st.update(stats_extra)
    rel = os.path.relpath(media_dir, HERE).replace("\\", "/") if media_dir else "."
    cfg = load_settings()
    # ГРАБЛЯ 23.10.2026: страница «пустая», если она гигантская — браузер не парсит 46 МБ.
    # Поэтому связи пишем КОМПАКТНО (короткие ключи) + ограничиваем список узлов в странице.
    page = load_page_template()
    for key, val in (("__DEPTH__", cfg["graph_depth"]), ("__NODESMAX__", cfg["graph_nodes_max"]),
                     ("__CHILDMAX__", cfg["graph_children_max"]),
                     ("__LISTMAX__", cfg["graph_list_max"]),
                     ("__LINKSMAX__", cfg["graph_links_max"]),
                     ("__CARDH__", cfg["graph_card_h"]), ("__THUMB__", cfg["graph_thumb"])):
        page = page.replace(key, str(val))
    st["cfg"] = {k: v for k, v in cfg.items() if k != "graph_media"}
    return (page.replace("__DATA__", json.dumps(nd, ensure_ascii=False))
                .replace("__STATS__", json.dumps(st, ensure_ascii=False))
                .replace("__MEDIA__", rel))


def load_page_template():
    """Шаблон страницы: файл `plm_graph_page.html` рядом с инструментом (переносимость).

    Приоритет: env PLM_GRAPH_TEMPLATE → TEMPLATE рядом → minimal PAGE.
    Так шаблон правится БЕЗ правки кода (требование «самодостаточный инструмент»).
    """
    for p in (os.environ.get("PLM_GRAPH_TEMPLATE", ""), TEMPLATE):
        if p and os.path.isfile(p):
            raw = open(p, encoding="utf-8").read()
            i, j = raw.find("<!DOCTYPE"), raw.rfind("</html>")
            if i >= 0 and j > i:
                return raw[i:j + 7]
    return PAGE


def main():
    no_open = "--no-open" in sys.argv
    global _media_mode, _media_max, _scan_budget, count_media
    cfg = load_settings()
    _media_mode = (cfg.get("graph_image_mode") or "auto").lower()
    _media_max = int(cfg.get("graph_media_limit", 25000))
    _scan_budget = float(cfg.get("graph_scan_budget", 120))
    count_media = 0
    media = None if _media_mode == "none" or not cfg.get("graph_media") \
        else os.path.join(HERE, "db", "media")
    nodes, edges = collect_by_path(media)      # КЛЮЧ = ПУТЬ (одноимённые — разные узлы)
    src = "база (по путям)"
    if not nodes:
        nodes, edges = collect_from_db(media)
        src = "база (по именам)"
    if not nodes:
        nodes, edges = collect_from_snapshots(media)
        src = "файлы"
    if not nodes:
        print("НЕТ ДАННЫХ: ни базы, ни моделей. Сначала просканируйте (Сканировать).")
        return 1
    html = build_html(nodes, edges, media)
    errs = selfcheck(html)
    if errs:
        print("ОТКАЗ: страница не выпущена:")
        for e in errs:
            print("   -", e)
        return 1
    with open(DST, "w", encoding="utf-8") as f:
        f.write(html)
    print("источник: %s | узлов %d | рёбер %d | с превью %d"
          % (src, len(nodes), len(edges), sum(1 for v in nodes.values() if v.get("i"))))
    print("->", DST)
    if not no_open and cfg.get("graph_open_browser", True):
        try:
            import webbrowser
            webbrowser.open("file:///" + DST.replace("\\", "/"))
        except Exception:              # noqa: BLE001
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
