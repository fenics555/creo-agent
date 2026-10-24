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
_media_max = 0                      # V107: 0 = БЕЗ ПРЕДЕЛА (собрать превью у всех файлов)
_scan_budget = 600.0                # V107: 120 → 600 с (полный сбор превью идёт фоном)
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


def _kind_by_path(path):
    """Тип модели ПО РАСШИРЕНИЮ файла (без чтения) — чтобы .asm не показывался как PRT.

    V104: файл может быть недоступен (сеть/бюджет превью) — тип всё равно нужен.
    Точное уточнение (ASSEMBLY/ASSEM_MFG) делает чтение файла, когда оно есть.
    """
    low = (path or "").lower()
    if ".asm." in low or low.endswith(".asm"):
        return "ASSEMBLY"
    if ".prt." in low or low.endswith(".prt"):
        return "PART"
    if ".drw." in low or low.endswith(".drw"):
        return "DRAWING"
    return "?"


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
        # V107 ДОКАЧКА: если бюджет ограничен — сначала читаем те файлы, которых НЕТ в кэше,
        # иначе первые 25 000 по порядку пути съедали лимит каждый раз, а «хвост» базы
        # никогда не получал превью (владелец: «вместо картинки 0»).
        # ИСТОРИЯ ИЗМЕНЕНИЙ (V109): журнал `changes` по путям файлов — кто/когда/что правил.
        # Владелец: «история файла нигде в HTML не выводится». Собираем ДО цикла узлов,
        # потому что каждый узел берёт свою историю по своему пути.
        hist = defaultdict(list)

        def _clean(x):
            """Убрать управляющие символы (в базе есть `\\x01`/`\\x02` из Creo-строк) —
            иначе они попадают в JSON как `\\u0001` и ломают проверку JS."""
            return "".join(ch for ch in str(x or "") if ch >= " " or ch == "\t")

        # V110 (запрос владельца): строка истории = «ДАТА ПРАВКИ — КОМП/ЮЗЕР — РЕВИЗИЯ — ЧТО».
        # `who` в журнале — это АВТОР из паспорта Creo (имя машины/пользователя: ZEH116, FENICS,
        # GORSHKOV), а `ts` — когда ИНСТРУМЕНТ заметил правку (не когда её сделали в Creo).
        # Поэтому реальную дату правки достаём из описания: `revdate: -→31.08.23 05:11`.
        RE_REVDATE = re.compile(r"revdate:\s*[^→]*→([^;]+)")

        def _real_date(descr, ts):
            m = RE_REVDATE.search(descr or "")
            if m:
                return m.group(1).strip()
            return (ts or "")[:16]

        try:
            for item, rev, kind, descr, who, ts in con.execute(
                    "SELECT item,rev,kind,descr,who,ts FROM changes ORDER BY ts DESC LIMIT 200000"):
                if item:
                    d = _clean(descr)
                    # ЧТО изменилось — без служебного `revdate` (он показан отдельной колонкой).
                    what = RE_REVDATE.sub("", d).strip(" ;")
                    hist[item].append([_real_date(d, ts), _clean(who), _clean(rev),
                                       _clean(kind), what])
        except Exception:
            pass
        print("история: путей с записями %d" % len(hist), flush=True)

        _rows = list(con.execute("SELECT model, path, volume, material, creo, role, size, "
                                 "name, designation FROM snapshots"))
        if media_dir and int(_media_max) > 0:
            _rows.sort(key=lambda r: 0 if (r[1] or "") in cache else 1)
        for row in _rows:
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
            # ТИП ПО РАСШИРЕНИЮ ИЗ БАЗЫ (без чтения файла!) — V104.
            # Грабля: раньше kind брался ТОЛЬКО из прочитанного файла (при сборе превью), и если
            # файл не читали (бюджет превью исчерпан / нет доступа), оставался "?" → страница
            # показывала «PRT» даже для .asm-сборки (жалоба владельца: AX57K-V2 = PRT, а это сборка).
            kind = _kind_by_path(path)
            mfg = False
            # КЭШ: если файл уже читали — берём готовые превью, к диску не идём.
            # V107: `_media_max` = 0 → БЕЗ ПРЕДЕЛА (докачка). Раньше жёсткий потолок 25 000
            # оставлял 22 000 файлов без превью, хотя картинка в файле ЕСТЬ (жалоба владельца:
            # «вместо картинки 0» у .asm-сборок). Кэш инкрементальный — повторный прогон
            # дочитывает то, чего в кэше ещё нет, и уже собранное не перечитывает.
            _unlimited = int(_media_max) <= 0
            if path in cache:
                img, img2 = cache[path]
            elif media_dir and (_unlimited or cnt_media < int(_media_max)) \
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
                          "n": name, "d": (row[8] or ""),
                          "h": hist.get(path, [])[:40]}      # V109: история файла (до 40 записей)
            if img or img2:
                cache[path] = (img, img2)
                cnt_media += 1

        # СВЯЗИ: V104 — СКЛЕЙКА ПО МОДЕЛИ, затем раскладка на пути.
        #
        # ГЛАВНАЯ ГРАБЛЯ (жалоба владельца «HB72501-401 подряд десятки раз»):
        # у имени бывает МНОГО путей (HB72501-401 — 98 файлов), и прежняя логика «на каждую
        # комбинацию путей — своё ребро» давала ВЗРЫВ: 30 строк links × 98 путей = 948 рёбер.
        # Поэтому: (1) сначала СКЛЕИВАЕМ связи на уровне ИМЁН (одна связь «имя→имя» = одно ребро,
        # количество суммируется); (2) затем раскладываем по путям, но ТОЛЬКО для тех узлов,
        # что реально попали в страницу — и один узел получает НЕ БОЛЕЕ ОДНОЙ строки на соседа.
        agg = {}

        def add_edge(fr_name, to_name, typ, q):
            if not fr_name or not to_name or fr_name == to_name:
                return
            k = (fr_name, to_name, typ)
            agg[k] = agg.get(k, 0) + int(q or 1)

        for row in con.execute("SELECT parent, child, qty FROM links"):
            add_edge(_norm(row[0]), _norm(row[1]), "деталь", row[2])
        for row in con.execute("SELECT child, base, kind FROM derived"):
            k0 = (row[2] or "").lower()
            add_edge(_norm(row[0]), _norm(row[1]), "копия" if "коп" in k0 else "заготовка", 1)
        for (fr, to, typ), q in agg.items():
            for pk in by_name.get(fr, []):
                for ck in by_name.get(to, []):
                    if pk != ck:
                        edges.append({"from": pk, "to": ck, "type": typ, "qty": q,
                                      "channel": "db"})
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
        # V104: склейка одинаковых связей + суммирование qty (без дублей «одна связь = строка»)
        agg = {}

        def add_edge(fr, to, typ, q):
            if fr and to and fr != to and fr in nodes and to in nodes:
                k = (fr, to, typ)
                agg[k] = agg.get(k, 0) + int(q or 1)

        for row in con.execute("SELECT parent, child, qty FROM links"):
            add_edge(_norm(row[0]), _norm(row[1]), "деталь", row[2])
        for row in con.execute("SELECT child, base, kind FROM derived"):
            k = (row[2] or "").lower()
            add_edge(_norm(row[0]), _norm(row[1]),
                     "копия" if "коп" in k else "заготовка", 1)
        for (fr, to, typ), q in agg.items():
            edges.append({"from": fr, "to": to, "type": typ, "qty": q, "channel": "db"})
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
    # `\u00XX` опасен ТОЛЬКО в КОДЕ JS. В данных (JSON-строках) это штатный эскейп
    # управляющих символов из базы Creo — он допустим. Поэтому сначала убираем строки.
    esc = re.findall(r"\\u00[0-9a-fA-F]{2}", code)
    if esc:
        errs.append("экранированные \\uXXXX в коде JS: %d" % len(esc))
    # ГРАБЛЯ 23.10.2026: граф пуст, если уровень считать как строку (depth * "d" = NaN).
    if re.search(r"\*\s*dir\b", js) and 'var dir' not in js and 'const sign' not in js:
        errs.append("граф: уровень считается как depth * dir (строка) → NaN → пустой граф")
    # Проверка картинок делается В PYTHON (plm_graph), а не в JS — поэтому здесь только
    # убеждаемся, что страница знает про два превью (i и i2).
    if '"i2"' not in js and "n.i2" not in js:
        errs.append("граф: страница не показывает второй вид (чертёж)")
    # 🔴 ГРАБЛЯ 24.10.2026: страница падала с `SyntaxError: Unexpected number` — в шаблоне
    # использовали ИМЯ вида `__LISTMAX__`, а генератор подставляет туда ЧИСЛО → `window.800`.
    # Проверяем, что после подстановки не осталось обращений `X.<число>` и `__ИМЯ__` в коде.
    js_nc = re.sub(r"//[^\n]*", "", js)                 # без комментариев (там бывают примеры)
    js_nc = re.sub(r"/\*.*?\*/", "", js_nc, flags=re.S)  # и без блочных
    bad_num = re.findall(r"(?:window|document|this|root)\s*\.\s*\d", js_nc)
    if bad_num:
        errs.append("битая подстановка: обращение к свойству числом (%d шт.) — "
                    "не используйте имена __XXX__ в JS" % len(bad_num))
    left = re.findall(r"__[A-Z_]{3,}__", js_nc)
    # допускаем ТОЛЬКО известные подставляемые литералы (они уже заменены генератором)
    left = [x for x in left if x not in ("__DATA__", "__STATS__", "__MEDIA__")]
    if left:
        errs.append("в JS остались неподставленные литералы: %s" % ", ".join(sorted(set(left))[:5]))
    # баланс круглых/квадратных скобок (частая причина «страница пустая»)
    for op, cl, name in (("(", ")", "круглых"), ("[", "]", "квадратных")):
        code2 = re.sub(r'"(?:\\.|[^"\\])*"', '""', js)
        code2 = re.sub(r"'(?:\\.|[^'\\])*'", "''", code2)
        code2 = re.sub(r"//[^\n]*", "", code2)
        if code2.count(op) != code2.count(cl):
            errs.append("дисбаланс %s скобок в JS: %d vs %d"
                        % (name, code2.count(op), code2.count(cl)))
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
    # V104: graph_page_nodes 12000 → 60000 — на боевой базе 21 868 моделей СО СВЯЗЯМИ, и при
    # старом лимите ~10 000 связанных моделей ВООБЩЕ не попадали в страницу (владелец не мог
    # найти DF-STP2-VDF / 170META-2-МОДЕЛЬ-ВЕРХА — «не выводит ни картинку, ни чертёж»).
    # Ленивая загрузка (порции) держит страницу быстрой даже при 60 000 узлов.
    cfg = {"graph_depth": 4, "graph_nodes_max": 400, "graph_children_max": 60,
           "graph_list_max": 800, "graph_links_max": 120, "graph_card_h": 230,
           "graph_thumb": 40, "graph_media": True, "graph_image_mode": "auto",
           "graph_chunk_nodes": 1200, "lazy_first_chunk": 1500,   # V104: показываем и их
           # V107: предел превью 25000 → 0 (без предела): потолок оставлял 22 000 файлов без
           # картинок, хотя превью в файлах есть. Бюджет времени 120 → 600 с (сбор идёт фоном).
           "graph_media_limit": 0, "graph_scan_budget": 600, "graph_page_nodes": 60000,
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
    # V104: ОДНА строка на МОДЕЛЬ-соседа (жалоба владельца «HB72501-401 подряд десятки раз»).
    # У имени бывает много путей (HB72501-401 — 98), и в «связях» появлялись все пути одной
    # модели подряд. Сворачиваем по ИМЕНИ соседа (+тип): количество суммируется, а путь-дубль
    # не показывается. Ключ узла (индекс) берём — самый «богатый» путь, чтобы ссылка вела.
    # Приоритет типа при склейке: «заготовка»/«копия» важнее «деталь» (их и показываем).
    _TPRI = {"деталь": 0, "заготовка": 1, "база/заготовка": 1, "копия": 2}

    def _merge(lst, side):
        """Одна строка на МОДЕЛЬ-соседа. Типы одной пары склеиваем (берём «сильнейший»)."""
        res = {}
        for e in lst:
            nm = (nodes.get(e[side], {}) or {}).get("n") or e[side]
            cur = res.get(nm)
            if cur is None:
                res[nm] = {"idx": e[side], "type": e.get("type", ""),
                           "qty": int(e.get("qty", 1) or 1)}
            else:
                cur["qty"] += int(e.get("qty", 1) or 1)
                if _TPRI.get(e.get("type", ""), 0) > _TPRI.get(cur["type"], 0):
                    cur["type"] = e.get("type", "")
        return [{"key": v["idx"], "type": v["type"], "qty": v["qty"]} for v in res.values()]
    out_m = {m: _merge(v, "to") for m, v in out_.items()}
    in_m = {m: _merge(v, "from") for m, v in in_.items()}
    # КОМПАКТНО: в страницу идут только узлы, у которых ЕСТЬ связи или превью,
    # плюс ограничение объёма (иначе 46 МБ — браузер не отрисует).
    cfg0 = load_settings()
    limit_nodes = int(cfg0.get("graph_page_nodes", 60000))
    # ОТСЕВ ШАБЛОНОВ и служебных: они «входят в тысячи сборок» и портят список
    # (SBORKA_MM — 3682, SBORKA_MFG — 1975, MM_PART — 1847, папки ШАБЛОНЫ/НАСТРОЙКИ).
    SVC = re.compile(r"^(SBORKA_MM|SBORKA_MFG|MFG_NC|MFG_NC_NEW|INLBS_MFG_NC|MM_PART|MM_ASSY|"
                     r"MM_|TEMPLATE|REGEN_BACKUP|NONE|NULL)$", re.I)
    SVC_DIR = re.compile(r"(ШАБЛОН|НАСТРОЙК|TEMPLATE|\\СИСТЕМН)", re.I)

    def _svc(k):
        v = nodes[k]
        nm = (v.get("n") or "").upper()
        return bool(SVC.match(nm)) or bool(SVC_DIR.search(v.get("p") or ""))

    # ── V104: СВОРАЧИВАЕМ ОДНОИМЁННЫЕ ПУТИ В ОДИН УЗЕЛ ────────────────────────────────────────
    # У имени бывает десятки путей (HB72501-401 — 98). Раньше каждый путь = отдельный узел, и
    # модель показывалась в списке десятки раз, а превью (лежит на ОДНОМ из путей) могло не
    # попасть в страницу вовсе. Теперь: один узел на ИМЯ, превью берём с того пути, где оно есть.
    #
    # V109 ГРАБЛЯ (жалоба владельца «ASM ... не выводит картинку»): у имени есть .asm И .drw,
    # и при равных связях побеждал ЧЕРТЁЖ — владелец видел «нет картинки сборки». Поэтому в
    # приоритете выбора представителя — ТИП: сборка > деталь > чертёж (чертёж лишь дополняет).
    _KPRI = {"ASSEMBLY": 0, "PART": 1, "MFG": 1, "DRAWING": 2}
    live = [k for k, v in nodes.items()
            if (out_.get(k) or in_.get(k) or v.get("i")) and not _svc(k)]
    live.sort(key=lambda k: (-(len(out_.get(k, ())) + len(in_.get(k, ()))),
                             # приоритет пути: сначала с превью (чтобы превью попало в узел)
                             0 if nodes[k].get("i") or nodes[k].get("i2") else 1,
                             # V109: при равенстве — тип (сборка важнее чертежа)
                             _KPRI.get((nodes[k].get("k") or "").upper(), 1),
                             k))
    # имя → лучший ключ-путь
    rep, rep_of = {}, {}
    for k in live:
        nm = nodes[k].get("n") or _norm((nodes[k].get("p") or k).split("\\")[-1])
        if nm not in rep:
            rep[nm] = k                     # первый в порядке приоритета = с превью
        rep_of[k] = nm
    keep_names = list(rep.keys())[:limit_nodes]
    keep = {rep[n] for n in keep_names}
    idx = {k: i for i, k in enumerate(sorted(keep))}      # ключ → номер (коротко)
    name_idx = {n: idx[rep[n]] for n in keep_names}       # имя → номер узла
    # перенос рёбер на «представителя» имени
    def remap(m):
        nm = rep_of.get(m)
        return rep.get(nm, m)
    out2, in2 = defaultdict(list), defaultdict(list)
    for m in keep:
        for e in out_m.get(m, []):
            t = remap(e["key"])
            if t in idx and t != m:
                out2[m].append({"key": t, "type": e["type"], "qty": e["qty"]})
        for e in in_m.get(m, []):
            f = remap(e["key"])
            if f in idx and f != m:
                in2[m].append({"key": f, "type": e["type"], "qty": e["qty"]})
    nd = {}
    for m in keep:
        v = nodes[m]
        full = v.get("p", "") or m
        nm = v.get("n") or _norm(full.split("\\")[-1])
        folder = full.rsplit("\\", 2)[-2] if "\\" in full else ""
        nd[idx[m]] = {"k": v.get("k", "?"), "v": v.get("v", ""), "m": bool(v.get("m")),
                      "i": v.get("i", ""), "i2": v.get("i2", ""),
                      "h": (v.get("h") or [])[:40],          # V109: история изменений файла
                      "s": v.get("s", 0), "nm": nm, "dir": folder,
                      # o — состав (что использует модель), n — входимость (кто использует её).
                      # V104: [номер, тип, количество] — ОДНА строка на соседа (без дублей).
                      "o": [[idx[e["key"]], e["type"], e["qty"]] for e in out2.get(m, [])],
                      "n": [[idx[e["key"]], e["type"], e["qty"]] for e in in2.get(m, [])]}
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
    # V107: реестр настроек для панели «НАСТРОЙКИ» в HTML — ОДИН источник с окном PLM Reader.
    # ВАЖНО: plm_settings импортируется ЛЕНИВО и с разрывом цикла (plm_reader ↔ plm_settings),
    # иначе при запуске `plm_graph.py` как скрипта import падал и spec оставался пустым.
    try:
        if "plm_reader" not in sys.modules:
            try:
                import plm_reader  # noqa: F401  (разрыв цикла импортов)
            except Exception:
                pass
        import plm_settings
        st["spec"] = plm_settings.settings_spec_json()
        st["cfg"] = {k: v for k, v in plm_settings.load_settings_file().items()}
    except Exception as e:                 # noqa: BLE001
        print("настройки для страницы не прочитаны: %s" % e)
        st["spec"] = []
        st["cfg"] = {k: v for k, v in cfg.items()}
    # V103 (24.10.2026) ЛЕНИВАЯ ЗАГРУЗКА: в HTML кладём ПЕРВУЮ ПОРЦИЮ (сразу рисуется),
    # остальные узлы уезжают в `CREO_GRAPH_data.js` (window.PLM_CHUNKS) — страница открывается
    # мгновенно, а список/граф наполняются по мере поступления порций.
    _write_chunks(nd, st)
    first_chunk, rest = _split_chunks(nd, st)
    return (page.replace("__DATA__", json.dumps(first_chunk["nodes"], ensure_ascii=False))
                .replace("__STATS__", json.dumps(first_chunk["stats"], ensure_ascii=False))
                .replace("__MEDIA__", rel))


DATA_JS = os.path.join(HERE, "CREO_GRAPH_data.js")


def _chunk_size():
    """Сколько узлов в одной порции (настройка `graph_chunk_nodes`, по умолчанию 1200)."""
    try:
        return max(200, int(load_settings().get("graph_chunk_nodes", 1200)))
    except Exception:
        return 1200


def _ordered_keys(nd):
    """Порядок узлов для страницы: сначала САМЫЕ СВЯЗАННЫЕ (они уходят в HTML сразу).

    V104: и `_split_chunks`, и `_write_chunks` ОБЯЗАНЫ идти по одному порядку — иначе первая
    порция и файл порций «разъезжаются», и часть моделей не попадает НИКУДА
    (грабля: `170META-2-МОДЕЛЬ-ВЕРХА` исчезала со страницы).
    """
    return sorted(nd.keys(),
                  key=lambda k: -(len(nd[k].get("o") or []) + len(nd[k].get("n") or [])))


def _split_chunks(nd, st):
    """Первую порцию — в HTML (сразу), остальные — в файл `CREO_GRAPH_data.js`."""
    keys = _ordered_keys(nd)
    size = _chunk_size()
    first_keys = keys[:size]
    first = {"nodes": {k: nd[k] for k in first_keys},
             "stats": dict(st, nodes=len(first_keys))}
    return first, [k for k in keys[size:]]


def _write_chunks(nd, st):
    """Записать ПОРЦИИ узлов в `CREO_GRAPH_data.js` (window.PLM_CHUNKS = [...]) — рядом с HTML.

    Порядок порций: сначала узлы С НАИБОЛЬШИМ числом связей (чтобы «живой» граф наполнялся
    осмысленно — первыми приходят самые связанные изделия).
    """
    size = _chunk_size()
    keys = _ordered_keys(nd)               # тот же порядок, что и в первой порции (V104)
    chunks = []
    for i in range(size, len(keys), size):
        part = {k: nd[k] for k in keys[i:i + size]}
        chunks.append({"nodes": part, "stats": dict(st, nodes=len(part))})
    try:
        with open(DATA_JS, "w", encoding="utf-8") as f:
            f.write("window.PLM_CHUNKS = ")
            json.dump(chunks, f, ensure_ascii=False, separators=(",", ":"))
            f.write(";\n")
    except Exception as e:                 # noqa: BLE001
        print("данные-порции не записаны: %s" % e)
    return len(chunks)


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
    _media_max = int(cfg.get("graph_media_limit", 0))       # V107: 0 = без предела
    _scan_budget = float(cfg.get("graph_scan_budget", 600))
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
    n_chunks = 0
    try:
        if os.path.isfile(DATA_JS):
            n_chunks = os.path.getsize(DATA_JS)
    except Exception:
        pass
    print("источник: %s | узлов %d | рёбер %d | с превью %d"
          % (src, len(nodes), len(edges), sum(1 for v in nodes.values() if v.get("i"))))
    print("-> %s  (+ порции: %s, %d КБ — догружаются страницей)"
          % (DST, os.path.basename(DATA_JS), n_chunks // 1024))
    if not no_open and cfg.get("graph_open_browser", True):
        try:
            import webbrowser
            webbrowser.open("file:///" + DST.replace("\\", "/"))
        except Exception:              # noqa: BLE001
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
