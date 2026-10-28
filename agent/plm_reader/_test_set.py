# -*- coding: utf-8 -*-
"""_test_set.py — СЕТ НА ПРОВЕРКУ PLM Reader (STRATEGY_PLM.md §2.5, GRABLI §106).

🔴 ЗАКОН ВЛАДЕЛЬЦА: «пробуй не на всей базе 40К, а на нескольких файлах!»

ЧТО ДЕЛАЕТ: берёт эталонные файлы сета (A: библиотека, D: живой комплект ЦТКД),
читает их ТЕМ ЖЕ путём, которым ходит скан (`engine.scan_item`), сверяет с ОЖИДАНИЯМИ.
Ожидания сняты фактом 28.10.2026 боевым каналом, а не «похожей» функцией
(грабля: мерили `creo_read.names` вместо `engine.asm_components` — GRABLI §106.0).

ЗАПИСЬ: на диск Z: НЕ ПИШЕТСЯ НИКОГДА. База не открывается. Только чтение файлов.

ЗАПУСК:
    python _test_set.py            — прогнать сет (код выхода 0 = сет зелёный)
    python _test_set.py --neg      — НЕГАТИВНЫЙ тест: ожидание роли перевёрнуто,
                                     сет ОБЯЗАН упасть (§99.3.3)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                           # noqa: BLE001
        pass

LIB = r"Z:\PTC\CREO-START\Libraries\Библиотека_стандартных_изделий\Болты_винты"
KIT = r"Z:\PTC\Work\001_15 ЦТКД Электон"

# ── ОЖИДАНИЯ СЕТА ───────────────────────────────────────────────────────────
#   role        — ожидаемая роль ('' = законно пустая)
#   min_parts   — минимум компонентов состава (engine.asm_components)
#   must_parts  — имена, которые ОБЯЗАНЫ быть в составе
#   forbidden   — имена, которых в составе быть НЕ ДОЛЖНО (шаблоны)
#   min_refs    — минимум refs (имена моделей склада внутри файла)
SET = [
    dict(tag="A1 din912 (библиотека)",
         path=os.path.join(LIB, "din912.prt.1"),
         role=None, min_parts=0, must_parts=(), forbidden=(), min_refs=0),
    dict(tag="D1 деталь (роль пустая законно)",
         path=os.path.join(KIT, r"ЦТКД 015.23.001 клемма32", "ctkd_015_23_001.prt.1"),
         role="", min_parts=0, must_parts=(), forbidden=(), min_refs=0),
    # D. Кириллица в ЗАГОТОВКЕ: роль строится из содержимого (UTF-8), не из имени файла
    dict(tag="D8 кириллица-заготовка",
         path=os.path.join(KIT, r"ЦТКД 437.001 Корпус", "цткд_437_001-psb-02-z.prt.1"),
         role="proizv.ЦТКД_437_001-PSB-02", min_parts=0, must_parts=(), forbidden=(), min_refs=0),
    dict(tag="D2 заготовка",
         path=os.path.join(KIT, r"ЦТКД 015.23.001 клемма32", "ctkd_015_23_001_zagotovka.prt.1"),
         role="proizv.CTKD_015_23_001", min_parts=0, must_parts=(), forbidden=(), min_refs=0),
    dict(tag="D3 обработка",
         path=os.path.join(KIT, r"ЦТКД 015.23.001 клемма32", "ctkd_015_23_001_mill_turn_z.prt.1"),
         role="proizv.CTKD_015_23_001_MILL_TURN", min_parts=0, must_parts=(), forbidden=(), min_refs=0),
    dict(tag="D4 приспособление",
         path=os.path.join(KIT, r"ЦТКД 015.23.001 клемма32", "ctkd_015_23_001-psb1.asm.1"),
         role="MFG", min_parts=0, must_parts=(), forbidden=(), min_refs=0),
    dict(tag="D5 обработка CAM",
         path=os.path.join(KIT, r"ЦТКД 015.23.001 клемма32", "ctkd_015_23_001_mill_turn.asm.1"),
         role="MFG", min_parts=0, must_parts=(), forbidden=(), min_refs=0),
    dict(tag="D6 кириллица, сборка 5 МБ",
         path=os.path.join(KIT, r"ЦТКД 437.001 Корпус", "цткд_437_001.asm.1"),
         role="MFG", min_parts=5,
         must_parts=("ЦТКД_437_001", "ЦТКД_437_001_Z"), forbidden=(), min_refs=0),
    dict(tag="D7 шаблоны НЕ в составе",
         path=os.path.join(KIT, r"ЦТКД 437.001 Корпус", "цткд_437_001-psb-02.asm.1"),
         role="MFG", min_parts=0, must_parts=(),
         forbidden=("SBORKA_MFG", "INLBS_MFG_NC", "MM_PART", "MFG_NC"), min_refs=0),
]


def _parts_names(eng, raw):
    """Имена состава ТАК, КАК ИХ БЕРЁТ СКАН: engine.asm_components."""
    out = []
    try:
        for item in eng.asm_components(raw):
            if isinstance(item, (tuple, list)) and item:
                out.append(str(item[0]).upper())
    except Exception:                           # noqa: BLE001
        pass
    return out


def run(negative=False):
    eng = _load()
    fails, checks = [], 0
    print("=" * 78)
    print("СЕТ НА ПРОВЕРКУ PLM Reader | путь замера: engine.scan_item (как скан)")
    print("запись: файлы сета только читаются; база не открывается; на Z: ничего не пишем")
    if negative:
        print("РЕЖИМ: НЕГАТИВНЫЙ — ожидание роли перевёрнуто, сет ОБЯЗАН упасть")
    print("=" * 78)
    for case in SET:
        p, tag = case["path"], case["tag"]
        if not os.path.isfile(p):
            fails.append("%s: НЕТ ФАЙЛА %s" % (tag, p))
            print("  ❌ %-32s НЕТ ФАЙЛА" % tag)
            continue
        name = eng.stem(os.path.basename(p))
        # СКАН подаёт ДВА набора имён (engine.py:2185): codes = ВСЕ модели склада,
        # fstems = модели ТОЙ ЖЕ ПАПКИ (для сверки шаблонных имён). Мерить иначе — ошибка замера.
        folder = os.path.dirname(p)
        try:
            folder_codes = frozenset(eng.stem(f) for f in os.listdir(folder)
                                     if os.path.isfile(os.path.join(folder, f)))
        except Exception:                       # noqa: BLE001
            folder_codes = frozenset([name])
        try:
            it = eng.scan_item(name, p, folder_codes, folder_codes, media_dir=None)
        except Exception as ex:                 # noqa: BLE001
            fails.append("%s: scan_item упал: %r" % (tag, ex))
            print("  ❌ %-32s scan_item упал: %r" % (tag, ex))
            continue
        raw = open(p, "rb").read()
        parts = _parts_names(eng, raw)
        role = it.get("role") or ""
        refs = it.get("refs") or {}
        local = []

        def chk(cond, what):
            nonlocal checks
            checks += 1
            if not cond:
                local.append(what)
                fails.append("%s: %s" % (tag, what))
            return cond

        if case["role"] is not None:
            exp = case["role"]
            if negative:                        # негатив: требуем НЕВЕРНУЮ роль
                exp = exp + "_НЕВЕРНО"
            chk(role == exp, "role: ждали %r, получили %r" % (exp, role))
        chk(len(parts) >= case["min_parts"],
            "состав: ждали >=%d, получили %d %s" % (case["min_parts"], len(parts), parts[:6]))
        for m in case["must_parts"]:
            chk(m.upper() in parts, "состав: НЕТ обязательного %s" % m)
        for f in case["forbidden"]:
            chk(f.upper() not in parts, "состав: ШАБЛОН попал в состав: %s" % f)
        chk(len(refs) >= case["min_refs"],
            "refs: ждали >=%d, получили %d" % (case["min_refs"], len(refs)))
        print("  %s %-32s role=%-34r состав=%d refs=%d"
              % ("❌" if local else "✅", tag, role, len(parts), len(refs)))
        if parts:
            print("       состав: %s" % ", ".join(parts[:8]))
    print("-" * 78)
    print("проверок: %d | провалов: %d" % (checks, len(fails)))
    if fails:
        print("ПРОВАЛЫ:")
        for f in fails:
            print("   ❌", f)
        print("СЕТ: КРАСНЫЙ")
        return 1
    print("СЕТ: ЗЕЛЁНЫЙ")
    return 0


def _load():
    import engine
    return engine


if __name__ == "__main__":
    sys.exit(run(negative=("--neg" in sys.argv)))
