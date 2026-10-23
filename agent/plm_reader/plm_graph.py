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


def collect_from_db():
    """Узлы и рёбра из базы plm_reader.

    Схема (engine.SCHEMA): snapshots(path, model, folder, size, volume, material, name,
    designation, rev, author, revdate, role, seen, hist, creo, created);
    links(parent, child, qty, source); derived(child, base, kind, source).
    Возвращает (nodes, edges) или (None, None), если базы нет.
    """
    if engine is None:
        return None, None
    try:
        con = engine.connect()
    except Exception:                  # noqa: BLE001
        return None, None
    nodes, edges = {}, []
    try:
        for row in con.execute("SELECT model, path, volume, material, creo, role "
                               "FROM snapshots"):
            model = _norm(row[0]) or _norm((row[1] or "").split("\\")[-1])
            if not model:
                continue
            role = (row[5] or "").upper()
            creo = (row[4] or "")
            v = ""
            if creo:
                v = creo if creo.upper().startswith("CREO") else ("Creo " + creo)
            nodes[model] = {"k": "PART", "v": v, "m": False, "i": "",
                            "s": 0, "p": (row[1] or "").split("\\")[-1],
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


def cut_preview(raw):
    """Превью из файла: искать ПО СИГНАТУРЕ (TOC-офсет DwgData НЕ ведёт к картинке!).

    Возвращает (bytes, 'jpg'|'bmp') или (b'', '').
    """
    j = -1
    while True:
        j = raw.find(b"\xff\xd8\xff", j + 1)
        if j < 0:
            break
        e = raw.find(b"\xff\xd9", j + 3)
        if e <= 0:
            continue
        cand = raw[j:e + 2]
        if len(cand) < 2048:
            continue
        w, h = jpeg_size(cand)
        if w and h and 16 <= w <= 4096 and 16 <= h <= 4096:
            return cand, "jpg"
    b = -1
    while True:
        b = raw.find(b"BM", b + 1)
        if b < 0 or b + 26 > len(raw):
            break
        size = int.from_bytes(raw[b + 2:b + 6], "little")
        w = int.from_bytes(raw[b + 18:b + 22], "little", signed=True)
        h = int.from_bytes(raw[b + 22:b + 26], "little", signed=True)
        if 1024 <= size <= len(raw) - b and 16 <= abs(w) <= 4096 and 16 <= abs(h) <= 4096:
            return raw[b:b + size], "bmp"
    return b"", ""


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
    for lit in ("__DATA__", "__STATS__", "__MEDIA__"):
        if lit in html:
            errs.append("не подставлен литерал %s" % lit)
    esc = re.findall(r"\\u00[0-9a-fA-F]{2}", js)
    if esc:
        errs.append("экранированные \\uXXXX в JS: %d" % len(esc))
    return errs


# --------------------------------------------------------------------- HTML-страница
def build_html(nodes, edges, media_dir, stats_extra=None):
    """Собирает автономную страницу (0 CDN) и возвращает текст HTML."""
    out_, in_ = defaultdict(list), defaultdict(list)
    for e in edges:
        out_[e["from"]].append(e)
        in_[e["to"]].append(e)
    nd = {}
    for m, v in nodes.items():
        nd[m] = {"k": v.get("k", "?"), "v": v.get("v", ""), "m": bool(v.get("m")),
                 "i": v.get("i", ""), "s": v.get("s", 0), "p": v.get("p", ""),
                 "o": [[e["to"], e["type"]] for e in out_.get(m, [])],
                 "n": [[e["from"], e["type"]] for e in in_.get(m, [])]}
    st = {"nodes": len(nd), "edges": len(edges),
          "media": sum(1 for v in nodes.values() if v.get("i"))}
    if stats_extra:
        st.update(stats_extra)
    rel = os.path.relpath(media_dir, HERE).replace("\\", "/") if media_dir else "."
    page = load_page_template()
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
    media = os.path.join(HERE, "db", "media")
    nodes, edges = collect_from_db()
    src = "база"
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
    if not no_open:
        try:
            import webbrowser
            webbrowser.open("file:///" + DST.replace("\\", "/"))
        except Exception:              # noqa: BLE001
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
