# -*- coding: utf-8 -*-
"""plm_asm_parse.py — состав сборки (.asm) ИЗ СТРУКТУРЫ ФАЙЛА (V200: вынесен из engine.py).

Чистый парсер: работает с `bytes` файла, не читает базу. Зависит от `stem`/`NAME_B`
(creo_read) и, ЛЕНИВО, от `engine` (`is_drawing_file`, `_clean_model_name`).
"""
import re

from creo_read import stem, NAME_B   # noqa: F401


def _hash_like(n):
    """Внутренний идентификатор Creo (длинная hex-строка) — не имя модели."""
    return bool(n) and len(n) >= 28 and all(c in "0123456789ABCDEFabcdef" for c in n)


# --- СВЯЗИ ИЗ СТРУКТУРЫ ФАЙЛА (состав сборки / .asm-обработка) -------------------------------
# ГРАБЛЯ (эта сессия): раньше состав брался из `names(raw)` — regex по ВСЕМУ файлу, без привязки
# к сборке: имя компонента засчитывалось по простому ВХОЖДЕНИЮ байтов, поэтому «инструмент» и
# «оснастка» попадали в состав изделия, а `_Z`-заготовки терялись. Здесь — структурные каналы.
# 🔴 Главное: формула зависит от ВЕРСИИ Creo (замер STRATEGY §2.7 на 5 700 файлах):
#   Creo 4–13  → «компонент id N (ИМЯ.PRT)»   (2 641 ребро)
#   Creo 3.0 и старше → «d <длина> (имя.PRT)» (182 ребра)
#   ProE/Wildfire, unknown → «@comp_ids» + имена
#   НЕ работает на 937 файлах, если брать только первый канал → обязателен КАСКАД из трёх.
# Кодировка имён — UTF-8 (НЕ cp1251): кириллицу `ЦТКД_…` в latin-1 читает как `Ð¦Ð¢Ð\…`.
P_ASM_COMP = re.compile(rb"(?:\xd0\xba\xd0\xbe\xd0\xbc\xd0\xbf\xd0\xbe\xd0\xbd\xd0\xb5\xd0\xbd\xd1\x82"
                        rb"|\xd0\xba\xd0\xbe\xd0\xbc\xd0\xbf\xd0\xbe\xd0\xbd\xd0\xb5\xd0\xbd\xd1\x8b)"
                        rb" id (\d+) \(([^)]{1,64}\.(?:PRT|ASM|prt|asm))\)")
P_ASM_D = re.compile(rb"(?:^|[\r\n])\s*d (\d+) \(([A-Za-z0-9_\-\.]{2,64}\.(?:PRT|ASM|prt|asm))\)")
P_ASM_IDS = re.compile(rb"@comp_ids(.{0,4096}?)@", re.S)

# Служебные имена (шаблоны и внутренние сборки) — в состав изделия НЕ входят.
ASM_SERVICE = {"SBORKA_MFG", "SBORKA_MM", "MFG_NC", "MFG_NC_ASM", "INLBS_MFG_NC", "MM_PART",
               "MM_ASSY", "MM_ASM", "MOLD_ASM", "MFG_ASM", "MASTER_MFG_ASM"}


def asm_components(raw, own="", stems=None, path=""):
    """Состав сборки/обработки ИЗ СТРУКТУРЫ ФАЙЛА: [(имя, роль, сколько раз)] — НЕ по вхождению байтов.

    Каскад каналов (по версии Creo, см. комментарий выше): фраза «компонент id» → «d N (имя)» →
    `@comp_ids`. Имя приводится к стему; роль определяется БИНАРНЫМИ признаками («ИМЯ — ЭТО ЛОЖЬ»):
      инструмент — `T00xx`;  заготовка — `_Z`;  отливка — `_OTLIVKA`/`_LIT`;  своя деталь — совпала
      со стемом файла;  ОСНАСТКА — всё остальное (приспособление/оправка/центровка; проверено на
      44 деталях ЦТКД живой пробой, STRATEGY §2.6).
    `stems` — если задано, посторонние имена берём ТОЛЬКО из этого множества (имена склада),
    иначе в состав попадал бы мусор из служебных записей Creo.

    🔴 ГРАБЛЯ 28.10.2026 (стоп-лист эстафеты п.3): `asm_comp` пишется ЧЕРТЕЖАМ — 25 977 связей.
    Чертёж НЕ содержит компонентов: у него есть вид/виды с указателями на модели, и имя модели
    попадает в байты (`d N (ИМЯ.PRT)` встречается в записях видов). Проверка типа закрывает канал.
    `path` пуст (старые вызовы/пробники) → проверку не применяем, поведение прежнее.
    """
    import engine                                    # V200: ленивый импорт (без цикла)
    if path and engine.is_drawing_file(path):
        return []
    m = P_ASM_COMP.search(raw[:400])
    inter = (m.group(1) == b"/" or b"ASSEM_MFG" in raw[:400] or b"ASSEMBLY/CAST" in raw[:400]) \
        if m else (b"ASSEM_MFG" in raw[:400])
    seen, out = {}, []
    for rx in (P_ASM_COMP, P_ASM_D):
        for g in rx.findall(raw):
            nm = g[1].decode("utf-8", "replace") if isinstance(g[1], bytes) else g[1]
            nm = engine._clean_model_name(nm.encode("utf-8", "replace")) if not nm.isascii() else nm
            s = stem(nm)
            if not s or len(s) < 2 or s.upper() in ASM_SERVICE:
                continue
            seen[s] = seen.get(s, 0) + 1
    if not seen:                                     # запасной канал: ProE/Wildfire и «unknown»
        blk = P_ASM_IDS.search(raw)
        if blk:
            for b in NAME_B.finditer(blk.group(1)):
                s = stem(b.group(1).decode("latin-1"))
                if len(s) >= 3 and s.upper() not in ASM_SERVICE:
                    seen[s] = seen.get(s, 0) + 1
    up_own = (own or "").upper()
    for s in sorted(seen):
        up = s.upper()
        if re.match(r"^T\d{3,4}$", up):
            role = "инструмент"
        elif up.endswith("_Z") or up.endswith("-Z") or "_Z_" in up:
            role = "заготовка"
        elif "OTLIVKA" in up or "ОТЛИВКА" in up or up.endswith("_O"):
            role = "отливка"
        elif up_own and up_own in up:
            role = "деталь"
        elif inter:
            role = "оснастка"
        else:
            role = "деталь"
        out.append((s, role, seen[s]))
    return out


def _internal_id(n):
    """Внутренний идентификатор Creo (hex/base36, >=24 знаков) — НЕ имя модели.

    В `derived.base`/`child` попадают такие коды (напр. `848HJNI4L5H6O4AV25BMF289G2`):
    они ничего не значат для человека, поэтому в дереве помечаются, а не выдаются за изделие."""
    if not n:
        return False
    n = re.sub(r"^[^0-9A-Za-z]+|[^0-9A-Za-z]+$", "", str(n))   # мусорный первый байт Creo
    if len(n) < 24:
        return False
    return all(c.isdigit() or ("A" <= c.upper() <= "Z") for c in n)
