# -*- coding: utf-8 -*-
"""map_tools.py: карта проекта — корневые каталоги и топ моделей по связям.

03.10.2026: переведена на базу ПЛМ-READER. Было три LEFT JOIN по агентским `usage/bom/links`,
из которых `usage` пуст с 27.09, — карта теряла почти все связи. Теперь одна таблица `links`.
"""
import plm_reader_tools as PRT

# ВНИМАНИЕ (ЖИВАЯ НАХОДКА 04.10.2026): блок `TOOLS` стоял ВЫШЕ функции build_map, и при
# загрузке реестра Python падал с «name 'build_map' is not defined» — блок map_tools
# НЕ ПОДКЛЮЧАЛСЯ ВОВСЕ (цитата из лога: «реестр: блок <map_tools> НЕ загружен»).
# Реестр грузит блоки по glob, но NameError на импорте глушил весь блок.
# Теперь объявление TOOLS стоит ПОСЛЕ функции — как в остальных блоках дома.


def build_map(top_n=100):
    """Корни папок и топ моделей по числу связей (вниз + вверх) из links ПЛМ-READER."""
    E = PRT.engine()
    c = E.connect(ro=True)
    try:
        # 03.10.2026: было без GROUP BY — одно обозначение приходило столько раз, сколько
        # у него версий файлов, и карта показывала MM_PART трижды. Теперь одна строка на изделие.
        rows = c.execute(
            "SELECT designation, MIN(path) AS path, COALESCE(dn,0)+COALESCE(up,0) AS links FROM ("
            "  SELECT s.designation AS designation, s.path AS path,"
            "         (SELECT COUNT(*) FROM links l WHERE l.parent = s.designation) AS dn,"
            "         (SELECT COUNT(*) FROM links l WHERE l.child  = s.designation) AS up"
            "  FROM snapshots s WHERE s.designation IS NOT NULL AND s.designation != ''"
            ") GROUP BY designation ORDER BY links DESC LIMIT ?", (int(top_n or 100),)).fetchall()
    finally:
        c.close()
    roots = {}
    top = []
    for des, path, cnt in rows:
        folder = path.replace("/", "\\").rsplit("\\", 1)[0] if path else ""
        root = folder.rsplit("\\", 1)[-1] if folder else ""
        r = roots.setdefault(root, {"name": root, "count": 0, "links": 0})
        r["count"] += 1
        r["links"] += cnt
        top.append({"name": des, "path": path, "root": root, "links": cnt})
    return {"roots": sorted(roots.values(), key=lambda r: r["links"], reverse=True)[:30],
            "top": top, "db": PRT._where_db()}


# ЖИВАЯ НАХОДКА 04.10.2026 (аудит dev\audit_tools.py): здесь стояло "fn": "build_map" —
# СТРОКОЙ, а tools_registry.execute() вызывает t["fn"](...) как функцию. Даже будь блок
# загружен, отказ был бы «'str' object is not callable» (в логе агента 04.10 10:30:20).
TOOLS = [
    {"name": "map", "desc": "Карта проекта: корни и топ моделей по связям (ПЛМ-READER)",
     "params": {"top": "сколько топовых моделей"}, "fn": build_map}
]
