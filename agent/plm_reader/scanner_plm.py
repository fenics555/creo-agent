# -*- coding: utf-8 -*-
r"""
scanner_new.py — НОВЫЙ СКАНЕР ПЛМ (прототип для замера)

ЦЕЛЬ: заменить 30–45 проходов по байтам на **1 чтение + 1 проход + ящики**.

СТРУКТУРА:
    READ      — файл читается ОДИН раз
    MAP       — ОДИН проход по байтам: сбор ВСЕХ якорей сразу
    EXTRACT   — из якорей достаются данные (каноны §167/§171/§173/§174)
    PACK      — раскладка по ЯЩИКАМ (= таблицам): явный список «что · откуда · куда»
    WRITE     — одна транзакция (позже; сейчас — сухой прогон)
    SCAN      — обход папок + сверка с базой (size/mtime)

КАНОНЫ (скиллы дома):
    §167 масса `e3 32 [тип] [7 байт]` · §171 типы `feat_defs_<N> − 910`
    §173 номинал `2F B1 B2` · §174 42 `PRO_MP_*` + пострегенерация
    §169 история `.drw` (`typed_data(MdlStored)`)
    Скилл темы: `repo\Creo\SKILL_creo_plmreader.md`

ЗАПУСК:
    python scanner_new.py            # замер на 30 файлах
    python scanner_new.py <папка>    # замер на своей папке
"""
import os
import re
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

# ═════════════════════════════════════════════════════════════════════════════
# СЛОВАРЬ ТИПОВ ЭЛЕМЕНТОВ Creo (pfcFeatureType) — 314 значений. §171
# ИСТОЧНИК: pfcFeature.h (Creo 13.4.1.0, otk_cpp\include) — снято 30.10.2026.
# Словарь ВПИСАН В КОД: в рантайме файлы Creo НЕ читаются (ПЕРЕНОСИМОСТЬ!).
# ФОРМУЛА: feat_defs_<N> − 910 = индекс в этом словаре.
FEATTYPE = {
    0: "FIRST", 1: "HOLE", 2: "SHAFT", 3: "ROUND", 4: "CHAMFER", 5: "SLOT", 6: "CUT",
    7: "PROTRUSION", 8: "NECK", 9: "FLANGE", 10: "RIB", 11: "EAR", 12: "DOME", 13: "DATUM_PLANE",
    14: "LOC_PUSH", 15: "UDF", 16: "DATUM_AXIS", 17: "DRAFT", 18: "SHELL", 19: "DOME2",
    20: "CORNER_CHAMFER", 21: "DATUM_POINT", 22: "IMPORT", 23: "COSMETIC", 24: "ETCH", 25: "MERGE",
    26: "MOLD", 27: "SAW", 28: "TURN", 29: "MILL", 30: "DRILL", 31: "OFFSET", 32: "DATUM_SURFACE",
    33: "REPLACE_SURFACE", 34: "GROOVE", 35: "PIPE", 36: "DATUM_QUILT", 37: "ASSEMBLY_CUT",
    38: "UDFTHREAD", 39: "CURVE", 40: "SURFACE_MODEL", 41: "WALL", 42: "BEND", 43: "UNBEND",
    44: "SHEETMETAL_CUT", 45: "FORM", 46: "THICKEN", 47: "BEND_BACK", 48: "UDFNOTCH",
    49: "UDFPUNCH", 50: "INTERNAL_UDF", 51: "SPLIT_SURFACE", 52: "GRAPH", 53: "SMMFGPUNCH",
    54: "SMMFGCUT", 55: "FLATTEN", 56: "SET", 57: "VDA", 58: "SMMFGFORM",
    59: "SHEETMETAL_PUNCH_POINT", 60: "LIP", 61: "MANUAL_MILL", 62: "MFGGATHER", 63: "MFGTRIM",
    64: "MFGUSE_VOLUME", 65: "CABLE_LOCATION", 66: "CABLE_SEGMENT", 67: "CABLE", 68: "COORD_SYS",
    69: "CHANNEL", 70: "AREA_NIBBLE", 71: "PATCH", 72: "PLY", 73: "CORE", 74: "EXTRACT",
    75: "MFGREFINE", 76: "SILHOUETTE_TRIM", 77: "SPLIT", 78: "EXTEND", 79: "SOLIDIFY",
    80: "INTERSECT", 81: "ATTACH", 82: "CROSS_SECTION", 83: "UDFZONE", 84: "UDFCLAMP",
    85: "DRILL_GROUP", 86: "ISEGMENT", 87: "CABLE_COSMETIC", 88: "SPOOL", 89: "COMPONENT",
    90: "MFGMERGE", 91: "FIXTURE_SETUP", 92: "FLAT_PAT", 93: "CONT_MAP", 94: "EXP_RATIO",
    95: "RIP", 96: "OPERATION", 97: "WORKCELL", 98: "CUT_MOTION", 99: "CUSTOMIZE",
    100: "DRV_TOOL_SKETCH", 101: "DRV_TOOL_EDGE", 102: "DRV_TOOL_CURVE", 103: "DRV_TOOL_SURF",
    104: "MATERIAL_REMOVAL", 105: "TORUS", 106: "PIPE_SET_START", 107: "PIPE_POINT_TO_POINT",
    108: "PIPE_EXTEND", 109: "PIPE_TRIM", 110: "PIPE_FOLLOW", 111: "PIPE_JOIN", 112: "AUXILIARY",
    113: "PIPE_LINE", 114: "LINE_STOCK", 115: "SOLID_PIPE", 116: "BULK_OBJECT", 117: "SHRINKAGE",
    118: "PIPE_JOINT", 119: "PIPE_BRANCH", 120: "DRV_TOOL_TWO_CNTR", 121: "SUB_HARNESS",
    122: "SHEETMETAL_OPTIMIZE", 123: "DECLARE", 124: "SHEETMETAL_POPULATE",
    125: "OPERATION_COMPONENT", 126: "MEASURE", 127: "DRAFT_LINE", 128: "REMOVE_SURFACES",
    129: "RIBBON_CABLE", 130: "ATTACH_VOLUME", 131: "BLD_OPERATION", 132: "UDFWORK_REGION",
    133: "SPINAL_BEND", 134: "TWIST", 135: "FREE_FORM", 136: "ZONE", 137: "WELDING_ROD",
    138: "WELD_FILLET", 139: "WELD_GROOVE", 140: "WELD_PLUG_SLOT", 141: "WELD_SPOT",
    142: "SHEETMETAL_SHEAR", 143: "RIBBON_PATH", 144: "RIBBON_EXTEND", 145: "ASSEMBLY_CUT_COPY",
    146: "DEFORM_AREA", 147: "RIBBON_SOLID", 148: "FLAT_RIBBON_SEGMENT", 149: "POSITION_FOLD",
    150: "SPRING_BACK", 151: "BEAM_SECTION", 152: "SHRINK_DIM", 153: "THREAD",
    154: "SHEETMETAL_CONVERSION", 155: "CMMMEASURE_STEP", 156: "CMMCONSTR", 157: "CMMVERIFY",
    158: "CAV_SCAN_SET", 159: "CAV_FIT", 160: "CAV_DEVIATION", 161: "SHEETMETAL_ZONE",
    162: "SHEETMETAL_CLAMP", 163: "PROCESS_STEP", 164: "EDGE_BEND", 165: "DRV_TOOL_PROFILE",
    166: "EXPLODE_LINE", 167: "GEOM_COPY", 168: "ANALYSIS", 169: "WATER_LINE", 170: "UDFRMDT",
    171: "VOL_SPLIT", 172: "WELD_EDGE_PREP", 173: "SMMFGOFFSET", 174: "SMMFGMATERIAL_REMOVE",
    175: "SMMFGCOSMETIC", 176: "SMMFGAPPROACH", 177: "SMMFGSLOT", 178: "SMMFGSHAPE",
    179: "IPMQUILT", 180: "USER", 181: "GROUP_HEAD", 182: "DRVD", 183: "SMT_CRN_REL",
    184: "SLDBEND", 185: "FLATQLT", 186: "DRV_TOOL_TURN", 187: "HULL_PLATE", 188: "HULL_HOLE",
    189: "HULL_CUTOUT", 190: "HULL_STIFFENER", 191: "HULL_BEAM", 192: "HULL_ENDCUT",
    193: "HULL_WLD_FLANGE", 194: "HULL_COLLAR", 195: "HULL_DRAW", 196: "HULL_BRACKET",
    197: "HULL_FOLDED_FLG", 198: "FR_SYS", 199: "HULL_COMPT", 200: "REFERENCE", 201: "SHELL_EXP",
    202: "FREEFORM", 203: "KERNEL", 204: "WELD_PROCESS", 205: "HULL_REP_TMP", 206: "INSULATION",
    207: "SLD_PIP_INSUL", 208: "SMT_EXTRACT", 209: "ASSY_MERGE", 210: "DS_OPTIMIZE",
    211: "COMP_INTERFACE", 212: "OLE", 213: "TERMINATOR", 214: "WELD_NOTCH",
    215: "ASSY_WELD_NOTCH", 216: "ROUTE_MANAGER", 217: "HULL_WELD_NOTCH", 218: "SMM_SLIT",
    219: "SMM_HOLE", 220: "SMM_NEST", 221: "SMM_GROOVE", 222: "SMM_ETCH", 223: "ROUTE_PATH",
    224: "HULL_SPLIT_BOUND", 225: "SUPERQUILT", 226: "MOLD_SLIDER", 227: "HULL_PAD",
    228: "ROUTE_SPOOL", 229: "GLOBAL_MODEL", 230: "HULL_MITRE", 231: "HULL_SLOTCUT",
    232: "PATTERN", 233: "PATTERN_HEAD", 234: "FLEX_MUTATOR", 235: "ANNOTATION",
    236: "GRANITE_REMOVE_SRFS", 237: "GRANITE_TAPER_EXTR", 238: "GRANITE_TOOL_COMP", 239: "STYLE",
    240: "GENERAL_MERGE", 241: "DAMPER", 242: "SPRING", 243: "AUTO_ROUND", 244: "DESIGNATED_AREA",
    245: "REMOVE_SURFACE", 246: "ARTWORK", 247: "WELD_COMBINE", 248: "CONTACT3D",
    249: "RS_GENERATOR", 250: "RS_TRJ_MOVE", 251: "PLASTIC_RIB", 252: "PM_BELT_CURVE", 253: "VPDD",
    254: "SUBDIVISION", 255: "FLEXMOVE", 256: "PM_BUSHING_LD", 257: "FLXATTACH", 258: "FLEXSUBST",
    259: "MOD_ROUND", 260: "CE_GEOM", 261: "ANALYT_GEOM", 262: "STAMPED_AREA", 263: "FLX_OGF",
    264: "CE_COMP", 265: "MFGPTM_MATREM", 266: "SPLIT_SRF_RGN", 267: "DERIVED_MEMBER",
    268: "ACCEPT_CRITERIA", 269: "MOLD_SHUTOFF_SRF", 270: "SMT_SKETCH_FORM", 271: "JOIN_WALLS",
    272: "FLX_SOLVER", 273: "CE_SKET", 274: "MOLD_SKIRT_EXT_FEAT", 275: "MOLD_SKIRT_FILL_FEAT",
    276: "MOD_CHAMFER", 277: "RCG_ROUND", 278: "RCG_CHAMFER", 279: "UNRCG_ROUND",
    280: "pfcFEAT_UNRCG_CHAMFER", 281: "pfcFEAT_ECAD_CU_AREAS", 282: "pfcFEAT_CUSTOM",
    283: "pfcFEAT_CUSTOM_GRANITE", 284: "pfcFEAT_PUNCH_QUILT", 285: "pfcFEAT_REFPART_CUTOUT",
    286: "pfcFEAT_PM_MOTOR", 287: "pfcFEAT_PRTSPLIT", 288: "pfcFEAT_ECAD_CUTS",
    289: "pfcFEAT_SMT_RECOGNITION", 290: "pfcFEAT_LATTICE", 291: "pfcFEAT_EDIT_BEND",
    292: "pfcFEAT_EDIT_BEND_RELIEF", 293: "pfcFEAT_EDIT_CORNER_RELIEF", 294: "pfcFEAT_MOLD_INSERT",
    295: "pfcFEAT_EDIT_CORNER_SEAM", 296: "pfcFEAT_SENSOR", 297: "pfcFEAT_PART_COMP",
    298: "pfcFEAT_PULL_WALL", 299: "pfcFEAT_HULL_BLOCK", 300: "pfcFEAT_HULL_BLOCK_DEF",
    301: "pfcFEAT_PM_BELT", 302: "pfcFEAT_MOVE_COMP", 303: "pfcFEAT_SPLIT_BODY",
    304: "pfcFEAT_NEWBODY", 305: "pfcFEAT_MERGEBODIES", 306: "pfcFEAT_INTERSECTBODIES",
    307: "pfcFEAT_SUBTRACTBODIES", 308: "pfcFEAT_SPLIT_OUT", 309: "pfcFEAT_REMOVEBODY",
    310: "pfcFEAT_BOOLEANBODIES", 311: "pfcFEAT_BODY_COPY", 312: "pfcFEAT_COMPOSITE", 313: "NIL"
}



# ═════════════════════════════════════════════════════════════════════════════
ANCHORS = (
    b"user_name", b"modif_time", b"rev_string", b"Proe_version", b"comment",
    b"feat_defs_", b"dim_type", b"chg_param_arr", b"param_restr_entry",
    b"PTC_MASTER_MATERIAL", b"PTC_MATERIAL_DESCRIPTION", b"PTC_MATERIAL_TYPE",
    b"symbol_key", b"reg_status", b"mdl_geom_rev", b"inactive_geom",
    b"MERGE_BASE_PART", b"from_mdl_name", b"to_mdl_name", b"model_names",
    b"PTC_UNITS_MASS", b"tool_params", b"OPERATION_NAME", b"MACHINING_TIME",
    b"num_parents", b"is_item_alive", b"rel_model_name",
    b"PRO_MP_MASS", b"PRO_MP_VOLUME", b"PRO_MP_AREA", b"PRO_MP_DENSITY",
)
# БАЙТОВЫЕ маркеры (не текст!) — отдельно: `\xe3\x32` = 2 байта 0xE3 0x32.
# ГРАБЛЯ: `b"e3\x32"` — это ТЕКСТ «e32» (3 символа), а НЕ байты! Нужны явные \x.
E32 = b"\xe3\x32"
# ЯКОРЯ — всё, что ищем ОДНИМ проходом (общий шаблон)
# ═════════════════════════════════════════════════════════════════════════════
ANCHORS = (
    b"user_name", b"modif_time", b"rev_string", b"Proe_version", b"comment",
    b"feat_defs_", b"dim_type", b"chg_param_arr", b"param_restr_entry",
    b"PTC_MASTER_MATERIAL", b"PTC_MATERIAL_DESCRIPTION", b"PTC_MATERIAL_TYPE",
    b"symbol_key", b"reg_status", b"mdl_geom_rev", b"inactive_geom",
    b"MERGE_BASE_PART", b"from_mdl_name", b"to_mdl_name", b"model_names",
    b"PTC_UNITS_MASS", b"tool_params", b"OPERATION_NAME", b"MACHINING_TIME",
    b"e3\x32", b"num_parents", b"is_item_alive", b"rel_model_name",
)
# ОДИН общий шаблон: альтернатива всех якорей (одна машина regex)
_ANCHOR_RX = re.compile(b"|".join(re.escape(a) for a in ANCHORS))


# ═════════════════════════════════════════════════════════════════════════════
# 1. READ — файл читается ОДИН раз
# ═════════════════════════════════════════════════════════════════════════════
# ═════════════════════════════════════════════════════════════════════════════
# 0. НАСТРОЙКИ СКАНЕРА (из settings/settings.json — НЕ хардкод!)
# ═════════════════════════════════════════════════════════════════════════════
_SETTINGS_CACHE = None


def settings():
    """Настройки из `settings/settings.json` (кэш в памяти)."""
    global _SETTINGS_CACHE
    if _SETTINGS_CACHE is None:
        _SETTINGS_CACHE = {}
        try:
            import json
            p = os.path.join(os.path.dirname(HERE), "settings", "settings.json")
            with open(p, encoding="utf-8") as f:
                _SETTINGS_CACHE = json.load(f)
        except Exception:                       # noqa: BLE001 — настройки не критичны
            _SETTINGS_CACHE = {}
    return _SETTINGS_CACHE


def cfg(key, default=None):
    """Значение настройки (или default)."""
    v = settings().get(key)
    return default if v in (None, "") else v


def model_of(path):
    """Имя модели из пути (без .prt.N/.asm.N/.drw.N/.mfg.N)."""
    f = os.path.basename(path)
    for ext in (".prt", ".asm", ".drw", ".mfg", ".frm", ".lay", ".sec"):
        i = f.lower().find(ext)
        if i > 0:
            return f[:i]
    return f.rsplit(".", 1)[0]


def read_file(path, max_mb=64, dump_dir=None, dump_limit=None):
    """
    ЧИТАТЬ ФАЙЛ В RAM (ход ① схемы §184).

    🎚️ РЫЧАГ ОТЛАДКИ (ВНУТРИ сканера!): `dump_raw_dir` из настроек —
       сохраняет СЫРЫЕ БАЙТЫ в файл (для тестов: «вдруг читает неправильно»).
       Если dump_dir не задан — берётся из настроек (`dump_raw_dir`).
    """
    if dump_dir is None:
        dump_dir = cfg("dump_raw_dir") or None
    if dump_limit is None:
        dump_limit = cfg("dump_raw_limit")
    try:
        if os.path.getsize(path) > max_mb * 1024 * 1024:
            return None
    except OSError:
        return None
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError:
        return None
    # 🎚️ РЫЧАГ ОТЛАДКИ: дамп байтов (только для тестов!)
    if dump_dir:
        try:
            os.makedirs(dump_dir, exist_ok=True)
            n = len([x for x in os.listdir(dump_dir) if x.endswith(".bin")])
            if dump_limit is None or n < int(dump_limit):
                safe = os.path.basename(path).replace("\\", "_")
                with open(os.path.join(dump_dir, safe + ".bin"), "wb") as f:
                    f.write(raw)
        except (OSError, ValueError, TypeError):
            pass
    return raw


# ═════════════════════════════════════════════════════════════════════════════
# 0б. ПРОПУСК НЕИЗМЕНИВШИХСЯ (по умолчанию!) — §184
# ═════════════════════════════════════════════════════════════════════════════
def is_changed(path, known):
    """
    Изменился ли файл? `known` = {path: (size, mtime)} из базы.

    ПО УМОЛЧАНИЮ: неизменившиеся НЕ читаем (быстро!).
    ОБРАТНАЯ НАСТРОЙКА: `full = true` («перечитать всё») — игнорировать кэш.
    """
    if cfg("full", False):
        return True                              # «перечитать всё»
    if not known:
        return True
    rec = known.get(path)
    if not rec:
        return True
    try:
        st = os.stat(path)
    except OSError:
        return True
    return not (int(rec[0]) == st.st_size and abs(float(rec[1]) - st.st_mtime) < 1.0)


# ═════════════════════════════════════════════════════════════════════════════
# 2. MAP — ОДИН проход: {якорь: [позиции]}
# ═════════════════════════════════════════════════════════════════════════════
# ═════════════════════════════════════════════════════════════════════════════
# 2б. КАРТА ФАЙЛА `#UGC_TOC` — ЗАКОН: СНАЧАЛА КАРТА, ПОТОМ ВГЛУБЬ (§178)
# ═════════════════════════════════════════════════════════════════════════════
_RE_TOC_LINE = re.compile(
    rb"^([A-Za-z_][A-Za-z_0-9:]*?)\s+([0-9a-f]{2,8})\s+([0-9a-f]{2,8})\s+([0-9a-f]{2,8})\s",
    re.M)


def read_toc(raw):
    """
    КАРТА файла: {СЕКЦИЯ: (смещение, длина)} — из `#UGC_TOC`.

    Формат строки: `ИМЯ_СЕКЦИИ  СМЕЩЕНИЕ  ДЛИНА  ...`
    Смещение — ОТ НАЧАЛА ФАЙЛА (проверено: `Model_L05_PX @0xAB6`, `NeuPrtSld @0xA87BE`).
    В файле 2–3 карты; читаем ВСЕ и объединяем (ключи уникальны по имени).
    """
    out = {}
    for tm in re.finditer(rb"#UGC_TOC", raw):
        end = raw.find(b"#" + b"#" * 5, tm.end())
        seg = raw[tm.end():tm.end() + 6000]
        for m in _RE_TOC_LINE.finditer(seg):
            name = m.group(1).decode("utf-8", "replace")
            try:
                off = int(m.group(2), 16)
                ln = int(m.group(3), 16)
            except ValueError:
                continue
            if off > len(raw):
                continue
            out.setdefault(name, (off, ln))
    return out


def toc_section(raw, toc, name, pad=0):
    """Байты секции `name` по КАРТЕ (если есть), иначе — пусто. §178."""
    if name in toc:
        off, ln = toc[name]
        return raw[off:off + ln + pad]
    return b""


def map_anchors(raw):
    """ОДИН проход по байтам → {якорь: [позиции]}. Включает байтовый маркер E32."""
    found = {}
    for m in _ANCHOR_RX.finditer(raw):
        found.setdefault(m.group(0), []).append(m.start())
    # байтовый маркер `e3 32` — ищем в ТОМ ЖЕ проходе (отдельный скан, но один цикл)
    e32 = []
    pos = raw.find(E32)
    while pos >= 0:
        e32.append(pos)
        pos = raw.find(E32, pos + 2)
    if e32:
        found[E32] = e32
    return found


# ═════════════════════════════════════════════════════════════════════════════
# 3. EXTRACT — из якорей достаются данные (каноны §167/§171/§173/§174)
# ═════════════════════════════════════════════════════════════════════════════
_STR = re.compile(rb"[\x20-\x7e\xc0-\xff]{1,90}")


def _str_at(raw, pos, after=b"\x00"):
    """
    Строка сразу ПОСЛЕ якоря.
    ЗАМЕР 30.10.2026: разделитель бывает `\x00`, но у некоторых полей — `\xf1`
    (напр. `from_mdl_name\\x00 \\xf1 <ЗНАЧЕНИЕ>\\x00`). Ищем БЛИЖАЙШИЙ разделитель.
    """
    s = raw.find(after, pos)
    if s < 0:
        return ""
    s += len(after)
    # если сразу после `\x00` стоит `\xf1` (или иной маркер) — пропускаем его
    while s < len(raw) and raw[s] in (0xF1, 0xE1, 0xE2, 0xE0, 0x00):
        s += 1
    m = _STR.match(raw, s)
    return m.group(0).decode("utf-8", "replace") if m else ""


def _dbl_from_2f(b1, b2):
    """`2F B1 B2` → double `40 B1 B2 00 00 00 00 00`. §173."""
    lead = 0x40 if b1 >= 0x40 else 0x3F
    try:
        return struct.unpack(">d", bytes([lead, b1, b2, 0, 0, 0, 0, 0]))[0]
    except struct.error:
        return None


def _dbl_from_e32(body7):
    """`e3 32 [тип]` + 7 байт → double (перебор lead). §167."""
    for lead in (0x40, 0x41, 0x3F, 0x42):
        try:
            v = struct.unpack(">d", bytes([lead]) + body7)[0]
        except struct.error:
            continue
        if 1e-9 < abs(v) < 1e12:
            return v
    return None


# ── 3.1. ПАСПОРТ + ИСТОРИЯ (§169: typed_data(MdlStored)) ─────────────────────
def extract_passport(raw, anchors):
    out = {"user": "", "computer": "", "rev": "", "creo": "", "ts": "",
           "designation": "", "material": "", "kind": ""}
    m = re.match(rb"#UGC:2\s+(\w+)", raw)
    if m:
        out["kind"] = m.group(1).decode()
    for pos in anchors.get(b"user_name", [])[:3]:
        v = _str_at(raw, pos)
        if v and not out["user"]:
            out["user"] = v
    for pos in anchors.get(b"rev_string", []):
        v = _str_at(raw, pos)
        if v:
            out["rev"] = v
            break
    for pos in anchors.get(b"Proe_version", []):
        v = _str_at(raw, pos)
        if v:
            out["creo"] = v
            break
    for pos in anchors.get(b"comment", []):
        v = _str_at(raw, pos)
        if "компьютер" in v.lower() or "computer" in v.lower():
            out["computer"] = v.split("'")[1] if "'" in v else v
            break
    # ⚠️ §176: `PTC_MASTER_MATERIAL` — это ЕДИНИЦЫ (`65G_MMKGS`), НЕ материал!
    # Материал Creo 7.0+: фактический (имя — в библиотеке Creo, в файле только ссылка)
    # + внутренний `PTC_SYSTEM_MTRL_PROPS` (плотность-пустышка) — ФИЛЬТРОВАТЬ.
    out["system_mtrl"] = raw.count(b"PTC_SYSTEM_MTRL_PROPS") > 0
    m = re.search(rb"PTC_MATERIAL_TYPE\x00\xe2[34][^\x00]*\x00([\x20-\x7e]{1,40})\x00", raw)
    if m:
        out["mtype"] = m.group(1).decode("utf-8", "replace")
    for pos in anchors.get(b"modif_time", []):
        seg = raw[pos:pos + 200]
        mm = re.search(rb"tm_sec\x00(.)\xe0\x01tm_min\x00(.)\xe0\x01tm_hour\x00(.)"
                       rb"\xe0\x01tm_mday\x00(.)\xe0\x01tm_mon\x00(.)\xe0\x01tm_year\x00(.)",
                       seg, re.S)
        if mm:
            s, mi, h, d, mo, y = (x[0] for x in mm.groups())
            out["ts"] = "%04d-%02d-%02dT%02d:%02d:%02d" % (y + 1900, mo + 1, d, h, mi, s)
            break
    return out


# ── 3.2. МАССА / ОБЪЁМ / ПЛОТНОСТЬ (§167) ────────────────────────────────────
def _mp_field(seg, name, lo, hi):
    """
    Значение поля из секции `mass_prop` — ФОРМУЛА §175 (доказана на живых файлах):
        <имя>\\x00 [байт-тип] <7 байт>   →   double = lead + 7 байт
        lead ∈ {0x40, 0x3E, 0x3F, 0x41, 0x3D} — берём попадающее в [lo, hi].
    Проверено: volume 0x40 → 71302.3 мм³ · surfarea 0x40 → 13515.8 мм² · density 0x3E → 7.85e-06 кг/мм³.
    """
    m = re.search(rb"\xe0\x02" + name + rb"\x00", seg)
    if not m:
        return None
    s = m.end()
    body = seg[s + 1:s + 8]
    if len(body) < 7:
        return None
    # 🔴 ЗАКОН «в файлах мусора НЕТ»: собираем ВСЕ варианты `lead`,
    #    а не «первый разумный». «Разумные» (по диапазону) — ВПЕРЁД, но не отбрасываем.
    cands = []
    for lead in (0x40, 0x3E, 0x3F, 0x41, 0x3D, 0x42, 0x3C):
        try:
            cands.append(struct.unpack(">d", bytes([lead]) + body)[0])
        except struct.error:
            pass
    good = [v for v in cands if lo <= abs(v) <= hi]
    return (good or cands or [None])[0]


def extract_mass(raw, anchors):
    """
    МАССА/ОБЪЁМ/ПЛОЩАДЬ/ПЛОТНОСТЬ — из секции `mass_prop` (НЕ из PRO_MP_MASS!).

    ФАКТ (замер 30.10.2026): `PRO_MP_MASS` — «схемное» значение, НЕ совпадает с реальным.
    Реальные свойства — в `mass_prop_data → p_mp_report_data → mass_prop`:
        volume · surfarea · density · cg · inertia
    МАССА НЕ ХРАНИТСЯ — она ВЫЧИСЛЯЕТСЯ: mass = volume × density.
    Файлы без `mass_prop` (заготовки `-z`) — ЗАКОННО без свойств.
    """
    mp = raw.find(b"mass_prop_data")
    if mp < 0:
        return {}
    seg = raw[mp:mp + 1500]
    vol = _mp_field(seg, b"volume", 1.0, 1e8)
    area = _mp_field(seg, b"surfarea", 1.0, 1e8)
    rho = _mp_field(seg, b"density", 1e-9, 0.1)          # кг/мм³
    out = {}
    if vol is not None:
        out["VOLUME"] = vol
    if area is not None:
        out["AREA"] = area
    if rho is not None:
        out["DENSITY"] = rho * 1e3                       # г/см³ (для карточки)
    if vol is not None and rho is not None:
        out["MASS"] = vol * rho                          # кг
    return out


# ── 3.3. ТИПЫ ЭЛЕМЕНТОВ (§171) ───────────────────────────────────────────────
_RX_DEFS_NUM = re.compile(rb"(\d+)")


def extract_features(raw, anchors, feat_dict):
    out = []
    for seq, pos in enumerate(anchors.get(b"feat_defs_", [])):
        m = _RX_DEFS_NUM.match(raw, pos + 10)
        if not m:
            continue
        n = int(m.group(1))
        seg = raw[m.end():m.end() + 140]
        mi = re.search(rb"id\x00(.)", seg)
        out.append({"defs": n, "typenum": n - 910,
                    "typename": feat_dict.get(n - 910, "?"),
                    "feat_id": mi.group(1)[0] if mi else None, "seq": seq})
    return out


# ── 3.4. РАЗМЕРЫ (§173) ──────────────────────────────────────────────────────
def extract_dimensions(raw, anchors):
    """
    Размеры — СОБИРАЕМ ВСЁ (закон владельца: «в файлах мусора НЕТ»).

    Не отбрасываем: если `feat_id` нет — запись ВСЁ РАВНО пишем (`feat_id=None`).
    Номинал: ВСЕ значения `2F B1 B2` в записи (а не первое «разумное») → список `nominals`.
    """
    out = []
    for pos in anchors.get(b"dim_type", []):
        seg = raw[pos:pos + 400]
        mf = re.search(rb"feat_id\x00(.)", seg)
        # ВСЕ номиналы (без фильтра «разумности»)
        noms = []
        for mm in re.finditer(rb"\x2f(.)(.)", seg):
            v = _dbl_from_2f(mm.group(1)[0], mm.group(2)[0])
            if v is not None:
                noms.append(round(v, 9))
        mc = re.search(rb"tol_class\x00(.)", seg)
        mt = re.search(rb"tol_type\x00(.)", seg)
        mb = re.search(rb"bound\x00(.)", seg)
        out.append({
            "feat_id": mf.group(1)[0] if mf else None,
            "nominal": noms[0] if noms else None,     # первый — как «основной»
            "nominals_all": noms,                     # ★ ВСЕ (ничего не потеряно)
            "tol_class": mc.group(1)[0] if mc else None,
            "tol_type": mt.group(1)[0] if mt else None,
            "bound": mb.group(1)[0] if mb else None,
        })
    return out


# ── 3.5. УРАВНЕНИЯ: ДВА МЕСТА (§174) ─────────────────────────────────────────
def extract_equations(raw, anchors):
    out = []
    for pos in anchors.get(b"chg_param_arr", []):
        seg = raw[pos:pos + 3000]
        for nm in re.finditer(rb"(PRO_MP_[A-Z_0-9]+)\x00", seg):
            out.append({"kind": "postregen", "name": nm.group(1).decode()})
            break
    for _ in anchors.get(b"param_restr_entry", []):
        out.append({"kind": "relation", "name": "param_restr_entry"})
    return out


_RX_REGSTAT = re.compile(rb"reg_status\x00(.)")


# ── 3.6. ЗДОРОВЬЕ (без Creo) ─────────────────────────────────────────────────
def extract_health(raw, anchors):
    out = {"regen": "", "reg_status": "", "inactive": 0}
    for pos in anchors.get(b"reg_status", []):
        m = _RX_REGSTAT.match(raw, pos)
        if m:
            b = m.group(1)[0]
            out["reg_status"] = str(b)
            out["regen"] = "ok" if b == 0 else "требует регенерации"
            break
    out["inactive"] = len(anchors.get(b"inactive_geom", []))
    return out


# ── 3.7. СВЯЗИ (наследование/копия/модель чертежа) ───────────────────────────
_RX_MODEL_REF = re.compile(rb"([A-Z0-9][A-Z0-9_\-\.]{3,40}\.(?:PRT|ASM))")


def extract_links(raw, anchors):
    """Связи: derived · copy_from · model_names · components (состав сборки).

    ⚡ ОПТИМИЗАЦИЯ: имена моделей ищем ТОЛЬКО в .asm/.drw (в .prt их нет).
    """
    out = {"derived": [], "copy_from": "", "model_names": [], "components": []}
    for pos in anchors.get(b"MERGE_BASE_PART", []):
        v = _str_at(raw, pos + 15)
        if v:
            out["derived"].append(v)
    for pos in anchors.get(b"from_mdl_name", []):
        v = _str_at(raw, pos)
        if v:
            out["copy_from"] = v
            break
    for pos in anchors.get(b"model_names", []):
        v = _str_at(raw, pos)
        if v:
            out["model_names"].append(v)
    # состав — только если это сборка/чертёж (быстрая проверка)
    head = raw[:200]
    if b"ASSEMBLY" in head or b"DRAWING" in head:
        comp = {}
        for mm in _RX_MODEL_REF.finditer(raw):
            nm = mm.group(1).decode("utf-8", "replace")
            comp[nm] = comp.get(nm, 0) + 1
        out["components"] = [{"name": n, "count": c} for n, c in
                             sorted(comp.items(), key=lambda x: -x[1])]
    return out



# ── 3.8. ПАРАМЕТРЫ (ВСЕ! Ничего не «отсеивать») ─────────────────────────────
# 🔴 ЗАКОН ВЛАДЕЛЬЦА (30.10.2026): «"НЕИЗВЕСТНОЕ" ≠ "МУСОР"».
# Раньше здесь был фильтр `_INTERNAL` (отбрасывал PRO_MP_*, PTC_UNITS, …) — УБРАН.
# Найдено непонятное → ЗАПИСАТЬ (в `unknown_fields`), а не выбрасывать.
_RE_PARAM = re.compile(rb"\xe0\x01([\x20-\x7e\xc0-\xff]{2,40})\x00")
_RE_PTC_NAME = re.compile(rb"([A-Z][A-Z_0-9]{3,40})\x00")


def extract_params(raw, anchors):
    """
    [(имя, значение)] — ВСЕ параметры, БЕЗ отсева.

    Возвращает: [(name, value)] — включая внутренние (`PRO_MP_*`, `PTC_*`) — они ЦЕННЫ.
    """
    out = []
    for m in _RE_PARAM.finditer(raw):
        nm = m.group(1).decode("utf-8", "replace")
        v = _str_at(raw, m.end() - 1)
        out.append((nm, v))            # ★ ВСЕ вхождения (повторы НЕ теряем!)
    return out


def extract_unknown_fields(raw, anchors):
    """«НЕ ИЗУЧЕНО» — ВСЕ ИМЕНА ПОЛЕЙ (закон: «в файлах мусора НЕТ»).

    ⚡ ОПТИМИЗАЦИЯ: быстрый find `\xe0` (маркер поля), имя проверяем локально.
    """
    out = {}
    pos = raw.find(b"\xe0")
    while pos >= 0:
        if pos + 2 < len(raw) and raw[pos + 1] in (0, 1, 2, 10):
            k = pos + 2
            start = k
            while k < len(raw) and (65 <= raw[k] <= 90 or 97 <= raw[k] <= 122 or raw[k] == 95):
                k += 1
            if k > start and k < len(raw) and raw[k] == 0 and 2 <= (k - start) <= 60:
                nm = raw[start:k].decode("ascii", "replace")
                out[nm] = out.get(nm, 0) + 1
        pos = raw.find(b"\xe0", pos + 1)
    return out



# ── 3.9. ПРЕВЬЮ (картинка) ───────────────────────────────────────────────────
# ── 3.14. ЧЕРТЁЖ (.drw) — модель-источник, лист, состояния (§168/§181) ───────
_RX_DRW_MODEL = re.compile(rb"([A-Z0-9][A-Z0-9_\-\.]{3,40}\.PRT)\x00")


def extract_drawing(raw, anchors):
    """
    [{source_model, sheet_size, states, uniq_name}] — данные чертежа `.drw`.

    ФАКТ (замер): связь с моделью — ИМЯ `.PRT` в файле (`CTKD-KALIBR-25X1X9G.PRT`).
    Поля: `uniq_name` · `time_stamp` · `names_table` · `size` · `active_size` ·
    `backup_size` · `state_name`.
    """
    out = {"source_models": [], "uniq_name": "", "sheet_size": None, "states": []}
    # ⚡ ОПТИМИЗАЦИЯ: только для чертежа (быстрая проверка заголовка)
    if b"DRAWING" not in raw[:200]:
        return out
    seen = []
    for m in _RX_DRW_MODEL.finditer(raw):
        nm = m.group(1).decode("utf-8", "replace")
        if nm not in seen:
            seen.append(nm)
    out["source_models"] = seen
    m = re.search(rb"uniq_name\x00([\x20-\x7e]{1,60})\x00", raw)
    if m:
        out["uniq_name"] = m.group(1).decode("utf-8", "replace")
    m = re.search(rb"active_size\x00([\x20-\x7e]{1,40})\x00", raw)
    if m:
        out["sheet_size"] = m.group(1).decode("utf-8", "replace")
    st = []
    for m in re.finditer(rb"state_name\x00([\x20-\x7e]{1,40})\x00", raw):
        v = m.group(1).decode("utf-8", "replace")
        if v not in st:
            st.append(v)
    out["states"] = st
    return out


def extract_media(raw, anchors):
    """Позиции картинок (PNG/JPEG) — для сохранения превью."""
    out = []
    for sig in (b"\x89PNG", b"\xff\xd8\xff"):
        pos = 0
        while True:
            i = raw.find(sig, pos)
            if i < 0:
                break
            out.append(i)
            pos = i + 4
            if len(out) > 5:
                break
    return out




# ── 3.9б. ДЛИНА `f8 <N>` (ГРАБЛЯ R4: бывает МНОГОБАЙТНОЙ!) ───────────────────
def f8_len(raw, pos):
    """
    Прочитать счётчик массива после `f8`.

    ЗАМЕР 30.10.2026: `f8 01` → 1 · **`f8 80 90` → 144** · `f8 80 91` → 145.
    Формат: `f8` + [если байт ≥ 0x80 → ФЛАГ, счётчик = СЛЕДУЮЩИЙ байт] + счётчик.
    Возвращает (значение, смещение_после_счётчика) или (None, pos).
    """
    i = pos + 1                                  # `f8` = 1 БАЙТ (0xF8), счётчик сразу после
    if i >= len(raw):
        return None, pos
    b0 = raw[i]
    if b0 >= 0x80:                               # флаг многобайтности
        if i + 1 >= len(raw):
            return None, pos
        return raw[i + 1], i + 2
    return b0, i + 1


# ── 3.10. ТЕЛА (§177) — у КАЖДОГО тела свои mass_prop ────────────────────────
def extract_bodies(raw, anchors):
    """
    [{body_id, order_num, feat_id, volume, density, surfarea, mass}]
    ВАЖНО (§177): `mass_prop` живёт ВНУТРИ тела (`gen_mass_prop_data`),
    у КАЖДОГО тела СВОИ свойства. Масса детали = СУММА по телам.
    """
    out = []
    # ВАЖНО: `gen_mass_prop_data` встречается 2× на тело (первое — БЕЗ данных, второе — с ними).
    # ⇒ группируем по индексу тела: i//2, берём запись С ДАННЫМИ (volume/density не пусты).
    seen = {}
    for i, m in enumerate(re.finditer(rb"gen_mass_prop_data", raw)):
        seg = raw[m.start():m.start() + 1600]
        vol = _mp_field(seg, b"volume", 1.0, 1e8)
        area = _mp_field(seg, b"surfarea", 1.0, 1e8)
        rho = _mp_field(seg, b"density", 1e-9, 0.1)
        # body_id — ищем НАЗАД (у ПЕРВОГО тела может отсутствовать → 0)
        back = raw[max(0, m.start() - 900):m.start()]
        mb = None
        for bm in re.finditer(rb"body_id\x00(.)", back):
            mb = bm.group(1)[0]
        if mb is None:
            mb = 0
        mo = re.search(rb"order_num\x00(.)", back)
        key = (mb, i // 2)                     # группировка «пара записей на тело»
        rec = {"seq": len(seen), "body_id": mb,
               "order_num": mo.group(1)[0] if mo else None,
               "volume": vol, "density": rho * 1e3 if rho else None,
               "surfarea": area, "mass": (vol * rho) if (vol and rho) else None}
        old = seen.get(key)
        # берём запись С ДАННЫМИ (если у старой пусто) — НО если данных больше, сохраняем обе
        if old is None or (rec["volume"] and not old["volume"]):
            seen[key] = rec
        else:
            rec["seq"] = len(seen)
            seen[(mb, i)] = rec
    return list(seen.values())


# ── 3.11. МАТЕРИАЛЫ (§176/§177) ──────────────────────────────────────────────
_SYSTEM_MTRL = b"PTC_SYSTEM_MTRL_PROPS"
_RE_MTRL_ENTRY = re.compile(rb"\xe0\nname\x00([\x20-\x7e]{3,60})\x00\xe0\x01id\x00(.)")


def extract_materials(raw, anchors):
    """
    [{name, mat_id, mtype, mass_density, system}]
    §176: `PTC_SYSTEM_MTRL_PROPS` — ВНУТРЕННИЙ материал Creo 7.0+ (плотность-пустышка).
    §177: материалов может быть МНОГО (`material_arr f8 <N>`); мастер — один (см. `extract_master`).
    """
    out = []
    for m in _RE_MTRL_ENTRY.finditer(raw):
        name = m.group(1).decode("utf-8", "replace")
        seg = raw[m.start():m.start() + 1200]
        # MASS_DENSITY: ТРИ формата в файле (замер 30.10.2026):
        #   #1 `\x00 e1 f0 f7 60 23 e0 76 …`   #2 `\x00 e1 23 e0 76 …`   #3 `\x00 54 eb 02 9d 88 00 e3 32 23 e0 76 …`
        # Значение ВСЕГДА начинается с `23 e0 76 6f c8 e5 b7 7f` → lead 0x3E → 7.85e-06.
        # ⇒ Ищем ПО МАРКЕРУ ЗНАЧЕНИЯ (`23` + 7 байт), а не по конкретному префиксу.
        md = None
        for dm in re.finditer(rb"MASS_DENSITY\x00(.{0,30}?)\x23(.{7})", seg, re.S):
            body = dm.group(2)
            v = struct.unpack(">d", bytes([0x3E]) + body)[0]
            if 1e-12 <= abs(v) <= 1e3:


# ── 3.13. МАТРИЦЫ И ГАБАРИТЫ (§181) ─────────────────────────────────────────


# ═════════════════════════════════════════════════════════════════════════════
# 4. PACK — раскладка по ЯЩИКАМ (= таблицам базы)
                md = v
                break
        # запасной путь: `_mp_field` (формат `\xe0\x02<имя>`)
        if md is None:
            md = _mp_field(seg, b"MASS_DENSITY", 1e-12, 1e3)
        out.append({
            "name": name,
            "mat_id": m.group(2)[0],
            "mass_density": md,
            "system": name == "PTC_SYSTEM_MTRL_PROPS",
        })
    return out


def extract_master(raw, anchors):
    """
    Мастер-материал детали (§177) — ОДИН на всю деталь («задать как мастер»).

    ФАКТ: `PTC_ASSIGNED_MATERIAL` = ССЫЛКА на `PTC_MASTER_MATERIAL`
    (в файле текст `"PTC_MASTER_MATERIAL"`), а сам `PTC_MASTER_MATERIAL` = ЕДИНИЦЫ (`65G_MMKGS`).
    ⇒ ИМЯ фактического материала в файле ОТСУТСТВУЕТ (живёт в библиотеке материалов Creo).
    Что читается: ссылка + единицы + признак назначенного материала.
    """
    out = {"master_name": "", "reported_name": "", "has_master": False,
           "materials": []}
    # 🔴 ЗАМЕР 30.10.2026 (секция `MdlStatus`): материалы лежат МАССИВОМ с карточками:
    #    `materials  f8 <N>` → [ name · description · properties f8 <K> (type·value·unit) ]
    #    `current_material  f4 04 <ИМЯ>` — МАСТЕР (один на деталь).
    # ФОРМАТ (замер): `materials\x00 f8 <N> f7 .. fb e3 e0\nname\x00 <ИМЯ>\x00
    #                 e0\ndescription\x00 <ОПИС>\x00 e0\x00properties\x00 f8 <K> ...`
    # ВНИМАНИЕ: имена полей через `\xe0\n` (0x0A), а НЕ `\xe0\x01`!
    for mm in re.finditer(rb"materials\x00\xf8(.)\xf7", raw, re.S):
        n_mat = mm.group(1)[0]
        seg = raw[mm.start():mm.start() + 6000]
        # ⚠️ ГРАБЛЯ 1: НЕ использовать `re.S` — DOTALL ломает `\xe0\x0a`.
        # ⚠️ ГРАБЛЯ 2: класс `[\x20-\x7e\xc0-\xff]` НЕ ловит кириллицу `\xd0\x93` («Г»)
        #    — байт `\x93` < 0xC0! Правильный класс: `[\x20-\x7e\x80-\xff]` (весь UTF-8).
        for entry in re.finditer(rb"\xe0\x0aname\x00([\x20-\x7e\x80-\xff]{2,50})\x00"
                                 rb"\xe0\x0adescription\x00([\x20-\x7e\x80-\xff]{0,50})\x00"
                                 rb"\xe0\x00properties\x00\xf8(.)", seg):
            nm = entry.group(1).decode("utf-8", "replace")
            de = entry.group(2).decode("utf-8", "replace")
            n_props = entry.group(3)[0]
            if nm not in [x["name"] for x in out["materials"]]:
                out["materials"].append({"name": nm, "description": de,
                                         "n_props": n_props})
    m = re.search(rb"current_material\x00\xf4(.)([\x20-\x7e]{2,50})\x00", raw, re.S)
    if m:
        out["current_material"] = m.group(2).decode("utf-8", "replace")
        out["has_master"] = True
    # 🔴 ЗАМЕР 30.10.2026 (по КАРТЕ → секция `LargeText`):
    #    `PTC_MASTER_MATERIAL\x00 <4 байта> e3 33 <ИМЯ МАТЕРИАЛА>\x00 f7 1d`
    #    `PTC_REPORTED_MATERIAL\x00 <6 байт> e3 33 <ИМЯ МАТЕРИАЛА>\x00`
    #    ИМЯ МАТЕРИАЛА ЧИТАЕТСЯ (напр. `65G_MMKGS` = сталь 65Г).
    #    ⚠️ Раньше я считал `65G_MMKGS` «единицами» — ЭТО БЫЛО НЕВЕРНО (это имя стали!).
    m = re.search(rb"PTC_MASTER_MATERIAL\x00.{0,8}?\xe3\x33([\x20-\x7e]{2,40})\x00", raw, re.S)
    if m:
        out["master_name"] = m.group(1).decode("utf-8", "replace")
        out["has_master"] = True
    m = re.search(rb"PTC_REPORTED_MATERIAL\x00.{0,10}?\xe3\x33([\x20-\x7e]{2,40})\x00", raw, re.S)
    if m:
        out["reported_name"] = m.group(1).decode("utf-8", "replace")
    return out


# ═════════════════════════════════════════════════════════════════════════════
# 4. PACK — раскладка по ЯЩИКАМ (= таблицам базы)
#    ЯВНЫЙ СПИСОК: что · откуда · куда
def extract_matrices(raw, anchors):
    """[{field,dims,values}] — matrix (4x4) · outline (2x3).

    ФОРМАТ: `<имя>\x00 f9 <строк> [<столбцов>] <значения>` (§181).
    ⚡ ОПТИМИЗАЦИЯ: быстрый find `\xf9`, имя НАЗАД (не regex по всему файлу).
    """
    out = []
    pos = raw.find(b"\xf9")
    while pos >= 0:
        j = pos - 1
        if j >= 0 and raw[j] == 0:
            k = j - 1
            while k >= 0 and (97 <= raw[k] <= 122 or raw[k] == 95):
                k -= 1
            name = raw[k + 1:j].decode("ascii", "replace")
            if 3 <= len(name) <= 30 and pos + 2 < len(raw):
                seg = raw[pos + 3:pos + 3 + 200]
                vals = []
                for i2 in range(0, min(len(seg) - 3, 64), 4):
                    v = struct.unpack(">f", seg[i2:i2 + 4])[0]
                    if -1e9 < v < 1e9 and abs(v) > 1e-12:
                        vals.append(round(v, 6))
                out.append({"field": name, "dims": [raw[pos+1], raw[pos+2]], "values": vals[:16]})
        pos = raw.find(b"\xf9", pos + 1)
    return out



# ═════════════════════════════════════════════════════════════════════════════
def pack(raw, anchors, feat_dict):
    """{таблица: данные} — что пишем в базу."""
    path_kind = ""
    m = re.match(rb"#UGC:2\s+(\w+)", raw)
    if m:
        path_kind = m.group(1).decode()

    passport = extract_passport(raw, anchors)
    mass = extract_mass(raw, anchors)
    links = extract_links(raw, anchors)
    return {
        "snapshots": {                      # паспорт модели
            "kind": path_kind,
            "user": passport["user"],
            "computer": passport["computer"],
            "rev": passport["rev"],
            "creo": passport["creo"],
            "ts": passport["ts"],
            "material": passport["material"],
        },
        "mass_props": mass,                 # масса/объём/площадь (§175, первое тело)
        "bodies": extract_bodies(raw, anchors),        # ★ ТЕЛА (§177) — по одному на тело
        "materials": extract_materials(raw, anchors),  # ★ МАТЕРИАЛЫ (§176/§177)
        "master_mat": extract_master(raw, anchors),    # ★ МАСТЕР-МАТЕРИАЛ (один)
        "features": extract_features(raw, anchors, feat_dict),      # дерево (§171)
        "dimensions": extract_dimensions(raw, anchors),             # размеры (§173)
        "equations": extract_equations(raw, anchors),               # 2 места (§174)
        "health": extract_health(raw, anchors),                     # здоровье
        "params": extract_params(raw, anchors),                     # ВСЕ параметры (без отсева!)
        "unknown_fields": extract_unknown_fields(raw, anchors),     # ★ «НЕ ИЗУЧЕНО» (закон!)
        "tools": extract_tools(raw, anchors),                       # ★ ИНСТРУМЕНТЫ (.mfg)
        "matrices": extract_matrices(raw, anchors),                 # ★ МАТРИЦЫ/ГАБАРИТЫ (§181)
        "drawing": extract_drawing(raw, anchors),                   # ★ ЧЕРТЁЖ (.drw)
        "links": links,                                             # связи
        "media": extract_media(raw, anchors),                       # превью
    }


# ═════════════════════════════════════════════════════════════════════════════
# 5. SCAN ITEM — 1 чтение + 1 проход + ящики
# ═════════════════════════════════════════════════════════════════════════════
def scan_item_new(path, feat_dict):
    """
    Прочитать файл ОДИН раз → КАРТА → 1 проход → ящики. Возвращает {таблица: данные}.

    ПОРЯДОК (§178, закон): ① `#UGC_TOC` (карта секций) → ② один проход по байтам →
    ③ раскладка по ящикам. Карта сохраняется в `_meta.toc` (видно, где что лежит).
    """
    raw = read_file(path)
    if raw is None:
        return None
    toc = read_toc(raw)                     # ← ① КАРТА (закон!)
    anchors = map_anchors(raw)              # ← ② ОДИН проход
    boxes = pack(raw, anchors, feat_dict)   # ← ③ раскладка по ящикам
    boxes["_meta"] = {"path": path, "size": len(raw), "anchors": len(anchors),
                      "toc": {k: {"off": v[0], "len": v[1]} for k, v in toc.items()}}
    return boxes


# ═════════════════════════════════════════════════════════════════════════════
# 7. АДАПТЕР: НОВЫЙ СКАНЕР → СТАРЫЙ ФОРМАТ `scan_item` (для переключения!)
#    Назначение: `engine.do_scan` ждёт dict старого формата (`it[...]`).
#    Адаптер переводит ящики нового сканера в этот формат — БЕЗ правки do_scan.
# ═════════════════════════════════════════════════════════════════════════════
def new_to_old(path, boxes):
    """
    Ящики нового сканера → dict старого формата (`scan_item`).

    Используется при ПЕРЕКЛЮЧЕНИИ (флаг `scanner_new` в настройках).
    """
    if not boxes:
        return None
    snap = boxes.get("snapshots") or {}
    mm = boxes.get("master_mat") or {}
    bodies = boxes.get("bodies") or []
    links = boxes.get("links") or {}
    # ОБЪЁМ: сумма по телам (у детали может быть НЕСКОЛЬКО тел!)
    vol = 0.0
    for b in bodies:
        v = b.get("volume")
        if v:
            vol += float(v)
    # МАТЕРИАЛ: мастер или первый не-системный
    material = mm.get("current_material") or mm.get("master_name") or ""
    if not material:
        for m in (mm.get("materials") or []):
            if not m.get("system"):
                material = m.get("name") or ""
                break
    # СВЯЗИ: refs (состав) из components
    refs = {}
    for c in (links.get("components") or []):
        refs[c.get("name")] = c.get("count", 1)
    try:
        st = os.stat(path)
        size, mtime = st.st_size, st.st_mtime
    except OSError:
        size, mtime = 0, 0
    return {
        "model": model_of(path),
        "path": path,
        "size": size,
        "mtime": mtime,
        "volume": vol or 0.0,
        "material": material,
        "name": snap.get("name", "") or "",
        "designation": snap.get("designation", "") or "",
        "rev": snap.get("rev", "") or "",
        "author": snap.get("user", "") or "",
        "revdate": snap.get("ts", "") or "",
        "role": snap.get("kind", "") or "",
        "refs": refs,
        "hist": 0,
        "creo": snap.get("creo", "") or "",
        "base": "", "dkind": "", "copy_from": links.get("copy_from", "") or "",
        "parts": [], "derived_all": [(d, "наследование") for d in (links.get("derived") or [])],
        "props_all": [], "cparams": [], "family": [], "hist2": [], "media": [],
        # ★ ДОПОЛНИТЕЛЬНО (новые данные — для расширенной записи)
        "_new": boxes,
    }


def scan_item_new_old(path, feat_dict=None):
    """Новый сканер → СТАРЫЙ формат (для `engine.do_scan`)."""
    boxes = scan_item_new(path, feat_dict or FEATTYPE)
    return new_to_old(path, boxes)


# ═════════════════════════════════════════════════════════════════════════════
# 8. ЗАМЕР (сравнение с базовой точкой engine.py = 19.0 мс/файл)
# ═════════════════════════════════════════════════════════════════════════════
def bench(folder, limit=30):
    files = []
    for dp, _, fs in os.walk(folder):
        for f in fs:
            if f.lower().endswith((".prt.1", ".asm.1", ".drw.1")):
                files.append(os.path.join(dp, f))
        if len(files) >= limit * 3:
            break
    files = files[:limit]
    feat = FEATTYPE
    print(f"ФАЙЛОВ: {len(files)} | словарь типов: {len(feat)}")
    t0 = time.perf_counter()
    ok = 0
    for p in files:
        try:
            if scan_item_new(p, feat):
                ok += 1
        except Exception as ex:
            print("  ОШИБКА:", os.path.basename(p), ex)
    T = time.perf_counter() - t0
    print(f"\n=== НОВЫЙ СКАНЕР (1 проход) ===")
    print(f"  файлов: {ok}/{len(files)}")
    print(f"  ВСЕГО: {T:.2f} сек | НА ФАЙЛ: {T / max(ok, 1) * 1000:.1f} мс")
    print(f"  прогноз 70 000 файлов: {T / max(ok, 1) * 70000 / 60:.1f} мин")
    print(f"  БАЗА (engine.py): 19.0 мс | прогноз 22.2 мин")
    if ok:
        print(f"  УСКОРЕНИЕ: {19.0 / (T / ok * 1000):.2f}×")
    return files


# ── 3.12. ИНСТРУМЕНТЫ МАНУФАКТУРИНГА (§179, долг закрыт) ─────────────────────
def extract_tools(raw, anchors):
    """
    [{tool_id, n_params, assem}] — инструменты из `.mfg` (мануфактуринг).

    Формат (замер `1_10.mfg.1`): `tool_array f8 <N>` → [ type · tool_id "T0010" ·
    tool_params f8 <K> ] · `Mfg_Assem → assem_ptr = "<сборка>"`.
    """
    out = []
    m = re.search(rb"Mfg_Assem\x00\xe3\xe0\nassem_ptr\x00([\x20-\x7e]{1,40})\x00", raw)
    assem = m.group(1).decode("utf-8", "replace") if m else ""
    for tm in re.finditer(rb"tool_array\x00\xf8(.)\xf7", raw):
        seg = raw[tm.start():tm.start() + 4000]
        for tid in re.finditer(rb"\xe0\ntool_id\x00([\x20-\x7e]{2,20})\x00", seg):
            after = seg[tid.end():tid.end() + 60]
            mp = re.search(rb"tool_params\x00\xf8(.)", after)
            out.append({
                "tool_id": tid.group(1).decode("utf-8", "replace"),
                "n_params": mp.group(1)[0] if mp else 0,
                "assem": assem,
            })
    return out


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else r"Z:\PTC\Work\001_15 ЦТКД Электон"
    files = bench(root, 30)
    # показать пример разбора
    if files:
        feat = FEATTYPE
        b = scan_item_new(files[0], feat)
        print(f"\n=== ПРИМЕР: {os.path.basename(files[0])} ===")
        print(f"  snapshots : {b['snapshots']}")
        print(f"  mass_props: {b['mass_props']}")
        print(f"  features  : {len(b['features'])} · dimensions: {len(b['dimensions'])}"
              f" · equations: {len(b['equations'])} · params: {len(b['params'])}")
        print(f"  health    : {b['health']}")
        print(f"  links     : derived={b['links']['derived']} copy={b['links']['copy_from']!r}")
