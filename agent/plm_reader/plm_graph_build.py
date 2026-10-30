# -*- coding: utf-8 -*-
"""plm_graph_build.py — ГРАФ-ПОСТРОИТЕЛЬ (V142, слово владельца 30.10.2026).

🔴 ЗАКОН ВЛАДЕЛЬЦА (дословно):
    «ГРАФ-построитель по единой базе по системе ЧИТАЕТ ВСЁ, ПИШЕТ ТОЛЬКО В СВОЁ.
     Делает полный граф связей всей базы. Далее нам нужно будет ХТМЛ окно подключить
     к этой базе и основное окно ПЛМ ридера».
    «связи и графсвязи уже есть, единая база данных, иных связей нет и быть не может.
     И ХТМЛ окно должно не заново всё строить, а с нужными настройками просто выводить».

МЕСТО В КОНВЕЙЕРЕ (§2.1 STRATEGY_PLM.md):
    1. СКАНЕР      (engine.scan_to_base)      → ФАЙЛЫ → единая база (origin='real')
    2. ДОСТРОИТЕЛЬ (plm_build_links.py)       → БАЗА  → links/derived (origin='built')
    3. ГРАФ-ПОСТРОИТЕЛЬ (ЭТОТ ФАЙЛ)           → БАЗА  → graph_nodes/graph_edges/graph_metrics
    4. ПОКАЗ       (окно ПЛМ, HTML)           → только читает graph_*

СВЯЗИ НЕ ДУБЛИРУЮТСЯ: рёбра берутся из ЕДИНОГО источника `plm_links.edges()` (ДОГМА §4/§5),
который сам читает `links` + `derived`. Здесь — только раскладка по таблицам графа,
счётчики и метрики. Второго построения связей НЕТ.

ЗАПУСК:  python plm_graph_build.py            — построить граф (пишет в активную базу)
         python plm_graph_build.py --check    — только показать объём, НЕ писать
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import engine  # noqa: E402

NODES = "graph_nodes"
EDGES = "graph_edges"
METRICS = "graph_metrics"


def _kind_of_model(model, path):
    """ТИП модели (деталь/сборка/мануфактуринг/чертёж) — по расширению и имени файла.

    ⚠️ Не путать с ВИДОМ СВЯЗИ (он в рёбрах). Здесь — что за объект.
    """
    p = (path or model or "").lower()
    base = os.path.basename(p)
    if ".drw" in base:
        return "чертёж"
    if base.startswith("mfg") or "mfg" in base or "manufact" in base:
        return "мануфактуринг"
    if ".asm" in base:
        return "сборка"
    return "деталь"


def build(check_only=False, engine_mod=None):
    """ПОСТРОИТЬ ПОЛНЫЙ ГРАФ по единой базе. Возвращает словарь-отчёт.

    Читает ВСЁ (snapshots + links + derived — через `plm_links`), пишет ТОЛЬКО в
    `graph_nodes` / `graph_edges` / `graph_metrics`.
    """
    eng = engine_mod or engine
    t0 = time.time()
    import plm_links as L

    edges_raw = L.edges(eng)          # ЕДИНЫЙ источник рёбер (второго построения НЕТ!)
    con = eng.connect()
    res = {"nodes": 0, "edges": 0, "by_kind": {}, "by_dir": {}, "secs": 0.0}
    try:
        # ── узлы: из snapshots (модель, путь, папка, размер, объём, материал, Creo, ревизия)
        nodes = {}
        for row in con.execute("SELECT model, path, folder, size, volume, material, creo, rev "
                               "FROM snapshots"):
            m = (row[0] or "").strip()
            if not m or L.is_service(m):
                continue
            cur = nodes.get(m)
            # путь-представитель: самый свежий по размеру (у модели много версий)
            if cur is None or int(row[3] or 0) >= int(cur[4] or 0):
                nodes[m] = [m, row[1] or "", row[2] or "", row[3] or 0,
                            float(row[4] or 0), row[5] or "", row[6] or "", row[7] or ""]
        # ── счётчики связей у узла (вниз/вверх) — честными проходами, без временных меток
        down, up = {}, {}
        for e in edges_raw:
            if e["dir"] == "down":
                down[e["from"]] = down.get(e["from"], 0) + 1
                up[e["to"]] = up.get(e["to"], 0) + 1
            elif e["dir"] == "up":
                up[e["from"]] = up.get(e["from"], 0) + 1
                down[e["to"]] = down.get(e["to"], 0) + 1

        if check_only:
            res["nodes"] = len(nodes)
            res["edges"] = len(edges_raw)
            for e in edges_raw:
                res["by_kind"][e["kind"]] = res["by_kind"].get(e["kind"], 0) + 1
                res["by_dir"][e["dir"]] = res["by_dir"].get(e["dir"], 0) + 1
            res["secs"] = round(time.time() - t0, 2)
            return res


        # ── ЗАПИСЬ: граф — производная базы, обновляется ЦЕЛИКОМ (всегда актуален)
        con.execute("DELETE FROM %s" % NODES)
        con.execute("DELETE FROM %s" % EDGES)
        con.execute("DELETE FROM %s" % METRICS)

        # признак превью — по файлам в папке media (быстро, без чтения моделей)
        media_names = set()
        try:
            media_dir = eng.media_dir_for()
            if media_dir and os.path.isdir(media_dir):
                media_names = {f.lower() for f in os.listdir(media_dir)}
        except Exception:
            media_names = set()

        nrows, n_kinds = [], {}
        for m, (mm, path, folder, size, vol, mat, creo, rev) in nodes.items():
            kind = _kind_of_model(mm, path)
            n_kinds[kind] = n_kinds.get(kind, 0) + 1
            has_media = 1 if (path and os.path.basename(path).lower() in media_names) else 0
            nrows.append((mm, kind, folder, path, size, vol, mat, creo, rev,
                          down.get(mm, 0), up.get(mm, 0), has_media))
        con.executemany(
            "INSERT OR REPLACE INTO %s (model,kind,folder,path,size,volume,material,creo,rev,"
            "n_down,n_up,has_media) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)" % NODES, nrows)
        res["nodes"] = len(nrows)

        erows = [(e["from"], e["to"], e["kind"], e["dir"], e.get("origin", "real"),
                  int(e.get("qty") or 1), e.get("channel", "")) for e in edges_raw]
        con.executemany(
            'INSERT INTO %s ("from","to",kind,dir,origin,qty,channel) VALUES (?,?,?,?,?,?,?)' % EDGES,
            erows)
        res["edges"] = len(erows)
        for e in edges_raw:
            res["by_kind"][e["kind"]] = res["by_kind"].get(e["kind"], 0) + 1
            res["by_dir"][e["dir"]] = res["by_dir"].get(e["dir"], 0) + 1

        # ── метрики: сводка графа (шапка/статистика читает отсюда, а не считает заново)
        met = [("built_at", time.strftime("%Y-%m-%d %H:%M:%S")),
               ("nodes", str(res["nodes"])), ("edges", str(res["edges"]))]
        for k, v in sorted(res["by_kind"].items()):
            met.append(("edges_" + k, str(v)))
        for k, v in sorted(res["by_dir"].items()):
            met.append(("edges_dir_" + k, str(v)))
        for k, v in sorted(n_kinds.items()):
            met.append(("nodes_" + k, str(v)))
        con.executemany("INSERT OR REPLACE INTO %s (k,v) VALUES (?,?)" % METRICS, met)
        con.commit()
        res["secs"] = round(time.time() - t0, 2)
    finally:
        try:
            con.close()
        except Exception:
            pass
    return res


def report(res, check_only=False):
    print("=== ГРАФ-ПОСТРОИТЕЛЬ — %s ===" % ("ПРОВЕРКА (не пишет)" if check_only else "ПОСТРОЕНО"))
    print("узлов :", res.get("nodes", 0))
    print("рёбер :", res.get("edges", 0))
    print("по видам:", res.get("by_kind", {}))
    print("по направлению:", res.get("by_dir", {}))
    print("за %.2f с" % res.get("secs", 0.0))


if __name__ == "__main__":
    chk = "--check" in sys.argv
    report(build(check_only=chk), chk)

