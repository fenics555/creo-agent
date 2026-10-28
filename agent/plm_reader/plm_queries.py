# -*- coding: utf-8 -*-
"""plm_queries.py — ПОСТРОЕНИЕ ПО БАЗЕ (V140, вынесено из `engine.py` по слову владельца 28.10.2026).

🔴 РАЗДЕЛЕНИЕ РАБОТ (нерушимое):
    `engine.py`      — СКАНЕР: читает ФАЙЛЫ и НАПОЛНЯЕТ базу. Строит НИЧЕГО.
    `plm_queries.py` — ЧТЕНИЕ/ПОСТРОЕНИЕ ПО БАЗЕ: то, что показывают окна и граф.
    `plm_links.py`   — ЕДИНСТВЕННЫЙ источник СВЯЗЕЙ (ДОГМА §4/§5).

Владелец: «Сканер наполняет всем возможным БД и всё, не строит ничего. А то там коды уже
раздуваются на тысячи линий».

Каждая функция ЗДЕСЬ работает ТОЛЬКО с базой (`connect()`), файлы Creo не читает.
В `engine.py` на месте каждой осталась КОРОТКАЯ обёртка-прокси — старые вызовы не сломаны.
"""
import os


def _engine():
    """Движок (сканер) — нужен только для `connect()`. Импорт ЛЕНИВЫЙ: разрывает цикл импортов."""
    import engine as _e
    return _e


def connect(ro=False, db=None):
    """Соединение с базой — берём у движка (одна реализация на инструмент)."""
    return _engine().connect(ro=ro, db=db)


# ── РЕЭКСПОРТ хелперов сканера: вынесенные функции их используют (`stem`, `service_stems`, …).
# Берём ЛЕНИВО (в момент вызова), чтобы не создавать цикл импортов при загрузке модуля.
# Список собран ПО ФАКТУ использования в этом файле (а не «на всякий случай»).
_HELPERS = ("stem", "active_db", "real", "role", "last_hist", "user_time", "names", "params",
            "service_stems", "config_pro_dirs", "service_models", "scan_config", "warehouse_db_dir",
            "published", "_versioned", "_base_dir", "norm_path", "family_of")


def __getattr__(name):
    """ЛЮБОЕ имя (хелперы, константы, `HISTRE`, `_PARAM_*`) — берём из движка ЛЕНИВО.

    Так вынесенные функции работают БЕЗ правок: их свободные имена разрешаются в `engine`.
    Владелец: «Сканер наполняет БД и всё, не строит ничего» — поэтому построители живут здесь,
    но пользуются хелперами сканера через эту единственную точку доступа.
    """
    return getattr(_engine(), name)


globals().update({_h: getattr(__import__("engine"), _h) for _h in _HELPERS
                  if hasattr(__import__("engine"), _h)})



# ------------------------------------------------------------------------------------------------
def model_info(model):
    """Паспорт модели из базы + сколько файлов и в сколько сборок входит.

    ГРАБЛЯ (07.10.2026): брали ПЕРВЫЙ файл по порядку пути — у изделия, где есть деталь,
    чертёж И оснастка (три файла на одно имя), побеждала пустая техкарта, и паспорт выглядел
    незаполненным («ревизия пусто, материал пусто, кто/когда пусто»). Теперь берём САМЫЙ
    ПОЛНЫЙ паспорт, а при равенстве — свежайший файл.
    """
    try:
        con = connect()
        rows = con.execute("SELECT designation,name,material,volume,rev,role,mtime FROM snapshots "
                           "WHERE model=? ORDER BY path", (model,)).fetchall()
        files = con.execute("SELECT COUNT(*) FROM snapshots WHERE model=?", (model,)).fetchone()[0]
        pars = con.execute("SELECT COUNT(*) FROM links WHERE child=?", (model,)).fetchone()[0]
        con.close()
    except Exception:
        return ("", "", "", 0, "", ""), 0, 0
    best, best_mt = ("", "", "", 0, "", ""), 0
    for d, n, mat, v, rev, r, mt in rows:
        cand = (d or "", n or "", mat or "", v or 0, rev or "", r or "")
        if _passport_better(cand, mt, best, best_mt):
            best, best_mt = cand, mt
    return best, files, pars

# ------------------------------------------------------------------------------------------------
def mfg_models(model, limit=60):
    """МОДЕЛЬНАЯ ОСНАСТКА изделия: MFG-родители из связей + MFG-модели с тем же префиксом имени.

    Возвращает [(модель, откуда)].
    """
    m = stem(model)
    out = []
    try:
        con = connect()
        for (p,) in con.execute("SELECT l.parent FROM links l JOIN snapshots s ON s.model=l.parent "
                                "WHERE l.child=? AND s.role='MFG' GROUP BY l.parent", (m,)):
            out.append((p, "связь"))
        if "-" in m:
            prefix = m.rsplit("-", 1)[0] + "-"
            if len(prefix) >= 6:
                for (s,) in con.execute(
                        "SELECT DISTINCT model FROM snapshots WHERE role='MFG' AND model LIKE ? "
                        "AND model<>? ORDER BY model LIMIT ?", (prefix + "%", m, limit)):
                    if all(s != o[0] for o in out):
                        out.append((s, "по имени"))
        con.close()
    except Exception:
        return out
    return out

# ------------------------------------------------------------------------------------------------
def derived_bases(model):
    """Заготовки/отливки модели: из таблицы `derived` + из роли; хеши, шаблоны и «копию от себя» отсекаем."""
    m = stem(model)
    svc = service_stems()
    out = []
    try:
        con = connect()
        for b, k in con.execute("SELECT base, kind FROM derived WHERE child=?", (m,)):
            if not b:
                continue
            bs = stem(b)
            if bs == m or bs.upper() in svc:            # «копия от себя» и шаблоны — не родословная
                continue
            if not _hash_like(b):
                out.append((b, k or ""))
            else:
                out.append(("", "hash"))               # имя не найдено (в файле только код)
        con.close()
    except Exception:
        return []
    for b, k in role_bases(model):
        if all(b != o[0] for o in out):
            out.append((b, k))
    # 07.10.2026: «МОДЕЛЬ СКОПИРОВАНА ОТ …» — Creo пишет это в САМОМ файле (`from_mdl_name`),
    # в базе такого вида связи нет. Читаем файл, чтобы ответ был сразу, без перескана (З12: ответ
    # проверяемый, берётся из файла, а не со слов). Ищем в детали (.prt), иначе в других файлах.
    try:
        con = connect()
        paths = [r[0] for r in con.execute("SELECT path FROM snapshots WHERE model=?", (m,))]
        con.close()
    except Exception:
        paths = []
    prts = [p for p in paths if ".prt" in p.lower()]
    for p in (prts or paths):
        cf = copy_from_file(p)
        if cf:
            cs = stem(cf)
            if cs != m and cs.upper() not in svc and all(cf != o[0] for o in out):
                out.append((cf, "копия"))
            break
    return out

# ------------------------------------------------------------------------------------------------
def derived_children(base, limit=500):
    """Кто сделан ИЗ этой модели (обратная связь): список (child, kind).
    Строится из уже готовой таблицы derived — без чтения Creo-файлов."""
    m = stem(base)
    svc = service_stems()
    try:
        con = connect()
        rows = con.execute(
            "SELECT child, kind FROM derived WHERE base=? ORDER BY child LIMIT ?",
            (m, limit)).fetchall()
        con.close()
        return [(r[0], r[1] or "") for r in rows if (r[0] or "").upper() not in svc]
    except Exception:
        return []

# ------------------------------------------------------------------------------------------------
def derived_map():
    """Все связи «деталь ← заготовка/отливка»: {child: [(base, kind)]}."""
    out = {}
    try:
        con = connect()
        for c, b, k in con.execute("SELECT child, base, kind FROM derived"):
            out.setdefault(c, []).append((b, k or ""))
        con.close()
    except Exception:
        return {}
    return out

# ------------------------------------------------------------------------------------------------
def plm_tree_data():
    """ВСЁ дерево ПЛМ одним заходом: (верхние сборки, состав, паспорта+счётчики, заготовки)."""
    tops, children, info, derived = [], {}, {}, {}
    try:
        con = connect()
        # V134: СОСТАВ = физические связи. `mentions` (упоминание имени в байтах детали/чертежа)
        # и `family` (исполнения — виртуальные варианты генерика, НЕ детали состава) сюда не идут.
        # Иначе дерево производства мусорилось: 1375 исполнений DIN912 выглядели деталями.
        rows = con.execute("SELECT parent, child, SUM(qty) FROM links "
                           "WHERE source IS NULL OR source NOT IN ('mentions','family') "
                           "GROUP BY parent, child").fetchall()
        kids = set()
        for p, c, q in rows:
            children.setdefault(p, []).append((c, q or 1))
            kids.add(c)
        tops = sorted(set(children) - kids)
        for c, b, k in con.execute("SELECT child, base, kind FROM derived"):
            derived.setdefault(c, []).append((b, k or ""))
        agg, agmt = {}, {}
        for m, d, n, mat, v, rev, r, mt in con.execute(
                "SELECT model,designation,name,material,volume,rev,role,mtime FROM snapshots"):
            cand = (d or "", n or "", mat or "", v or 0, rev or "", r or "")
            if m not in agg or _passport_better(cand, mt, agg[m], agmt.get(m, 0)):
                agg[m] = cand            # паспорт строки изделия — САМЫЙ ПОЛНЫЙ файл (не первый)
                agmt[m] = mt
        fcnt = dict(con.execute("SELECT model,COUNT(*) FROM snapshots GROUP BY model"))
        pcnt = dict(con.execute("SELECT child,COUNT(*) FROM links GROUP BY child"))
        con.close()
    except Exception:
        return tops, children, info, derived
    for m in set(agg) | set(children) | set(derived):
        a = agg.get(m, ("", "", "", 0, "", ""))
        info[m] = a + (fcnt.get(m, 0), pcnt.get(m, 0))
    return tops, children, info, derived

# ------------------------------------------------------------------------------------------------
def count_tops():
    try:
        con = connect()
        n = con.execute("SELECT COUNT(*) FROM (SELECT DISTINCT parent FROM links WHERE parent NOT IN "
                        "(SELECT DISTINCT child FROM links))").fetchone()[0]
        con.close()
        return n
    except Exception:
        return 0

# ------------------------------------------------------------------------------------------------
def models_info(models):
    """Паспорта и счётчики для НАБОРА моделей одним запросом.

    model -> (обозначение, наименование, материал, объём, ревизия, роль, файлов, входит в сборок)
    """
    out = {}
    models = list(models)
    if not models:
        return out
    q = ",".join("?" * len(models))
    try:
        con = connect()
        agg = {}
        for m, d, n, mat, v, rev, r in con.execute(
                "SELECT model,designation,name,material,volume,rev,role FROM snapshots "
                "WHERE model IN (%s)" % q, models):
            if m not in agg:
                agg[m] = (d or "", n or "", mat or "", v or 0, rev or "", r or "")
        fcnt = dict(con.execute("SELECT model,COUNT(*) FROM snapshots WHERE model IN (%s) "
                                "GROUP BY model" % q, models))
        pcnt = dict(con.execute("SELECT child,COUNT(*) FROM links WHERE child IN (%s) "
                                "GROUP BY child" % q, models))
        con.close()
    except Exception:
        return out
    for m in models:
        a = agg.get(m, ("", "", "", 0, "", ""))
        out[m] = (a[0], a[1], a[2], a[3], a[4], a[5], fcnt.get(m, 0), pcnt.get(m, 0))
    return out

# ------------------------------------------------------------------------------------------------
def plm_tops(limit=500):
    """Верхние СБОРКИ: модели с составом, которые сами ни в одну сборку не входят."""
    try:
        con = connect()
        rows = con.execute("SELECT DISTINCT parent FROM links WHERE parent NOT IN "
                           "(SELECT DISTINCT child FROM links) ORDER BY parent LIMIT ?",
                           (limit,)).fetchall()
        con.close()
        return [r[0] for r in rows]
    except Exception:
        return []

# ------------------------------------------------------------------------------------------------
def plm_children(model, sources=None):
    """СОСТАВ изделия из базы: [(ребёнок, количество)]. Служебные (шаблоны) отсеиваются.

    ГРАБЛЯ 28.10.2026 (владелец: «у дин912 связей 5, не показывает связи исполнений»):
    запрос брал ВСЕ источники `links` в одну кучу — `plm_tree` (физический состав),
    `asm_comp` (структура файла) и `family` (ТАБЛИЦА СЕМЕЙСТВА: 1375 исполнений DIN912).
    Из-за этого 1375 исполнений выглядели как 1375 обычных ДЕТАЛЕЙ в составе, а мусорные
    связи (фантомные имена) не отсеивались. Теперь источник можно выбрать:
    `sources=None` — состав БЕЗ исполнений (по умолчанию, как и было по смыслу);
    `sources=("family",)` — только исполнения генерика (для отдельного раздела).
    """
    m = stem(model)
    svc = service_stems()
    try:
        con = connect()
        if sources:
            q = ",".join("?" * len(sources))
            rows = con.execute("SELECT child, SUM(qty) FROM links WHERE parent=? "
                               "AND source IN (%s) GROUP BY child ORDER BY child" % q,
                               (m,) + tuple(sources)).fetchall()
        else:
            # БЕЗ `family` и БЕЗ `mentions`: исполнения — НЕ состав (они отдельным разделом),
            # а `mentions` — просто УПОМИНАНИЕ имени в байтах детали/чертежа, тоже не состав.
            rows = con.execute("SELECT child, SUM(qty) FROM links WHERE parent=? "
                               "AND (source IS NULL OR source NOT IN ('family','mentions')) "
                               "GROUP BY child ORDER BY child", (m,)).fetchall()
        con.close()
        return [(c, q or 1) for c, q in rows if (c or "").upper() not in svc]
    except Exception:
        return []

# ------------------------------------------------------------------------------------------------
def plm_instances(model, limit=5000):
    """ИСПОЛНЕНИЯ генерика (таблица семейства): [(исполнение, кол-во)] — ОТДЕЛЬНО от состава.

    Владелец: «сами исполнения они как и где должны выводиться?» — отдельным разделом
    «Исполнения» в окне «Дерево связей» и на HTML-странице, а НЕ вперемешку с составом.
    Читаем ДВА источника: таблицу `family` (как записал скан: generic→instance) И связи
    `links` с источником `family` (их пишет тот же скан — так исполнения видны и в графе).
    """
    m = stem(model)
    out, seen = [], set()
    try:
        con = connect(ro=True)
        try:
            for inst, in con.execute("SELECT instance FROM family WHERE generic=? ORDER BY instance",
                                     (m,)):
                if inst and inst not in seen:
                    seen.add(inst)
                    out.append((inst, 1))
        except Exception:                          # таблицы family может не быть — не беда
            pass
        try:
            for inst, q in con.execute("SELECT child, SUM(qty) FROM links WHERE parent=? "
                                       "AND source='family' GROUP BY child ORDER BY child", (m,)):
                if inst and inst not in seen:
                    seen.add(inst)
                    out.append((inst, q or 1))
        except Exception:                          # noqa: BLE001
            pass
        con.close()
    except Exception:                              # noqa: BLE001
        return []
    return out[:int(limit)]

# ------------------------------------------------------------------------------------------------
def plm_parents(model):
    """Куда ВХОДИТ изделие: [(родитель, количество)]. Служебные (шаблоны) отсеиваются.

    V134: `mentions` (упоминание имени в байтах ДЕТАЛИ/ЧЕРТЕЖА) НЕ считаем входимостью.
    ГРАБЛЯ (владелец: «у дин912 связей 5»): в `din931.prt.1` есть `DIN912-UNC` как ЗНАЧЕНИЕ
    ПАРАМЕТРА таблицы семейства — рождалась ложная «входимость» DIN912 в DIN931. Из 5 «связей»
    DIN912 реальной была одна (сборка SCREWS_VZ); остальные — совпадение байтов.
    Настоящая входимость: `asm_comp` (структура сборки) и `plm_tree` (сборка по вхождению),
    `family` (исполнение → генерик).
    """
    m = stem(model)
    svc = service_stems()
    try:
        con = connect()
        rows = con.execute("SELECT parent, SUM(qty) FROM links WHERE child=? "
                           "AND (source IS NULL OR source<>'mentions') "
                           "GROUP BY parent ORDER BY parent", (m,)).fetchall()
        con.close()
        return [(p, q or 1) for p, q in rows if (p or "").upper() not in svc]
    except Exception:
        return []

# ------------------------------------------------------------------------------------------------
def plm_up_data(model, depth=8):
    """ВХОДИМОСТЬ ВВЕРХ одним заходом: {модель: [(родитель, кол-во)]} по всей цепочке сборок.

    V104: кол-во СУММИРУЕТСЯ в SQL (`GROUP BY child,parent`) — иначе одна и та же пара
    повторялась столько раз, сколько путей у имени (жалоба владельца: «HB72501-401 подряд»).
    Служебные (шаблоны) не попадают в цепочку.
    """
    out = {}
    svc = service_stems()
    try:
        con = connect(ro=True)
        frontier = [stem(model)]
        seen = set(frontier)
        for _ in range(depth):
            if not frontier:
                break
            q = ",".join("?" * len(frontier))
            # V134: `mentions` (упоминание имени в байтах детали/чертежа) — НЕ входимость
            rows = con.execute("SELECT child,parent,SUM(qty) FROM links WHERE child IN (%s) "
                               "AND (source IS NULL OR source<>'mentions') "
                               "GROUP BY child,parent" % q, frontier).fetchall()
            nxt = []
            for ch, par, qty in rows:
                if (par or "").upper() in svc:
                    continue
                out.setdefault(ch, []).append((par, qty or 1))
                if par not in seen:
                    seen.add(par)
                    nxt.append(par)
            frontier = nxt
        con.close()
    except Exception:
        return {}
    return out

# ------------------------------------------------------------------------------------------------
def plm_down_data(model, depth=2):
    """СОСТАВ вниз на N уровней: {модель: [(ребёнок, кол-во)]}. Служебные (шаблоны) не попадают.

    V104: кол-во СУММИРУЕТСЯ в SQL (`GROUP BY parent,child`) — одна строка на компонент,
    без повторов «по числу путей» (та же грабля, что в `plm_up_data`).
    """
    out = {}
    svc = service_stems()
    try:
        con = connect(ro=True)
        frontier = [stem(model)]
        for _ in range(depth):
            if not frontier:
                break
            q = ",".join("?" * len(frontier))
            rows = con.execute("SELECT parent,child,SUM(qty) FROM links WHERE parent IN (%s) "
                               "GROUP BY parent,child" % q, frontier).fetchall()
            nxt = []
            for par, ch, qty in rows:
                if (ch or "").upper() in svc:
                    continue
                out.setdefault(par, []).append((ch, qty or 1))
                nxt.append(ch)
            frontier = nxt
        con.close()
    except Exception:
        return {}
    return out

# ------------------------------------------------------------------------------------------------
def full_tree_lines(model, depth=6, show_internal=False):
    """Строки ПОЛНОГО дерева связей: [(текст, вид, груз)] — для вкладки «Дерево текстом».

    вид: `head` — заголовок, `node` — узел (груз = имя модели), `rel` — связь,
    `more` — «… ещё N» (груз = имя модели; клик = показать ВЕСЬ список),
    `note` — примечание. Читается только база, Creo не нужен.
    """
    m = stem(model)
    con = connect()
    svc = service_stems()      # 07.10.2026: служебные шаблоны (SBORKA_MFG/SBORKA_MM/MM_PART…) — НЕ связи изделия
    kids, parents = defaultdict(list), defaultdict(list)
    # V134: `mentions` (упоминание имени в байтах детали/чертежа) и `family` (исполнения —
    # виртуальные варианты генерика) в ДЕРЕВО не идут: иначе 1375 исполнений DIN912
    # показывались как детали состава, а ложные «связи по параметру» мусорили входимость.
    for par, ch, qty in con.execute("SELECT parent, child, qty FROM links "
                                    "WHERE source IS NULL OR source NOT IN ('mentions','family')"):
        if (par or "").upper() in svc or (ch or "").upper() in svc:
            continue
        kids[par].append((ch, qty or 1))
        parents[ch].append((par, qty or 1))
    base_of, made_of, selfref = defaultdict(list), defaultdict(list), defaultdict(list)
    for ch, base, kind in con.execute("SELECT child, base, kind FROM derived"):
        if not base:
            continue
        if (ch or "").upper() in svc or (base or "").upper() in svc:
            continue
        if base == ch:                      # имя совпало (мастер-модель) — не путать со связью
            selfref[ch].append(kind or "")
            continue
        base_of[ch].append((base, kind or ""))
        made_of[base].append((ch, kind or ""))
    snap = {r[0]: r for r in con.execute("SELECT model, name, volume, rev, role FROM snapshots")}
    fpath = {}                       # 07.10.2026: пути файлов изделий — чтобы добрать «КОПИЮ ОТ»
    for _m, _p in con.execute("SELECT model, path FROM snapshots "   # из САМОГО файла, не дожидаясь
                              "WHERE path LIKE '%.prt.%' OR path LIKE '%.asm.%'"):  # полного скана
        if _m not in fpath or (".prt" in _p.lower() and ".prt" not in fpath[_m].lower()):
            fpath[_m] = _p           # деталь предпочитаем сборке (у детали запись «от … .PRT»)
    con.close()

    def clean(x):
        return "".join(c for c in str(x) if c.isprintable())   # в базе бывают управляющие байты

    def lab(x):
        nm = clean(x)
        r = snap.get(nm) or snap.get(x)
        if not r:
            return nm + ("   (внутренний код Creo)" if _internal_id(nm) else "")
        return "%s%s%s%s" % (nm,
                             ("  «%s»" % clean(r[1])) if r[1] else "",
                             ("  %.0f мм³" % r[2]) if r[2] else "",
                             ("  rev%s" % r[3]) if r[3] else "")

    L = []
    _fbudget = [25]                  # не больше 25 файлов на построение дерева (чтобы не тормозило)

    def file_base(x):
        """«Копия от» ИЗ ФАЙЛА — если в базе такой связи ещё нет (скан мог её не записать)."""
        if _fbudget[0] <= 0:
            return ""
        p = fpath.get(x)
        if not p:
            return ""
        _fbudget[0] -= 1
        return copy_from_file(p)

    def add(t, kind="rel", p=None):
        L.append((t, kind, p))

    add("ПОЛНОЕ ДЕРЕВО СВЯЗЕЙ: моделей %d, состав %d, наследование/производная %d"
        % (len(snap), sum(len(v) for v in kids.values()), sum(len(v) for v in base_of.values())),
        "head")
    add("корень: %s   · глубина %d   · клик по изделию = оно станет корнем"
        % (m, depth), "head")
    seen = set()

    def rel_lines(x, pref, last, with_made):
        pad = pref + ("   " if last else "│  ")
        for b, k in base_of.get(x, []):
            add("%s⟵ %s: %s%s" % (pad, k, lab(b),
                                  "   (внутренний код Creo)" if _internal_id(clean(b)) else ""))
        for k in selfref.get(x, []):
            add("%s⟲ %s от мастер-модели с тем же именем" % (pad, k))
        _cf = file_base(x)                     # «копия от» — из файла, даже если база знает другое
        if _cf:
            _cs = stem(_cf)
            if _cs and all(_cs.lower() != (b or "").lower() for b, _k in base_of.get(x, [])):
                add("%s⟵ копия: %s" % (pad, clean(_cf)))
        if not with_made:
            return
        made = [(c, k) for c, k in made_of.get(x, [])
                if show_internal or not _internal_id(clean(c))]
        for c, k in made[:12]:
            add("%s⟶ из неё: %s  (%s)" % (pad, lab(c), k))
        if len(made) > 12:
            add("%s⟶ … ещё сделано из неё: %d   ← клик = весь список"
                % (pad, len(made) - 12), "more", clean(x))
        if len(made_of.get(x, [])) - len(made):
            add("%s⟶ … ещё %d с внутренними кодами Creo (подними галку «внутренние коды»)"
                % (pad, len(made_of.get(x, [])) - len(made)))
        r = snap.get(x)
        if r and "MFG" in (clean(r[4] or "")).upper():
            add("%s⚙ модельная оснастка (MFG)" % pad)

    def walk(x, pref, last, d):
        add("%s%s%s" % (pref, "└─ " if last else "├─ ", lab(x)), "node", clean(x))
        rel_lines(x, pref, last, True)
        if x in seen:
            add("%s   ⋯ (уже показано выше)" % pref)
            return
        seen.add(x)
        ch = kids.get(x, [])
        if not ch:
            return
        if d >= depth:
            add("%s   … глубже не раскрываю (уровень %d) — подними «Глубину» и «Обновить»"
                % (pref, d))
            return
        for i, (c, q) in enumerate(ch):
            walk(c, pref + ("   " if last else "│  "), i == len(ch) - 1, d + 1)

    walk(m, "", True, 1)

    add("")
    add("ВХОДИМОСТЬ ВВЕРХ (состав) + НАСЛЕДОВАНИЕ:", "head")
    seen2 = set()

    def up(x, pref, last, d):
        add("%s%s%s" % (pref, "└─ " if last else "├─ ", lab(x)), "node", clean(x))
        rel_lines(x, pref, last, False)
        if x in seen2:
            add("%s   ⋯ (уже показано выше)" % pref)
            return
        seen2.add(x)
        ps = parents.get(x, [])
        if d >= depth:
            return
        for i, (p, q) in enumerate(ps):
            up(p, pref + ("   " if last else "│  "), i == len(ps) - 1, d + 1)

    up(m, "", True, 1)
    if not parents.get(m):
        add("   (по СОСТАВУ выше нигде не входит — смотри ⟵ наследование/производную)")
    return L

# ------------------------------------------------------------------------------------------------
def made_of_list(model, limit=0):
    """ВЕСЬ список «кто сделан ИЗ модели» из `derived`: [(имя, вид, наименование, объём, rev)].

    limit=0 — без предела (для окна «показать весь список» у строки «… ещё N»)."""
    m = stem(model)
    svc = service_stems()
    if m.upper() in svc:
        return []          # у служебного шаблона списка «сделано из» для человека нет
    try:
        con = connect()
        snap = {r[0]: r for r in con.execute("SELECT model, name, volume, rev FROM snapshots")}
        rows = con.execute("SELECT child, kind FROM derived WHERE base=?", (m,)).fetchall()
        con.close()
    except Exception:
        return []
    out = []
    for ch, kind in rows:
        if (str(ch) or "").upper() in svc:
            continue
        nm = "".join(c for c in str(ch) if c.isprintable())
        r = snap.get(nm) or snap.get(ch) or (None, None, None, None)
        out.append((nm, kind or "", r[1] or "", r[2] or 0, r[3] or ""))
    out.sort(key=lambda x: x[0])
    if limit:
        out = out[:int(limit)]
    return out

# ------------------------------------------------------------------------------------------------
def do_where(model):
    con = connect()
    # V134: `mentions` (упоминание имени в байтах детали/чертежа) — НЕ входимость
    rows = con.execute("SELECT parent, SUM(qty) FROM links WHERE child=? "
                       "AND (source IS NULL OR source<>'mentions') "
                       "GROUP BY parent ORDER BY SUM(qty) DESC",
                       (stem(model),)).fetchall()
    con.close()
    print("«%s» входит в %d сборок:" % (stem(model), len(rows)))
    for par, qty in rows:
        print("   %-42s x%d" % (par, qty))

# ------------------------------------------------------------------------------------------------
def do_tree(model, depth):
    con = connect()
    kids, parents = defaultdict(list), set()
    # V134: без `mentions` (упоминания в байтах) и `family` (исполнения) — это не состав
    for par, ch, qty in con.execute("SELECT parent, child, qty FROM links "
                                    "WHERE source IS NULL OR source NOT IN ('mentions','family')"):
        kids[par].append((ch, qty))
        parents.add(ch)
    snap = {r[0]: r for r in con.execute("SELECT model, name, volume, rev FROM snapshots")}
    con.close()

    def lab(m):
        r = snap.get(m)
        if not r:
            return m
        nm = ("  «%s»" % r[1]) if r[1] else ""
        vol = ("  %.0f мм³" % r[2]) if r[2] else ""
        rv = ("  rev%s" % r[3]) if r[3] else ""
        return "%s%s%s%s" % (m, nm, vol, rv)

    tops = [stem(model)] if model else sorted(m for m in snap if m not in parents)
    print("ДЕРЕВО ПРОИЗВОДСТВА: моделей %d, связей %d%s"
          % (len(snap), sum(len(v) for v in kids.values()),
             ("  (корень: %s)" % stem(model)) if model else ""))
    seen = set()

    def walk(m, pref, last, d):
        if d > depth:
            return
        print("%s%s%s" % (pref, "└─ " if last else "├─ ", lab(m)))
        if m in seen:
            print("%s   ⋯ (уже показано выше)" % pref)
            return
        seen.add(m)
        ch = kids.get(m, [])
        for i, (c, q) in enumerate(ch):
            walk(c, pref + ("   " if last else "│  "), i == len(ch) - 1, d + 1)

    shown = tops[:60]
    for i, t in enumerate(shown):
        walk(t, "", i == len(shown) - 1, 1)
        print()

# ------------------------------------------------------------------------------------------------
def do_rename_plan(old, new):
    """СУХОЙ ПРОГОН переименования: модель + чертёж + все сборки-владельцы + порядок сохранения."""
    o = stem(old)
    n = stem(new) if new else ""
    con = connect()
    snap = {r[0] for r in con.execute("SELECT model FROM snapshots")}
    parents = defaultdict(set)
    # V134: `mentions` не считаем владельцем (иначе в план переименования попадали бы
    # детали/чертежи, где имя просто УПОМЯНУТО в параметрах — не настоящие владельцы)
    for par, ch in con.execute("SELECT parent, child FROM links "
                               "WHERE source IS NULL OR source<>'mentions'"):
        parents[ch].add(par)
    con.close()
    if not n:
        print("нужно: rename-plan СТАРОЕ_ИМЯ НОВОЕ_ИМЯ")
        return
    seen, order, stack = set(), [], list(parents.get(o, ()))
    while stack:
        p = stack.pop()
        if p in seen:
            continue
        seen.add(p)
        order.append(p)
        stack.extend(parents.get(p, ()))
    print("ПЛАН ПЕРЕИМЕНОВАНИЯ (сухой прогон, Creo не нужен) — по скиллу creoson_rename_mechanism")
    print("  было : %s  (модель/деталь или сборка)" % o)
    print("  станет: %s" % n)
    print("  чертёж: %s.drw  (%s)" % (o, "есть в базе" if o in snap else "в базе не виден"))
    print("  сборок-владельцев: %d" % len(order))
    for i, p in enumerate(order, 1):
        print("    %2d. %s" % (i, p))
    print("  ПОРЯДОК:")
    print("   1) загрузить (display:false): модель, её чертёж, ВСЕ сборки-владельцы;")
    print("   2) file:rename {file: %s, new_name: %s, onlysession:true}   (модель)" % (o, n))
    print("   3) file:rename {file: %s.drw, new_name: %s.drw, onlysession:true} + drawing:regenerate" % (o, n))
    print("   4) save СНИЗУ ВВЕРХ: модель → сборки-владельцы → ЧЕРТЁЖ ПОСЛЕДНИМ;")
    print("   5) старые версии %s.* — в backup (не удалять); 6) file:erase всех загруженных." % o)
    print("  ИСПОЛНЕНИЕ — только при запущенном Creo (CREO-START) + CREOSON, под щитом согласования.")
