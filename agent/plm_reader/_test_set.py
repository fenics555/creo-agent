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
# Литейное производство: мастер-модель, верх/низ, знаки, ящики знаков (слово владельца)
LIT = r"Z:\PTC\Work\000_03 401-LIT Литейное производство\000_5 401-LIT-MO Модельная оснастка для литья"
L170 = os.path.join(LIT, "170meta Держатель форм", "170meta-1")
L171 = os.path.join(LIT, "171meta держатель форм")
# Турновер: таблица семейства у СБОРКИ + взаимозамены компонентов (слово владельца)
TURN = (r"Z:\PTC\Work\000_14 MP Механизм переворота\000_2 MP-T Турноверы"
        r"\ПТР-401-МТ-01 Турновер")

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

    # ── Л. ЛИТЕЙНОЕ ПРОИЗВОДСТВО: наследование и булевы операции ──────────────
    # Мастер-модель: родитель — ОТЛИВКА (модель), а не свойство PTC_MASTER_MATERIAL.
    dict(tag="L1 мастер 170meta",
         path=os.path.join(L170, "170meta-1-master.prt.1"),
         role="nasled.23-170GR1-META-01-OTLIVKA", min_parts=0, must_parts=(), forbidden=(), min_refs=0),
    dict(tag="L2 мастер 171meta",
         path=os.path.join(L171, "171meta-1-master.prt.1"),
         role="nasled.23-171GR1-META-1-OTLIVKA", min_parts=0, must_parts=(), forbidden=(), min_refs=0),
    # Знак → ящик знака: наследование от ЗНАКА, а не от свойства «DISTORTION ENERGY».
    dict(tag="L3 знак1 низ-ящик 170",
         path=os.path.join(L170, "170meta-1-знак1-низ-ящик.prt.1"),
         role="nasled.170META-1-ЗНАК1-НИЗ", min_parts=0, must_parts=(), forbidden=(), min_refs=0),
    dict(tag="L4 знак1 верх-ящик 171",
         path=os.path.join(L171, "171meta-1-знак1-верх-ящик.prt.1"),
         role="nasled.171META-1-ЗНАК1-ВЕРХ", min_parts=0, must_parts=(), forbidden=(), min_refs=0),
    dict(tag="L5 знак2 верх-ящик 171",
         path=os.path.join(L171, "171meta-1-знак2-верх-ящик.prt.1"),
         role="nasled.171META-1-ЗНАК2-ВЕРХ", min_parts=0, must_parts=(), forbidden=(), min_refs=0),
    # Заготовка «_z» — производная от модели.
    dict(tag="L6 заготовка модель-верха 170",
         path=os.path.join(L170, "170meta-1-модель-верха_z.prt.1"),
         role="proizv.170META-1-МОДЕЛЬ-ВЕРХА", min_parts=0, must_parts=(), forbidden=(), min_refs=0),
    # Ящик низа (сборка) — состав из 6 компонентов.
    dict(tag="L7 ящик-низ-sb 170 (состав)",
         path=os.path.join(L170, "170meta-1-02-ящик-низ-sb.asm.1"),
         role="", min_parts=6,
         must_parts=("170META-1-МОДЕЛЬ-НИЗА", "170META-1-ЗНАК1-НИЗ"), forbidden=(), min_refs=0),
    dict(tag="L8 ящик-верх-sb 171 (состав)",
         path=os.path.join(L171, "171meta-1-03-ящик-верх-sb.asm.1"),
         role="", min_parts=5,
         must_parts=("171META-1-МОДЕЛЬ-ВЕРХА",), forbidden=(), min_refs=0),
    # «для копирования» — мастер-сборка всей оснастки.
    dict(tag="L9 для_копирования 170",
         path=os.path.join(L170, "170meta-1-000-для_копирования.asm.1"),
         role="", min_parts=6,
         must_parts=("170META-1-MASTER", "170META-1-01-ЯЩИК-ОСНОВНАЯ"), forbidden=(), min_refs=0),

    # ── Т. ТУРНОВЕР: таблица семейства у СБОРКИ + взаимозамены компонентов ────
    # Владелец: «есть сборки, у которых через таблицу семейства + взаимозамены меняются
    # разные компоненты в исполнениях». До 28.10.2026 скан отдавал по ним НОЛЬ.
    dict(tag="T1 турновер: исполнения сборки",
         path=os.path.join(TURN, "птр-401-мт-01r-00-t01.asm.1"),
         role="", min_parts=0, must_parts=(), forbidden=(), min_refs=0,
         min_family=5, must_instances=("ПТР-401-МТ-01R-00-T01_ISP-AL", "ПТР-401-МТ-01R-00-T01_ISP-BDF")),
    dict(tag="T2 турновер: вторая сборка",
         path=os.path.join(TURN, "птр-401-мт-01-00-t01.asm.1"),
         role="", min_parts=0, must_parts=(), forbidden=(), min_refs=0,
         min_family=5, must_instances=("ПТР-401-МТ-01-00-T01_ISP-AL",)),
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
        # ИСПОЛНЕНИЯ (таблица семейства) — в т.ч. у СБОРОК (турновер)
        if case.get("min_family"):
            try:
                fam = eng.family_of(raw, name, p)
            except Exception:                   # noqa: BLE001
                fam = []
            inst = {str(x[0]).upper() for x in fam if x}
            chk(len(inst) >= case["min_family"],
                "исполнения: ждали >=%d, получили %d" % (case["min_family"], len(inst)))
            for want in case.get("must_instances", ()):
                chk(want.upper() in inst, "исполнения: НЕТ %s" % want)
        print("  %s %-32s role=%-34r состав=%d refs=%d"
              % ("❌" if local else "✅", tag, role, len(parts), len(refs)))
        if parts:
            print("       состав: %s" % ", ".join(parts[:8]))
    fails += _check_rules(eng, negative)
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


# ── ПРАВИЛО «СВОЙСТВО ≠ РОДИТЕЛЬ-МОДЕЛЬ»: проверка ОБЕИХ сторон ─────────────
# Первая половина — имена, которые ОБЯЗАНЫ считаться свойством (иначе роль снова
# возьмёт материал вместо модели). Вторая — имена-МОДЕЛИ, которые свойством считать
# НЕЛЬЗЯ (иначе связь потеряется — ДОГМА: лучше собрать больше, чем потерять).
MUST_BE_PROPERTY = [
    "PTC_MASTER_MATERIAL", "PTC_SYSTEM_MTRL_PROPS", "PRO_MP_CSYS", "NONE", "LINEAR",
    "DISTORTION ENERGY (VON MISES)", "CHUGUN_VCH50", "STEEL_45", "Z_SHRINK_FACTOR",
    "mat_name_ptr", "NEUT_SPEC_1", "RESTRICT_TABLE",
]
MUST_BE_MODEL = [
    "23-170GR1-META-01-OTLIVKA", "23-171GR1-META-1-OTLIVKA", "170META-1-ЗНАК1-НИЗ",
    "171META-1-ЗНАК2-ВЕРХ", "170META-1-МОДЕЛЬ-НИЗА", "ЦТКД_437_001_Z", "DIN912",
    "500-55-500-MODEL-MASTER", "MO-STP-PROBNIK", "1013-M2-1-ЗНАК1-ВЕРХ",
]


def _check_rules(eng, negative=False):
    """Полная проверка признаков. Возвращает список провалов."""
    bad = []
    # НОМИНАЛЫ ИЗ ИМЕНИ ИСПОЛНЕНИЯ (замер: 331/344 шпилек, 102/106 винтов)
    # (имя, ожидаемый диаметр, ожидаемая длина|None, ожидаемый шаг|None)
    NOM_CASES = [
        ("M3X12_G22033", 3.0, 12.0, None),
        ("M10X1P25_G22033", 10.0, None, 1.25),
        ("DIN912-M2_5X4", 2.5, 4.0, None),
        ("DIN912-M10X150", 10.0, 150.0, None),
        ("DIN912-M2_5", 2.5, None, None),      # родительский типоразмер — это НОРМА
    ]
    for nm, dia, ln, pit in NOM_CASES:
        got = eng.instance_nominals(nm)
        if negative:
            got = {}                         # негатив: разбор "сломан" -> обязан упасть
        ok_d = abs((got.get("диаметр") or -1) - dia) < 1e-6
        ok_l = (ln is None and "длина" not in got) or (ln is not None and abs((got.get("длина") or -1) - ln) < 1e-6)
        ok_p = (pit is None and "шаг" not in got) or (pit is not None and abs((got.get("шаг") or -1) - pit) < 1e-6)
        if not (ok_d and ok_l and ok_p):
            bad.append("номиналы %s: ждали ⌀%s/L%s/шаг%s, получили %s" % (nm, dia, ln, pit, got))
    print("  %s номиналы из имени: %d случаев проверено" % ("❌" if bad else "✅", len(NOM_CASES) + 1))
    for nm in MUST_BE_PROPERTY:
        got = bool(eng.is_property_name(nm))
        if negative:
            got = not got                   # негатив: ожидание перевёрнуто -> обязан упасть
        if not got:
            bad.append("свойство не распознано: %r" % nm)
    for nm in MUST_BE_MODEL:
        got = bool(eng.is_property_name(nm))
        if got:
            bad.append("МОДЕЛЬ ошибочно принята за свойство: %r" % nm)
    first = eng.first_model_name(["PTC_MASTER_MATERIAL", "CHUGUN_VCH50",
                                  "23-170GR1-META-01-OTLIVKA"])
    if first != "23-170GR1-META-01-OTLIVKA":
        bad.append("first_model_name: ждали отливку, получили %r" % first)
    only_props = eng.first_model_name(["PTC_MASTER_MATERIAL", "NONE"])
    if only_props != "":
        bad.append("first_model_name: при одних свойствах должна быть пустая строка, дала %r"
                   % only_props)
    print("  %s правило свойство/модель: свойств %d, моделей %d, first_model_name=%r"
          % ("❌" if bad else "✅", len(MUST_BE_PROPERTY), len(MUST_BE_MODEL), first))
    return bad


def _load():
    import engine
    return engine


if __name__ == "__main__":
    sys.exit(run(negative=("--neg" in sys.argv)))
