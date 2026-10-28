# -*- coding: utf-8 -*-
r"""PLM Reader — движок ПЛМ «в лоб»: паспорт изделий, дерево производства, входимость и ИЗМЕНЕНИЯ.

Creo не нужен. Своя база лежит РЯДОМ с инструментом (db\plm_reader.db) — легко перенести на другую машину.
Корень склада ОДИН на все входы (окно, CLI, мета базы): Z:\PTC.

CLI:
  python engine.py scan [--roots П1 П2] [--limit СЕК]
  python engine.py where МОДЕЛЬ        (в каких сборках и сколько раз)
  python engine.py changes [--n 40]    (журнал изменений: кто/когда/что)
"""
import argparse
import datetime
import json
import os
import re
import sqlite3
import struct
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)          # сначала СВОЯ папка (вложенный читатель creo_read — переносимость)
BASE_DIR = os.environ.get("PLM_DATA_DIR") or os.path.join(HERE, "db")   # рабочая папка базы (можно увести на другой диск)
DB = os.environ.get("PLM_DB") or os.path.join(BASE_DIR, "plm_reader.db")   # данные — в подпапке db\ (её не делим)
# Логи: дома — в общий D:\AI\log, на чужой машине — рядом с инструментом (переносимость)
LOG = os.environ.get("PLM_LOG") or (
    r"D:\AI\log\plm_reader\engine.log" if os.path.isdir(r"D:\AI\log") else os.path.join(HERE, "log", "engine.log"))
DEFAULT_ROOTS = [r"Z:\PTC"]      # единый корень склада: тот же, что в окне (settings.json) и в meta базы

SETTINGS_FILE = os.environ.get("PLM_SETTINGS") or os.path.join(HERE, "settings", "settings.json")


def scan_config(settings=None):
    """Корни и исключения ИЗ НАСТРОЕК окна — чтобы CLI и окно сканировали ОДНО И ТО ЖЕ.

    Возвращает (roots, exclude). Раньше CLI брал только DEFAULT_ROOTS и не знал про
    исключения — из-за чего `check` считал исключённые папки «пропавшими», а `scan`
    затирал в базе meta exclude пустым списком (найдено аудитом 02.10.2026)."""
    try:
        if settings is None:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                settings = json.load(f)
    except Exception:
        return None, None
    if not isinstance(settings, dict):
        return None, None
    roots = [r for r in (settings.get("folders") or []) if isinstance(r, str) and r.strip()]
    excl = [e for e in (settings.get("exclude") or []) if isinstance(e, str) and e.strip()]
    return (roots or None), (excl or None)


def set_base_dir(path):
    """Увести РАБОЧУЮ папку базы на другой диск (пусто = рядом, `db\\`).

    Меняет всё, что завязано на папку: сама база, замок скана, кэш и бэкапы.
    Звать ДО первого обращения к базе (окно зовёт сразу после чтения настроек)."""
    global BASE_DIR, DB, LOCK_FILE
    d = (path or "").strip()
    BASE_DIR = os.path.abspath(d) if d else os.path.join(HERE, "db")
    DB = os.environ.get("PLM_DB") or os.path.join(BASE_DIR, "plm_reader.db")
    try:                                     # замок всегда РЯДОМ с базой, а не в папке инструмента
        LOCK_FILE = os.path.join(BASE_DIR, "plm.lock")
    except NameError:                        # LOCK_FILE ещё не объявлен — создадим позже
        pass
    os.makedirs(BASE_DIR, exist_ok=True)
    return BASE_DIR


def mirror_dirs(settings=None):
    """Папки-ЗЕРКАЛА базы: список `db_mirror` из настроек (пусто = не дублировать).

    Читает тот же settings\\settings.json, что и окно, — поэтому работает и для CLI."""
    try:
        if settings is None:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                settings = json.load(f)
    except Exception:
        return []
    out = []
    for p in (settings.get("db_mirror") or []):
        if isinstance(p, str) and p.strip():
            v = os.path.abspath(p.strip())
            if v.lower() not in [x.lower() for x in out] and v.lower() != BASE_DIR.lower():
                out.append(v)
    return out


def mirror_keep():
    """Сколько свежих баз держать в КАЖДОМ зеркале (настройка `mirror_keep`, 1..50, по умолч. 3)."""
    try:
        return max(1, min(50, int(_settings_json().get("mirror_keep") or KEEP_MIRROR)))
    except Exception:
        return KEEP_MIRROR


def mirror_full_only():
    """Зеркалить только после ПОЛНОГО скана (настройка `mirror_full_only`, по умолчанию True)."""
    return bool(_settings_json().get("mirror_full_only", True))


def mirror_published(ver, mirrors=None):
    """Скопировать ОПУБЛИКОВАННУЮ базу в каждое зеркало (другой диск) и почистить старые.

    Ошибка зеркала НЕ роняет скан: основная база уже опубликована, пишем в лог и идём дальше."""
    import shutil
    keep = mirror_keep()
    done = []
    for d in (mirrors if mirrors is not None else mirror_dirs()):
        name = os.path.basename(ver)
        dst = os.path.join(d, name)
        try:
            os.makedirs(d, exist_ok=True)
            shutil.copy2(ver, dst)
            done.append(dst)
            # ротация в зеркале: держим НАСТРАИВАЕМОЕ число свежих баз (mirror_keep)
            try:
                olds = sorted(f for f in os.listdir(d)
                              if re.match(r"^plm_reader_\d{8}_\d{6}\.db$", f))
                for old in olds[:-keep]:
                    os.remove(os.path.join(d, old))
            except Exception as e:
                log("mirror %s: ротация не удалась (%s)" % (d, e))
        except Exception as e:
            log("mirror FAIL %s: %s" % (d, e))
    if done:
        log("mirror: продублировано в %d папок: %s"
            % (len(done), ", ".join(done)))
        print("mirror: база продублирована -> %s" % ", ".join(done), flush=True)
    return done


def as_roots(x):
    """Корни скана ВСЕГДА списком. Поддерживает строку с разделителем ';'."""
    if x is None:
        return list(DEFAULT_ROOTS)
    
    # Если это строка, пробуем разбить её по ';'
    if isinstance(x, (str, bytes, os.PathLike)):
        if isinstance(x, bytes):
            x = x.decode("utf-8", "ignore")
        if isinstance(x, str) and ";" in x:
            x = [part.strip() for part in x.split(";")]
        else:
            x = [x]
            
    out = []
    for r in x:
        try:
            r = os.fspath(r)
        except Exception:
            r = str(r)
        if isinstance(r, bytes):
            r = r.decode("utf-8", "ignore")
        r = r.strip()
        if r and r not in out:
            out.append(r)
    return out
MODEL = re.compile(r"\.(prt|asm|drw)\.\d+$", re.IGNORECASE)
HISTRE = re.compile(rb"\xf7(.)\xe3([0-9]{1,7})\x00\x00(.{0,220}?)\x00((?:Creo )?[0-9][0-9.]*)\x00", re.S)
REF_PART = re.compile(rb"ref_part_tab\x00")
NAME_N = re.compile(rb"name\x00([A-Za-z0-9_\-\.]{4,47})\x00")
# ⚠️ ОСТАВЛЕНО для совместимости (старые вызовы). НЕ ИСПОЛЬЗОВАТЬ в новых местах:
# регулярка с `.` по скиллу `Creo\READ\SKILL_creo_read_roles.md` §5 п.1 НЕ РАБОТАЕТ надёжно
# (непечатные байты между тегами), берёт ТОЛЬКО первую запись и ТОЛЬКО латиницу.
MERGE_BASE = re.compile(rb"MERGE_BASE_PART.{0,80}?([A-Za-z0-9_\-]{5,40})\x00", re.S)

# 🔴 БАЙТОВЫЕ ЯКОРЯ ЗАПИСИ `MERGE_BASE_PART` (скилл `SKILL_creo_read_roles.md` §1, замер 28.10.2026):
#   "MERGE_BASE_PART" \x00 \x27 \xeb \x02 z \xd8 \x00 \xe3 \x33 \xf7 \x1c <ИМЯ РОДИТЕЛЯ> \x00
#                                                        ^^^^^^^^^^^^^^^^^ ЯКОРЬ ИМЕНИ
#   … повтор: \xf7 \x1d \xe3 \x33 <ИМЯ РОДИТЕЛЯ> \x00
# Имя стоит ПОСЛЕ `\xe3\x33\xf7\x1c` и повторяется ДВАЖДЫ — берём первое вхождение.
_MB_MARK = b"MERGE_BASE_PART"
_MB_ANCHOR = b"\xe3\x33\xf7\x1c"          # перед именем родителя (основная запись)
_MB_ANCHOR2 = b"\xe3\x33"                 # второй вариант (дубль)


def _name_at(raw, pos, limit=64):
    """Имя модели, начинающееся с позиции `pos`: до `\\x00`, UTF-8, без служебных байтов.

    По скиллу §5 п.1 — БЕЗ регулярок: идём по байтам от `pos` до нуля, отсекаем
    непчатные/служебные. Кириллица (UTF-8, многобайтная) сохраняется — скилл §1 доп.
    """
    if pos < 0 or pos >= len(raw):
        return ""
    end = raw.find(b"\x00", pos)
    if end < 0:
        end = min(len(raw), pos + limit)
    chunk = raw[pos:end][:limit]
    # Отсекаем ведущие служебные байты Creo (могут быть прямо перед именем).
    i = 0
    while i < len(chunk) and chunk[i] < 0x20:
        i += 1
    chunk = chunk[i:]
    if not chunk:
        return ""
    s = chunk.decode("utf-8", "replace")
    s = "".join(ch for ch in s if ch.isprintable())
    return s.strip()


def merge_base_parts(raw):
    """ВСЕ родители из `MERGE_BASE_PART` — [(имя_родителя, вид_записи)] (скилл §1 + §1 доп.).

    Владелец: «наследований есть несколько вариантов в крео: как наследование, как добавление
    тела… разница есть» — и замер это подтвердил: в ОДНОМ файле бывает НЕСКОЛЬКО записей
    `MERGE_BASE_PART` (напр. `500-55-500-model-master.prt.1` — 3 записи: отливка, мастер, деталь).

    Владелец о именах: «имя МОДЕЛИ РОДИТЕЛЯ и имя МОДЕЛИ потомка может быть любым, вообще
    не похожим. НО СВЯЗЬ внутри файла будет уже к точному реальному имени!» — поэтому имя берём
    ИЗ БАЙТОВ файла и НЕ сверяем с именами файлов на диске.

    Реализация ПО СКИЛЛУ: `bytes.find` (без регулярок), ВСЕ вхождения, UTF-8.
    """
    out, seen = [], set()
    raw = raw or b""
    pos = raw.find(_MB_MARK)
    while pos >= 0:
        after = pos + len(_MB_MARK)
        # Ищем якорь имени в пределах разумного окна (запись рядом с маркером).
        window = raw[after:after + 300]
        ip = window.find(_MB_ANCHOR)
        shift = len(_MB_ANCHOR)
        if ip < 0:
            ip = window.find(_MB_ANCHOR2)
            shift = len(_MB_ANCHOR2)
        if ip >= 0:
            nm = _name_at(window, ip + shift)
            if nm and len(nm) >= 2 and nm.upper() not in ("MM_ASSY", "MM_PART", "SBORKA_MM",
                                                          "SBORKA_MFG", "MFG_NC"):
                key = nm.upper()
                if key not in seen:
                    seen.add(key)
                    out.append((nm, "наследование"))
        pos = raw.find(_MB_MARK, after)
    return out


_RP_NAME = b"\xe0\x0aname\x00"          # ЯКОРЬ ИМЕНИ в записи `ref_part_tab` (скилл §2)


def ref_part_parents(raw):
    """ЗАГОТОВКА/ОТЛИВКА из `ref_part_tab` → поле `name` (скилл §2, якорь проверен 28.10.2026).

    ⚠️ Только для ДЕТАЛЕЙ (`.prt`): у сборок `ref_part_tab` = СПИСОК КОМПОНЕНТОВ, а не родитель.

    ЗАМЕР живого файла `500-55-500-model-master.prt.1` (hex):
        ref_part_tab\\x00 … \\xe0\\x00 objname\\x00 \\xe2 \\xe0\\x01 object_type\\x00 \\x02
            \\xe0\\x0a name \\x00 |052401-OTLIVKA| \\x00
    🔴 ГРАБЛЯ (моя, 28.10.2026): искать `name\\x00` «как есть» НЕЛЬЗЯ — первым попадается
    `objname\\x00`, и вместо имени читалось `\\xe2\\xe0\\x01object_type` («object_type»).
    Имя берём ТОЛЬКО после якоря `\\xe0\\x0aname\\x00` (тип-префикс `0a` = строка).
    """
    out, seen = [], set()
    raw = raw or b""
    pos = raw.find(b"ref_part_tab\x00")
    while pos >= 0:
        seg_end = min(len(raw), pos + 600)
        i = raw.find(_RP_NAME, pos, seg_end)
        if i >= 0:
            nm = _name_at(raw, i + len(_RP_NAME), limit=64)
            if nm and len(nm) >= 2 and nm.upper() not in ("MM_ASSY", "MM_PART", "SBORKA_MM",
                                                          "SBORKA_MFG", "MFG_NC"):
                key = nm.upper()
                if key not in seen:
                    seen.add(key)
                    out.append(nm)
        pos = raw.find(b"ref_part_tab\x00", pos + 1)
    return out



COPY_FROM_RE = re.compile(rb"from_mdl_name\x00(.{1,160}?)to_mdl_name\x00", re.S)


def _clean_model_name(b):
    """Имя модели из байтов Creo: UTF-8 + срез служебных байтов, которые Creo ставит перед строкой."""
    s = b.decode("utf-8", "replace")
    s = "".join(ch for ch in s if ch.isprintable())
    return re.sub(r"^[^0-9A-Za-zА-Яа-яЁё]+", "", s).strip()


def copy_from_of(raw):
    """ОТ КАКОЙ МОДЕЛИ СКОПИРОВАНА деталь — «Модель скопирована от …» (Creo).

    В файле это пара записей `from_mdl_name` → `to_mdl_name` (внутри — путь копирования).
    Дом этого не читал вовсе, поэтому ответ на вопрос «от чего скопирована деталь» взять
    было негде, хотя в Creo он виден. Имя лежит в UTF-8 (кириллица — многобайтная).
    Возвращает имя источника с расширением (напр. `X.PRT`) или ''."""
    m = COPY_FROM_RE.search(raw or b"")
    if not m:
        return ""
    n = re.search(rb"([^\x00]{2,90}\.(?:PRT|ASM|DRW))\x00", m.group(1))
    return _clean_model_name(n.group(1)) if n else ""


def copy_from_file(path):
    """То же, но ПРЯМО ИЗ ФАЙЛА — работает и на уже собранной базе, без перескана."""
    try:
        with open(path, "rb") as f:
            return copy_from_of(f.read())
    except Exception:
        return ""


def derived_of(raw, path=""):
    """Из какой модели сделана деталь (зеркало/заготовка/отливка): (имя, вид) или ('', '').

    🔴 ПЕРЕПИСАНО 28.10.2026 по скиллу `Creo\\READ\\SKILL_creo_read_roles.md` §1/§2/§5:
      * `MERGE_BASE_PART` → «наследование» (зеркало), родитель = имя из байтов;
      * `ref_part_tab` → «производная» (заготовка/отливка) — ⚠️ ТОЛЬКО для `.prt`
        (у сборок это СПИСОК КОМПОНЕНТОВ, а не родитель — скилл §2 ⚠️);
      * возвращает ПЕРВОГО родителя (совместимость со старыми вызовами);
        ВСЕ родители — через `merge_base_parts()` / `ref_part_parents()`.

    Старый код брал ТОЛЬКО первую запись регуляркой `.{0,80}?` (скилл это запрещает) —
    из-за этого терялись остальные родители и кириллица, а в имя попадал мусор
    (`PTC_NOTE_TEXT`, `PTC_MATERIAL_TYPE`).
    """
    mb = merge_base_parts(raw)
    if mb:
        return mb[0][0], "наследование"
    if not is_drawing_file(path):
        rp = ref_part_parents(raw)
        if rp:
            return rp[0], "производная"
    return "", ""
def _app_version():
    """Версия — ЕДИНЫЙ источник: APP_VERSION в plm_reader.py.
    Иначе engine.VERSION расходится с шапкой окна, и check_updates вечно просит обновление (V31 vs V32)."""
    try:
        with open(os.path.join(HERE, "plm_reader.py"), encoding="utf-8") as f:
            for line in f:
                m = re.match(r'\s*APP_VERSION\s*=\s*"(V\d+)"', line)
                if m:
                    return m.group(1)
    except Exception:
        pass
    return "V0"


VERSION = _app_version()
PARSER_TAG = "p25"      # меняй при ЛЮБОМ изменении правил разбора — форсирует полный пересчёт
                        # V137 (28.10.2026): p24 → p25. НАСЛЕДОВАНИЕ ПЕРЕЧИТАНО ПО СКИЛЛУ
                        # `Creo\READ\SKILL_creo_read_roles.md`: `MERGE_BASE_PART` — без регулярок
                        # (`bytes.find`), ВСЕ записи (не первая!), имя в UTF-8 (была потеряна
                        # КИРИЛЛИЦА — читалась только латиница), мусор (`PTC_NOTE_TEXT`,
                        # `PTC_MATERIAL_TYPE`) больше не попадает в имя родителя;
                        # `ref_part_tab` — якорь имени `\xe0\x0aname\x00` (было `name\x00` →
                        # читалось `objname`/`object_type`). Замер: 86 связей на 111 файлах,
                        # до 6 родителей у одного файла. Нужен ПОЛНЫЙ перескан.
                        # V135 (28.10.2026): p23 → p24. Таблица семейства пишется ТОЛЬКО деталям
                        # (.prt), состав (.asm_comp) — ТОЛЬКО не-чертежам; в базу ушли 15 937 + 11 490
                        # ложных исполнений и 25 977 ложных связей чертежей — нужен ПОЛНЫЙ перескан.
# p23 (23.10.2026): + связи из СТРУКТУРЫ файла (`asm_components`, каскад трёх каналов по версии
# Creo, источник в базе `asm_comp`): состав сборки, .asm-обработки → деталь/заготовка/отливка/
# инструмент/ОСНАСТКА. До этого состав брался по вхождению имени в байты, оснастки в базе не было.


def parser_tag_changed():
    """База собрана СТАРЫМИ правилами разбора? Тогда нужен ПОЛНЫЙ скан (перечитает все файлы).

    Окно обязано СКАЗАТЬ об этом прямо (слово владельца 07.10.2026: «если нужен „перечитать
    всё“ — просто так скажи»): после обновления дома новые связи (например «копия от»)
    появляются в базе ТОЛЬКО после полного прохода, и молчать об этом нельзя.
    """
    try:
        con = connect()
        r = con.execute("SELECT v FROM meta WHERE k='param_sig'").fetchone()
        con.close()
        return (not r) or (not str(r[0] or "").endswith("|" + PARSER_TAG))
    except Exception:
        return False
BACKUP_KEEP = int(os.environ.get("PLM_BACKUP_KEEP") or 3)   # сколько бэкапов базы держать в db\backup\
KEEP_MIRROR = int(os.environ.get("PLM_KEEP_MIRROR") or 3)   # сколько опубликованных баз держать в каждом зеркале


def log(msg):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s  %s\n" % (datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"), msg))
    except Exception:
        pass


def stem(name):
    n = name.upper()
    for ext in (".PRT", ".ASM", ".DRW", ".NEU", ".SEC", ".M_P", ".PRT.", ".ASM."):
        if ext in n:
            n = n.split(ext)[0]
            break
    return re.sub(r"\.\d+$", "", n)


_VER_RE = re.compile(r"^(.*)\.([A-Za-z_]{2,4})\.(\d+)$", re.IGNORECASE)


def _filter_latest(files_stat):
    """«только последние версии»: у каждого изделия (папка, база, тип) оставить файл СТАРШЕЙ версии.

    Изделие — имя вида `БАЗА.ТИП.НОМЕР` (напр. `123.45.prt.12`); файлы без номера версии проходят
    как есть. Так настройка работает В ГЛАВНОМ СКАНЕ, а не только в мёртвом файловом сканере.
    """
    groups, plain = {}, []
    for it in files_stat:
        m = _VER_RE.match(os.path.basename(it[0]))
        if not m:
            plain.append(it)
            continue
        key = (os.path.dirname(it[0]).lower(), m.group(1).lower(), m.group(2).lower())
        groups.setdefault(key, []).append((int(m.group(3)), it))
    out = []
    for lst in groups.values():
        lst.sort(key=lambda x: x[0])
        out.append(lst[-1][1])                # старшая версия изделия
    out += plain
    return out


def parse_toc(raw):
    out, pos = {}, raw.find(b"#UGC_TOC")
    for _ in range(20):
        if pos < 0:
            break
        p = raw.find(b"\n", pos)
        nxt = -1
        while True:
            e = raw.find(b"\n", p + 1)
            if e < 0:
                break
            line = raw[p + 1:e].decode("ascii", "replace").strip()
            p = e
            if line.startswith("NEXT_TOC_ENTRY"):
                nxt = int(line.split()[1], 16)
                break
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_:]{1,40}) ([0-9a-f]{2,8}) ([0-9a-f]{2,8})"
                         r"(?: ([0-9a-f]{2,8}))?(.*)$", line)
            if m and (not m.group(5).strip() or m.group(5).strip()[0] in "0123456789-"):
                ln = int(m.group(4), 16) if m.group(4) else int(m.group(3), 16)
                out[m.group(1)] = (int(m.group(2), 16), max(ln, 1))
        if nxt < 0 or nxt >= len(raw):
            break
        pos = nxt
    return out


def real(raw, key):
    m = re.search(rb"\xe0\x02" + key.encode() + rb"\x00\xed", raw)
    if not m or m.end() + 8 > len(raw):
        return None
    try:
        return struct.unpack(">d", raw[m.end():m.end() + 8])[0]
    except Exception:
        return None


def params(raw, toc):
    out = {}
    if "NeuPrtSld" not in toc:
        return out
    off, ln = toc["NeuPrtSld"][0], toc["NeuPrtSld"][1]
    for m in re.finditer(rb"([\x20-\xff]{3,32})\x00\xe2\x33(.{0,60}?)\x00", raw[off:off + ln], re.S):
        t = re.search(r"[\w]+$", m.group(1).decode("utf-8", "replace"))
        try:
            v = m.group(2).decode("utf-8")
        except UnicodeDecodeError:
            continue
        if t and v and "\x00" not in v:
            out.setdefault(t.group(0), " ".join(v.split()))
    return out


def role(raw):
    if b"MERGE_BASE_PART" in raw:
        m = re.search(rb"MERGE_BASE_PART.{0,80}?([A-Za-z0-9_\-]{5,40})\x00", raw, re.S)
        return "nasled." + (m.group(1).decode("latin-1") if m else "?")
    for m in re.finditer(rb"ref_part_tab\x00", raw):
        nm = re.search(rb"name\x00([A-Za-z0-9_\-\.]{4,47})\x00", raw[m.end():m.end() + 200])
        if nm:
            return "proizv." + nm.group(1).decode("latin-1")
    return ""


TAIL = re.compile(rb"\xf7(.)\xe3([0-9]{1,7})\x00\x00(.{0,220}?)\x00((?:Creo )?[0-9][0-9.]*)\x00", re.S)
STAMP = re.compile(rb"\xf7\x14([\x20-\x7e\xc0-\xff]{1,24}?)\x00\xe2(.)(.)(.)(.)(.)(.)", re.S)
NAME_B = re.compile(rb"[\x00-\x1f\x80-\xff]([A-Za-z0-9][A-Za-z0-9_\-\.]{3,47}\.(?:PRT|ASM))",
                    re.IGNORECASE)


def user_time(raw):
    out = []
    for m in STAMP.finditer(raw):
        s, mi, h, d, mo, y = (b[0] for b in m.groups()[1:])
        try:
            dt = datetime.datetime(1900 + y, mo + 1, d, h, mi, s)
        except ValueError:
            continue
        if 1990 <= dt.year <= 2030:
            try:
                who = m.group(1).decode("utf-8")
            except UnicodeDecodeError:
                who = m.group(1).decode("cp1251", "replace")
            out.append((m.start(), who, dt))
    return sorted(set(out))


def last_hist(raw):
    st, last = user_time(raw), None
    for t in TAIL.finditer(raw):
        prev = [s for s in st if s[0] < t.start()]
        last = (t.group(2).decode(), prev[-1][1] if prev else "",
                prev[-1][2].strftime("%d.%m.%y %H:%M") if prev else "")
    return last


def names(raw):
    """Имена моделей внутри файла (расширение срезано) и сколько раз встречаются."""
    c = Counter()
    for m in NAME_B.finditer(raw):
        c[stem(m.group(1).decode("latin-1"))] += 1
    return c


def under_roots(path, roots):
    """Путь внутри одного из корней (без учёта регистра, по границе папки). roots — список."""
    try:
        p = os.path.normcase(os.path.abspath(path))
    except Exception:
        return False
    for r in as_roots(roots):
        rn = os.path.normcase(os.path.abspath(r)).rstrip("\\/")
        if rn and (p == rn or p.startswith(rn + "\\")):
            return True
    return False


def excluded(path, excl):
    """Путь под одной из папок-исключений (без учёта регистра, по границе папки)."""
    if isinstance(excl, str):
        excl = [excl]
    if not excl:
        return False
    try:
        p = os.path.normcase(os.path.abspath(path))
    except Exception:
        return False
    for r in excl:
        rn = os.path.normcase(os.path.abspath(r)).rstrip("\\/")
        if rn and (p == rn or p.startswith(rn + "\\")):
            return True
    return False


def collect(roots, max_mb, max_depth=None, exclude=None, recurse=True):
    """ВСЕ файлы моделей рекурсивно (ключ — путь). max_depth — предел вложенности (None = без предела).
    recurse=False («с подпапками» снят) — только файлы верхней папки, в подпапки не заходим."""
    files = []
    for root in as_roots(roots):
        root = os.path.abspath(root)
        if not os.path.isdir(root):
            continue
        for dp, dirs, fs in os.walk(root):
            if exclude:                       # исключённые папки не обходим вовсе — скан чище и быстрее
                dirs[:] = [d for d in dirs if not excluded(os.path.join(dp, d), exclude)]
            if not recurse:
                dirs[:] = []                  # «с подпапками» снят: только верхняя папка
            rel = os.path.relpath(dp, root)
            d = 0 if rel == "." else rel.count(os.sep) + 1
            if max_depth is not None and d > max_depth:
                dirs[:] = []
                continue
            try:
                for f in sorted(fs):
                    if MODEL.search(f):
                        p = os.path.join(dp, f)
                        if exclude and excluded(p, exclude):
                            continue
                        if os.path.getsize(p) <= max_mb * 1_000_000:
                            files.append(p)
            except Exception:
                pass
    return files


def collect_stat(roots, max_mb, max_depth=None, exclude=None, recurse=True):
    """Файлы модели + их size/mtime ОДНИМ проходом (scandir/stat), без повторных stat.
    recurse=False («с подпапками» снят) — только файлы верхней папки."""
    out = []
    lim = max_mb * 1_000_000
    for root in as_roots(roots):
        root = os.path.abspath(root)
        if not os.path.isdir(root):
            continue
        for dp, dirs, fs in os.walk(root):
            if exclude:                       # исключённые папки не обходим вовсе
                dirs[:] = [d for d in dirs if not excluded(os.path.join(dp, d), exclude)]
            if not recurse:
                dirs[:] = []                  # «с подпапками» снят: только верхняя папка
            rel = os.path.relpath(dp, root)
            d = 0 if rel == "." else rel.count(os.sep) + 1
            if max_depth is not None and d > max_depth:
                dirs[:] = []
                continue
            try:
                for f in fs:
                    if not MODEL.search(f):
                        continue
                    p = os.path.join(dp, f)
                    if exclude and excluded(p, exclude):
                        continue
                    try:
                        st = os.stat(p)
                    except OSError:
                        continue
                    if st.st_size <= lim:
                        out.append((p, st.st_size, st.st_mtime, st.st_ctime))
            except Exception:
                pass
    return out


_PARAM_DES = ("\u041e\u0411\u041e\u0417\u041d\u0410\u0427\u0415\u041d\u0418\u0415", "OBOZNACHENIE",
              "DESIGNATION", "PART_NUMBER")
_PARAM_NAME = ("\u041d\u0410\u0418\u041c\u0415\u041d\u041e\u0412\u0410\u041d\u0418\u0415", "NAIMENOVANIE",
               "NAME", "PART_NAME", "TITLE")
_PARAM_MAT = ("PTC_MASTER_MATERIAL", "PTC_MATERIAL_NAME", "PTC_MATERIAL_DESCRIPTION",
              "\u041c\u0410\u0422\u0415\u0420\u0418\u0410\u041b", "MATERIAL")


def _pfirst(pr, keys):
    """Первое непустое значение параметра из списка ключей (по приоритету)."""
    for k in keys:
        v = pr.get(k)
        if v:
            return v
    return ""


def _by_rules(raw, rules):
    """Первое НЕПУСТОЕ по списку правил: имя параметра ИЛИ шаблон `{ИМЯ} "текст" +` (кавычки не выводятся)."""
    for rule in (rules or []):
        r = (rule or "").strip()
        if not r:
            continue
        v = compose(raw, r) if ("{" in r or '"' in r) else param(raw, [r])
        if v:
            return v
    return ""


def _des_from_rel(raw):
    """Есть ли уравнение `ОБОЗНАЧЕНИЕ = rel_model_name` (тогда обозначение = имя модели)."""
    for enc in ("utf-8", "cp1251"):
        try:
            nb = "\u041e\u0411\u041e\u0417\u041d\u0410\u0427\u0415\u041d\u0418\u0415".encode(enc)
        except Exception:
            continue
        i = raw.find(nb)
        if i >= 0 and b"rel_model_name" in raw[i:i + 220]:
            return True
    return False


def scan_item(s, path, stems, fstems=frozenset(), pdes=None, pname=None, pmat=None):
    raw = open(path, "rb").read()
    vol = real(raw, "volume") or real(raw, "mtrl_volume")
    des = _by_rules(raw, pdes or _PARAM_DES)
    nmv = _by_rules(raw, pname or _PARAM_NAME)
    mat = _by_rules(raw, pmat or _PARAM_MAT)
    if not des and _des_from_rel(raw):
        des = s                                  # ОБОЗНАЧЕНИЕ = rel_model_name → имя модели
    nm = names(raw)
    refs = {c: nm[c] for c in nm if c != s and c in stems and len(c) >= 2}
    # V125: ВСЕ параметры модели (имя + тип + значение) и ТАБЛИЦА СЕМЕЙСТВА.
    # Владелец: «все же что за ПЛМ, которая хранит не все параметры?»; «исполнения могут
    # иметь СВОИ параметры, управляемые через уравнения или таблицу семейства».
    cparams = creo_params(raw)
    fam = family_of(raw, s, path)      # V135: таблица семейства — ТОЛЬКО у ДЕТАЛИ (.prt)
    hist2 = creo_history(raw)          # V126: кто/когда правил (компьютер + юзер + Creo)
    h = last_hist(raw) or ("", "", "")
    hm = HISTRE.findall(raw)
    base, dkind = derived_of(raw, path)
    # 🔴 V137 (28.10.2026): ВСЕ родители наследования, а не первый (скилл §1 доп.: в одном файле
    # бывает НЕСКОЛЬКО записей `MERGE_BASE_PART` — замер дал до 5 у одного файла оснастки).
    # `derived_of` оставлен для совместимости (даёт первого), а записываются ВСЕ.
    _mb_all = merge_base_parts(raw)
    _rp_all = ref_part_parents(raw) if not is_drawing_file(path) else []
    derived_all = [(nm, "наследование") for nm, _ in _mb_all]
    derived_all += [(nm, "производная") for nm in _rp_all if nm.upper() not in
                    {n.upper() for n, _ in derived_all}]
    cf = copy_from_of(raw)      # 07.10.2026: «МОДЕЛЬ СКОПИРОВАНА ОТ …» — ОТДЕЛЬНАЯ связь (Creo пишет
                                # её в самом файле: `from_mdl_name` → `to_mdl_name`). Она ДОПОЛНЯЕТ
                                # заготовку/отливку, а не заменяет. Есть и у деталей, и у сборок.
    # СВЯЗИ ИЗ СТРУКТУРЫ (эта сессия): состав сборки и модели .asm-обработки (деталь/заготовка/
    # отливка/инструмент/ОСНАСТКА). Берутся только имена, которые есть на складе (`stems`),
    # иначе в состав лезли бы посторонние записи Creo. Отсюда в базу идёт «связь → оснастка»,
    # которой раньше в базе не было вовсе (ЭТАП 1.7 / 2.6).
    # V135: состав берём у СБОРОК (.asm); чертёж (.drw) составом не обладает вообще — `asm_components`
    # вернёт [] по проверке типа, но и разбирать его байты незачем.
    parts = asm_components(raw, s, stems, path) if not is_drawing_file(path) else []
    return {"model": s, "path": path, "size": len(raw), "mtime": os.path.getmtime(path),
            "volume": vol or 0.0, "material": mat,
            "name": nmv,
            "designation": des,
            "rev": h[0], "author": h[1], "revdate": h[2], "role": role(raw, fstems, s), "refs": refs,
            "hist": len(hm), "creo": (hm[-1][3].decode("latin-1") if hm else ""),
            "base": base, "dkind": dkind, "copy_from": cf, "parts": parts,
            "derived_all": derived_all,
            "cparams": cparams, "family": fam, "hist2": hist2}


# --- ЕДИНЫЙ ЧИТАТЕЛЬ: своя вложенная копия creo_read (папка самодостаточна) ---
try:
    import creo_read as _CR          # своя копия рядом с engine.py (переносимость)
except ImportError:                  # запасной путь: общая библиотека дома
    sys.path.insert(0, os.path.dirname(HERE))
    import creo_read as _CR  # noqa: E402

stem = _CR.stem
parse_toc = _CR.parse_toc
real = _CR.real
params = _CR.params
role = _CR.role
user_time = _CR.user_time
last_hist = _CR.last_hist
names = _CR.names
param = _CR.param
compose = _CR.compose

SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
  path TEXT PRIMARY KEY, model TEXT, folder TEXT, size INTEGER, mtime REAL, volume REAL,
  material TEXT, name TEXT, designation TEXT, rev TEXT, author TEXT, revdate TEXT,
  role TEXT, seen TEXT, hist INTEGER, creo TEXT, created REAL);
CREATE TABLE IF NOT EXISTS changes (
  id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, rev TEXT, kind TEXT, descr TEXT,
  who TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS links (parent TEXT, child TEXT, qty INTEGER, source TEXT);
CREATE INDEX IF NOT EXISTS ix_links_child ON links(child);
CREATE TABLE IF NOT EXISTS derived (child TEXT, base TEXT, kind TEXT, source TEXT);
CREATE INDEX IF NOT EXISTS ix_derived_child ON derived(child);
CREATE INDEX IF NOT EXISTS ix_derived_base ON derived(base);
-- V125: ВСЕ ПАРАМЕТРЫ МОДЕЛИ «как в Creo» (имя + тип + значение). Владелец: «хранить нужно
-- как все параметры детали, так и все параметры исполнения — тогда связи будут реальные».
CREATE TABLE IF NOT EXISTS params (path TEXT, model TEXT, name TEXT, type TEXT, value TEXT);
CREATE INDEX IF NOT EXISTS ix_params_model ON params(model);
CREATE INDEX IF NOT EXISTS ix_params_name ON params(name);
CREATE INDEX IF NOT EXISTS ix_params_path ON params(path);
-- V125: ТАБЛИЦА СЕМЕЙСТВА (генерик ↔ исполнения) — ОТДЕЛЬНО от физических связей `links`.
-- Владелец: «давай попробуем отдельную family, ну а вдруг чего — переделаем».
CREATE TABLE IF NOT EXISTS family (generic TEXT, instance TEXT, params TEXT, source TEXT);
CREATE INDEX IF NOT EXISTS ix_family_generic ON family(generic);
CREATE INDEX IF NOT EXISTS ix_family_instance ON family(instance);
-- V126: ИСТОРИЯ ПРАВОК «КТО И КОГДА» — КОМПЬЮТЕР + ПОЛЬЗОВАТЕЛЬ + ВРЕМЯ + ВЕРСИЯ CREO.
-- Владелец: «+ что когда правилось и кем (имя компьютера + юзер)». Creo пишет это в файл
-- (`user_name`, `comment` → «Наименование компьютера: 'X'», `modif_time`, `Proe_version`).
CREATE TABLE IF NOT EXISTS history (path TEXT, model TEXT, ts TEXT, user TEXT, computer TEXT,
  creo TEXT, rev TEXT, action TEXT);
CREATE INDEX IF NOT EXISTS ix_history_model ON history(model);
CREATE INDEX IF NOT EXISTS ix_history_path ON history(path);
CREATE INDEX IF NOT EXISTS ix_history_comp ON history(computer);
CREATE TABLE IF NOT EXISTS folders (path TEXT PRIMARY KEY, parent TEXT, depth INTEGER,
  models INTEGER, files INTEGER, seen TEXT);
-- V135: ЗДОРОВЬЕ ФАЙЛА — вынесено ИЗ `try` (грабля 28.10.2026: таблица создавалась внутри
-- `try/except`, исключение гасилось, и в боевой базе таблицы `health` НЕ БЫЛО — «no such table:
-- health», история/здоровье файлов не выводились). Теперь создаётся здесь, в `connect()`.
-- Владелец: «Нужно знать историю и ЗДОРОВЬЕ файлов крео».
CREATE TABLE IF NOT EXISTS health (path TEXT PRIMARY KEY, model TEXT, regen TEXT,
  reg_status TEXT, inactive INTEGER, geom_rev TEXT);
CREATE INDEX IF NOT EXISTS ix_health_model ON health(model);
"""


# --- АКТИВНАЯ БАЗА: свежайший опубликованный файл — замены файла не требуется (обходит блокировку по сети) ---
def _base_dir():
    return os.path.dirname(DB)


def _versioned(dbdir=None):
    """Опубликованные versioned-базы plm_reader_ГГГГММДД_ЧЧММСС.db, по возрастанию имени."""
    d = dbdir or _base_dir()
    try:
        return sorted(f for f in os.listdir(d)
                      if re.match(r"^plm_reader_\d{8}_\d{6}\.db$", f))
    except Exception:
        return []


def warehouse_db_dir():
    """ПАПКА БАЗЫ РЯДОМ СО СКЛАДОМ: `<корень>\\plm_reader\\db` — для корней из настроек.

    Владелец 27.10.2026: «сделай чтоб читало наконец». База обязана лежать РЯДОМ СО СКЛАДОМ,
    а не в папке инструмента: инструмент можно перенести/обновить — история склада остаётся.
    Считается от корней настроек (`Z:\\PTC\\Work` → `Z:\\PTC\\Work\\plm_reader\\db`,
    `Z:\\PTC\\CREO-START` → `Z:\\PTC\\CREO-START\\plm_reader\\db`). Нет ни одной — ''.
    """
    try:
        roots = scan_config()[0] or DEFAULT_ROOTS
    except Exception:                              # noqa: BLE001
        roots = DEFAULT_ROOTS
    for root in roots:
        r = str(root).rstrip("\\")
        if not r:
            continue
        cand = os.path.join(r, "plm_reader", "db")
        if os.path.isdir(cand):
            return cand
    return ""


def _is_plm_db(name):
    """ЭТО ФАЙЛ НАШЕЙ БАЗЫ? Законны ТОЛЬКО две формы: `plm_reader.db` и
    `plm_reader_ГГГГММДД_ЧЧММСС.db`.

    ГРАБЛЯ 27.10.2026: в папке базы лежали ПОСТОРОННИЕ файлы — `plm_reader_before_{ 20261006_121208 }.db`
    и `plm_reader_before_patch_20261005_212954.db` (46 МБ, «памятники» от 05.10). Широкий фильтр
    `f.endswith('.db')` пропускал их, и такой «памятник» мог стать АКТИВНОЙ базой (в нём links
    15 085 против 50 746 в боевой). Отсекаем всё, что не подходит ТОЧНО.
    """
    return bool(re.match(r"^plm_reader(_\d{8}_\d{6})?\.db$", name or ""))


def _db_search_dirs():
    """ГДЕ ИСКАТЬ базу. ГЛАВНАЯ ГРАБЛЯ 27.10.2026: база лежала в ДВУХ папках —
    локальной (`<инструмент>\\db`, 63 МБ, от 24.10) и БОЕВОЙ на складе
    (`Z:\\PTC\\CREO-START\\plm_reader\\db`, 188 МБ, от 27.10). `active_db()` смотрела ТОЛЬКО
    в локальную → страница читала СТАРУЮ базу, где нет ни `arch_dims` (параметров), ни
    свежих связей. Теперь ищем в ОБЕИХ и берём САМУЮ СВЕЖУЮ по времени правки.

    ПОРЯДОК ВАЖЕН: СНАЧАЛА папка склада (боевая), потом локальная. `active_db()` берёт
    свежайшую по mtime, но при равных датах выигрывает ПЕРВАЯ в списке — склад идёт раньше.
    Папка `backup\\` НЕ включается (там копии для отката, не боевые).
    """
    out = []
    for d in (warehouse_db_dir(), os.path.dirname(DB), BASE_DIR, os.path.join(HERE, "db")):
        if d and os.path.isdir(d) and d not in out:
            out.append(d)
    # папка базы РЯДОМ СО СКЛАДОМ у КАЖДОГО корня (корней может быть несколько)
    try:
        for root in (scan_config()[0] or []):
            d = os.path.join(str(root).rstrip("\\"), "plm_reader", "db")
            if os.path.isdir(d) and d not in out:
                out.append(d)
    except Exception:                              # noqa: BLE001
        pass
    return out


def active_db():
    """Путь к АКТИВНОЙ базе — САМАЯ СВЕЖАЯ по ВРЕМЕНИ ПРАВКИ, среди ВСЕХ папок базы.

    Владелец: «сделай чтоб читало наконец» (база с датой интереснее — видно, когда снята).
    Порядок: (1) versioned-файлы (`plm_reader_ГГГГММДД_ЧЧММСС.db`) — берём СВЕЖАЙШИЙ по mtime;
    (2) если versioned нет — `plm_reader.db` (он обновляется публикацией).
    Пустой/битый файл (0 байт) пропускаем. Ищем в ЛОКАЛЬНОЙ папке И РЯДОМ СО СКЛАДОМ
    (раньше локальная 63-МБ копия от 24.10 «затмевала» боевые 188 МБ от 27.10).
    """
    dirs = _db_search_dirs()
    cand, main = [], []
    for order, d in enumerate(dirs):
        for name in _versioned(d):
            p = os.path.join(d, name)
            try:
                if os.path.getsize(p) > 0:            # 0 байт = недописанный/битый файл
                    # order: папка СКЛАДА идёт раньше → при равных датах выигрывает она
                    cand.append((os.path.getmtime(p), -order, name, p))
            except Exception:                        # noqa: BLE001 — файл исчез между листингом и stat
                pass
        m = os.path.join(d, "plm_reader.db")
        try:
            if os.path.isfile(m) and os.path.getsize(m) > 0:
                main.append((os.path.getmtime(m), -order, "plm_reader.db", m))
        except Exception:                            # noqa: BLE001
            pass
    if cand:
        return max(cand)[3]                          # самый свежий versioned по ВРЕМЕНИ ПРАВКИ
    if main:
        return max(main)[3]                          # иначе — самый свежий `plm_reader.db`
    return DB


def _rotate(keep=3):
    """Оставить последние `keep` versioned-баз; старые удалить (best-effort — блокировка не мешает)."""
    for name in _versioned()[:-keep]:
        try:
            os.remove(os.path.join(_base_dir(), name))
        except Exception:
            pass


def connect(ro=False, db=None):
    """Соединение с базой. ro=True — ТОЛЬКО ЧТЕНИЕ (PRAGMA query_only): просмотрщик ничего не пишет.
    db — путь базы (для черновика скана); по умолчанию боевая."""
    path = db or active_db()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    con = sqlite3.connect(path, timeout=30)
    if ro:                                   # просмотр: без миграции/схемы и без записи вовсе
        try:
            con.execute("PRAGMA query_only=ON")
        except Exception:
            pass
        return con
    # миграция 25.09.2026: старый ключ (model) → ключ по ПУТИ; старые snapshots/links пересоздаём
    try:
        cols = [r[1] for r in con.execute("PRAGMA table_info(snapshots)")]
        if cols and "folder" not in cols:
            con.execute("DROP TABLE snapshots")
            con.execute("DROP TABLE links")
            con.commit()
        elif cols and "hist" not in cols:                 # 25.09: добавили число записей и версию Creo
            con.execute("ALTER TABLE snapshots ADD COLUMN hist INTEGER")
            con.execute("ALTER TABLE snapshots ADD COLUMN creo TEXT")
            con.commit()
        if cols and "created" not in cols:                # 28.09: дата создания файла (ОС)
            con.execute("ALTER TABLE snapshots ADD COLUMN created REAL")
            con.commit()
    except Exception:
        pass
    con.executescript(SCHEMA)
    con.commit()
    return con


# --- V125: ПАРАМЕТРЫ «КАК В CREO» (имя + тип + значение) и ТАБЛИЦА СЕМЕЙСТВА ---------------
# Владелец: «хранить параметры нужно В ТОЧНОСТИ КАК В CREO»; «все же что за ПЛМ, которая
# хранит не все параметры?»; «исполнения вообще могут иметь свои параметры, управляемые
# через уравнения или таблицу семейства»; «хранить как все параметры детали, так и все
# параметры исполнения, тогда связи будут реальные и выводиться будут без плясок».
#
# РАЗВЕДАНО НА ЖИВЫХ ФАЙЛАХ (DIN912 5.4 МБ, O-RING 6.8 МБ, G11738, DIN931, DIN7991):
#   1) ПАРАМЕТР В ФАЙЛЕ = `<ИМЯ>\x00` + тег значения (`\x27\x88\x20\xe3\x33` или `\xe2\x33`)
#      + `<ЗНАЧЕНИЕ-UTF8>\x00`.  Проверено: `NAME_1\x00'\x88 \xe33Винт   \x00`.
#   2) ТИП — в блоке `attributes`: `name.<ИМЯ>.` → `type.<N>` → `value(<тип>_val).<знач>`.
#      Типы Creo: `s_val` строка · `d_val` число · `i_val` целое · `l_val` длинное.
#   3) ТАБЛИЦА СЕМЕЙСТВА — блок `user_instances` → `user_visible_name` → `drv_tbl_ptr`
#      (генерик) + имена исполнений `<модель>[-_]<размер>`: `DIN912-M2_5X4` … (1375 вхождений
#      в DIN912; 691 в DIN931; 574 в DIN7991; 2085 в O-RING). У 618 библиотечных генериков —
#      ВСЕГО ~10 523 исполнения, и ПЛМ их НЕ читал вовсе (отсюда «мало связей по DIN912»).
#      В скилле дома это УЖЕ было (§8.3/§8.7 SKILL_creo_file_reading.md) — в код не попало.
CREO_VAL_TAG = (b"\x27\x88\x20\xe3\x33", b"\xe2\x33")
CREO_TYPES = {b"s_val": "str", b"d_val": "num", b"i_val": "int", b"l_val": "int",
              b"b_val": "bool", b"r_val": "ref"}


def _creo_clean(s):
    """Убрать служебные байты Creo по краям значения (\\x00-\\x1f) — иначе в базе мусор.

    V125: Creo ставит ПЕРЕД значением пару служебных байтов (`\\xf7\\x1d`, `\\xf7\\x1c`) —
    если их не срезать, в параметр попадает `'\\x1fDIN912-M'` вместо `'DIN912-M'`.
    """
    s = s.strip("\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x11\x12\x13"
                "\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f \t\r\n")
    return s.lstrip("\xf7\x1c\xf7\x1d\xf7\x1e\xf7\x1f").strip()


# имя параметра: латиница/кириллица/подчёркивание, 2..31 знак (UTF-8 кириллица = 2 байта)
_RX_PNAME = rb"([A-Za-z\xd0\x90-\xd1\x8f_][A-Za-z0-9\xd0\x90-\xd1\x8f_\.]{1,30})"
# параметр: <ИМЯ>\0 <тег> <значение>\0
# V125: Creo ставит ПЕРЕД значением служебные байты `\xf7\x1c/\xf7\x1d/\xf7\x1f` —
# их надо срезать ДО декодирования, иначе `\xf7` (невалидный UTF-8) «съедает» `\x1f`
# и в значение попадает мусор (`'\x1fDIN912-M'` вместо `'DIN912-M'`).
_RX_PARAM = re.compile(_RX_PNAME + rb"\x00(?:" + b"|".join(CREO_VAL_TAG) + rb")"
                       rb"(?:\xf7[\x1c-\x1f])?(.{0,120}?)\x00", re.S)
# блок attributes: name.<ИМЯ>. ... type.<N> ... value(<тип>).<знач>
_RX_ATTR = re.compile(rb"name\." + _RX_PNAME + rb"\x00.{0,150}?value\((s_val|d_val|i_val|l_val)\)"
                      rb"\x00(.{0,120}?)\x00", re.S)


def creo_params(raw):
    """ВСЕ параметры модели «как в Creo»: [(имя, тип, значение)] — тип из блока `attributes`.

    Тип берётся по разметке Creo (`value(s_val)` = строка, `value(d_val)` = число и т. д.);
    если разметки нет (сжатый вид) — тип «str». Одно имя = одна запись (первое непустое).
    """
    out = {}
    for m in _RX_ATTR.finditer(raw):
        nm = m.group(1).decode("utf-8", "replace").strip()
        typ = CREO_TYPES.get(m.group(2), "str")
        val = _creo_clean(m.group(3).decode("utf-8", "replace"))
        if nm and val and nm not in out:
            out[nm] = (typ, val)
    for m in _RX_PARAM.finditer(raw):
        nm = m.group(1).decode("utf-8", "replace").strip()
        val = _creo_clean(m.group(2).decode("utf-8", "replace"))
        if nm and val and "\x00" not in val and nm not in out:
            out[nm] = ("str", val)
    return [(nm, t, v) for nm, (t, v) in out.items()]


# таблица семейства: имена исполнений выглядят как <генерик>[-_]<размер>
_RX_INST = re.compile(rb"user_instances|user_visible_name|drv_tbl_ptr")


def family_of(raw, model="", path=""):
    """ТАБЛИЦА СЕМЕЙСТВА из файла ГЕНЕРИКА: [(исполнение, родитель)] — с МНОГОУРОВНЕВОСТЬЮ.

    Читается по блоку `instances_data` / `user_instances` (проверено на DIN912, DIN931, DIN7991,
    O-RING). Имена исполнений — `<модель>[-_]<типразмер>`; у каждого есть свой **родитель**
    (`drv_tbl_ptr`), поэтому таблица бывает **многоуровневой**: `DIN912-M2_5X4` → `DIN912-M2_5`
    → `DIN912`. Пустой список = модель НЕ генерик (обычная деталь).

    🔴 ГРАБЛЯ 28.10.2026 (стоп-лист эстафеты п.2): исполнения пишутся СБОРКАМ (15 937) и
    ЧЕРТЕЖАМ (11 490). Исполнение — это ВИРТУАЛЬНЫЙ вариант ВНУТРИ файла генерика; таблица
    семейства живёт во `.prt` (скилл `SKILL_creo_read_family.md` §5: настоящие модели семейств —
    590 `.prt.1` / 31 `.asm.1` / 4 `.drw.1`, но исполнения библиотечного крепежа — детали).
    Причина ошибки — та же, что в грабле 3: имя модели-генерика ВСТРЕЧАЕТСЯ в байтах блока
    `instances_data` чужого файла, и `re.finditer` по всему `raw` ловил совпадение. Проверка типа
    файла закрывает канал: НЕ деталь (`.prt`) → таблицы семейства не пишем.
    `path` пуст (старые вызовы/пробники) → проверку не применяем, поведение прежнее.

    Возвращает [(instance, parent)]: parent = '' для верхнего уровня.
    """
    if path and not is_part_file(path):
        return []
    if not model or not _RX_INST.search(raw):
        return []
    # 1) собираем пары «имя → родитель» из блока instances_data.
    # ЗАМЕР (DIN912): запись выглядит так —
    #   user_visible_name\x00…<ИМЯ>\x00\xe1\xe1\xe1\xe1\xe1…<РОДИТЕЛЬ>\x00
    # имена идут парами: `DIN912-M2_5` → `DIN912-M`, `DIN912-M2_5X4` → `DIN912-M2_5`
    # (то есть таблица МНОГОУРОВНЕВАЯ). Имя и родитель разделены `\xe1\xe1\xe1\xe1\xe1`.
    pairs = {}
    blk = raw
    i = raw.find(b"instances_data")
    if i >= 0:
        blk = raw[i:i + 400000]          # блок таблицы (дальше уже геометрия)
    base = re.escape(model.encode("utf-8", "replace"))
    for m in re.finditer(rb"\xe3\x02(" + base + rb"[-_][A-Za-z0-9_\-\.]{1,30})\x00"
                         rb"\xe1\xe1\xe1\xe1\xe1"           # разделитель «имя | родитель»
                         rb".{0,20}?\xe3\x02(" + base + rb"[-_A-Za-z0-9\.]{1,30})\x00", blk, re.S):
        nm = _creo_clean(m.group(1).decode("utf-8", "replace"))
        par = _creo_clean(m.group(2).decode("utf-8", "replace"))
        if nm and nm != model:
            pairs[nm] = par
    # 2) все имена (на случай, если иерархию не разобрали) — родитель = генерик
    seen, out = set(), []
    for m in re.finditer(base + rb"[-_][A-Za-z0-9_\-\.]{1,30}", raw):
        s = _creo_clean(m.group(0).decode("utf-8", "replace"))
        if s and s != model and s not in seen:
            seen.add(s)
            out.append((s, pairs.get(s, model)))
    return out


def search_params(words, limit=500):
    """V125: ПОИСК ПО ПАРАМЕТРАМ (таблица `params`): модель, у которой параметр содержит слово.

    Владелец: «искать по имени файла + по всем параметрам моделей и сборок + исполнениям».
    Ищем по `params.value` И `params.name` (например «ГОСТ 11738» найдёт деталь, у которой
    параметр NAME_2 = 'ГОСТ 11738-72', даже если имя файла нечитаемое). Возвращает список
    словарей {model, path, name, type, value}.
    """
    ws = [w for w in (words or []) if w]
    if not ws:
        return []
    try:
        con = connect(ro=True)
    except Exception:                  # noqa: BLE001
        return []
    try:
        conds, args = [], []
        for w in ws:
            like = "%" + w + "%"
            conds.append("(value LIKE ? OR name LIKE ? OR model LIKE ?)")
            args += [like, like, like]
        sql = ("SELECT DISTINCT model, path, name, type, value FROM params WHERE "
               + " AND ".join(conds) + " ORDER BY model LIMIT ?")
        return [{"model": r[0], "path": r[1], "name": r[2], "type": r[3], "value": r[4]}
                for r in con.execute(sql, args + [int(limit)])]
    except Exception:                  # noqa: BLE001
        return []
    finally:
        try:
            con.close()
        except Exception:              # noqa: BLE001
            pass


def model_params(path_or_model, limit=2000):
    """V132: ВСЕ параметры модели — [(имя, тип, значение)] для карточки/окна.

    ГЛАВНАЯ ГРАБЛЯ (владелец: «где мои параметры? висит твой паспорт»): параметры в БОЕВОЙ
    базе лежат в `arch_dims` (`{model, arch_date, dims}` = JSON `{"d26": 27.19, ...}`) и в
    `arch_dim_ch` (история). Таблица `params` создаётся только НОВЫМ сканом — в старой базе
    её НЕТ, и окно показывало «параметров нет». Теперь читаем ОБА источника:
      1) `arch_dims` по ИМЕНИ модели (как HTML) — основной путь;
      2) таблицу `params` по ПУТИ (если база собрана новым сканом) — как дополнение.
    `path_or_model` принимает И путь файла, И имя модели (что дали — то и ищем).
    """
    try:
        con = connect(ro=True)
    except Exception:                  # noqa: BLE001
        return []
    out = []
    seen = set()
    # Стем модели (как `_norm` в plm_graph): `din912-m4x20.prt.1` -> `DIN912-M4X20`.
    # В engine своей `_norm` нет — считаем здесь, чтобы не тянуть plm_graph (цикл импортов).
    def _stem(x):
        s = str(x or "").strip()
        low = s.lower()
        for suf in (".prt.", ".asm.", ".prt", ".asm", ".drw."):
            i = low.find(suf)
            if i > 0:
                return s[:i].upper()
        return s.upper()

    try:
        # 1) arch_dims: параметры по ИМЕНИ модели (JSON-словарь)
        mdl = _stem(str(path_or_model).split("\\")[-1])
        try:
            row = con.execute("SELECT dims FROM arch_dims WHERE model=? "
                              "ORDER BY arch_date DESC LIMIT 1", (mdl,)).fetchone()
            if row and row[0]:
                d = json.loads(row[0])
                if isinstance(d, dict):
                    for k, v in list(d.items())[:int(limit)]:
                        kk = str(k)
                        if kk in seen:
                            continue
                        seen.add(kk)
                        out.append((kk, "число" if isinstance(v, (int, float)) else "строка", v))
        except Exception:              # noqa: BLE001
            pass
        # 2) params: полный набор от нового скана (по пути, затем по имени)
        for col, val in (("path", path_or_model), ("model", mdl)):
            if len(out) >= int(limit):
                break
            try:
                for r in con.execute(
                        "SELECT name, type, value FROM params WHERE %s=? ORDER BY name LIMIT ?"
                        % col, (val, int(limit))):
                    if r[0] in seen:
                        continue
                    seen.add(r[0])
                    out.append((r[0], r[1], r[2]))
            except Exception:          # noqa: BLE001 — таблицы params может не быть
                pass
        return out[:int(limit)]
    finally:
        try:
            con.close()
        except Exception:              # noqa: BLE001
            pass


def model_family(model, limit=5000):
    """V127: СЕМЕЙСТВО модели: исполнения (со СВОИМ родителем — таблица бывает многоуровневой)
    и родитель самой модели (если она исполнение).

    Возвращает {"children": [(исполнение, родитель)], "parent": ""}. Владелец: «связи
    фемили-линкс» + «есть многоуровневые таблицы семейств» — поэтому отдаём и РОДИТЕЛЯ каждого
    исполнения, а не плоский список.
    """
    try:
        con = connect(ro=True)
    except Exception:                  # noqa: BLE001
        return {"children": [], "parent": ""}
    try:
        kids = [(r[0], r[1]) for r in con.execute(
            "SELECT instance, generic FROM family WHERE generic=? ORDER BY instance LIMIT ?",
            (model, int(limit)))]
        par = con.execute("SELECT generic FROM family WHERE instance=? LIMIT 1",
                          (model,)).fetchone()
        return {"children": kids, "parent": (par[0] if par else "")}
    except Exception:                  # noqa: BLE001
        return {"children": [], "parent": ""}
    finally:
        try:
            con.close()
        except Exception:              # noqa: BLE001
            pass


# --- V126: ИСТОРИЯ ПРАВОК «КТО И КОГДА» — КОМПЬЮТЕР + ПОЛЬЗОВАТЕЛЬ + ВРЕМЯ --------------------
# Владелец: «+ что когда правилось и кем (имя компьютера + юзер)».
#
# РАЗВЕДАНО НА ЖИВЫХ ФАЙЛАХ (G11738.prt.1): Creo пишет в файл КАЖДУЮ запись истории:
#   полный вид:  user_name\x00\xf1USER\x00\xe0\x00modif_time\x00\xe2
#                tm_sec\x00<1б> tm_min\x00<1б> tm_hour\x00<1б> tm_mday\x00<1б> tm_mon\x00<1б> tm_year\x00<1б>
#                typed_data(<ВИД>)\x00\xf1\xe3 rev_string\x00<НОМЕР>\x00
#                comment\x00<UTF-8>"Наименование компьютера: '<КОМПЬЮТЕР>'"\x00 Proe_version\x00<"Creo X.Y.Z">
#   сжатый вид:  \xf7\x14USER\x00\xe2 <sec><min><hour><mday><mon><year>   (6 байт времени)
# ВАЖНО: поле `user_name` почти всегда = служебное «USER»; РЕАЛЬНЫЙ КОМПЬЮТЕР/ПОЛЬЗОВАТЕЛЬ
# лежит в `comment`: «Наименование компьютера: 'Konstruktor-2'» (бывает 'frezer-4', 'Valeriy').
# Год = 1900 + байт, месяц = байт + 1 (проверено: 2026-10-02 11:42:07).
_CREO_PC_MARK = "Наименование компьютера: '".encode("utf-8")
_RX_HIST_FULL = re.compile(
    rb"user_name\x00.{0,4}?\x00\xe0\x00modif_time\x00\xe2"
    rb"tm_sec\x00(.)tm_min\x00(.)tm_hour\x00(.)tm_mday\x00(.)tm_mon\x00(.)tm_year\x00(.)"
    rb".{0,40}?(?:rev_string\x00(.{0,12}?)\x00)?"
    rb".{0,200}?" + re.escape(_CREO_PC_MARK) + rb"([^']{0,60})'"
    rb".{0,60}?Proe_version\x00([^\x00]{0,20})", re.S)
_RX_HIST_SHORT = re.compile(rb"\xf7\x14([\x20-\x7e]{1,24}?)\x00\xe2"
                            rb"(.)(.)(.)(.)(.)(.)")


def creo_history(raw):
    """ИСТОРИЯ ПРАВОК из файла Creo: [{user, computer, creo, ts, rev, action}] — КАК В CREO.

    Владелец: «что когда правилось и кем (имя компьютера + юзер)». Берём ВСЕ записи журнала.
    ЗАМЕР на G11738: коротких времён (каждая операция) — 4833, а «компьютер» (`comment`) — лишь 9
    (Creo пишет компьютер ТОЛЬКО при сохранении модели, `typed_data(MdlStored)`). Поэтому
    компьютер привязываем к БЛИЖАЙШЕМУ времени ПЕРЕД ним по позиции в файле, а не по индексу.
    """
    events = []          # (позиция, вид, данные)
    # V126: между полями времени стоит разделитель `\xe0\x01` (проверено на живом файле:
    # `tm_sec\x00\x07\xe0\x01tm_min\x00\x2a…`) — БЕЗ него шаблон не находил НИ ОДНОГО времени,
    # и все «компьютеры» прилипали к единственной пустой записи.
    for m in re.finditer(rb"tm_sec\x00(.)\xe0\x01tm_min\x00(.)\xe0\x01tm_hour\x00(.)"
                         rb"\xe0\x01tm_mday\x00(.)\xe0\x01tm_mon\x00(.)\xe0\x01tm_year\x00(.)",
                         raw, re.S):
        sec, mi, h, d, mo, y = (b[0] for b in m.groups())
        events.append((m.start(), "t", (sec, mi, h, d, mo, y)))
    for m in _RX_HIST_SHORT.finditer(raw):
        sec, mi, h, d, mo, y = (b[0] for b in m.groups()[1:7])
        events.append((m.start(), "t", (sec, mi, h, d, mo, y)))
    # V126: компьютер + версия Creo. Формат записи (проверено):
    #   \xf7\x14USER\x00\xe2<6 байт времени>\xe3<rev>\x00 … \x00<"Наименование компьютера: 'X'">\x00Creo <ver>
    # поэтому компьютер относим к ПОСЛЕДНЕЙ записи времени ПЕРЕД ним (а не по индексу).
    for m in re.finditer(re.escape(_CREO_PC_MARK) + rb"([^']{0,60})'\x00([^\x00]{0,24})", raw, re.S):
        events.append((m.start(), "pc", (m.group(1).decode("utf-8", "replace").strip(),
                                         m.group(2).decode("utf-8", "replace").strip())))
    for m in re.finditer(rb"rev_string\x00(.{0,12}?)\x00", raw):
        events.append((m.start(), "rev", m.group(1).decode("utf-8", "replace").strip()))
    events.sort(key=lambda x: x[0])

    out, last_ts = [], ""
    for _pos, kind, data in events:
        if kind == "t":
            sec, mi, h, d, mo, y = data
            try:
                dt = datetime.datetime(1900 + y, mo + 1, d, h, mi, sec)
            except ValueError:
                continue
            if not (1990 <= dt.year <= 2040):
                continue
            last_ts = dt.strftime("%d.%m.%Y %H:%M:%S")
            out.append({"user": "USER", "computer": "", "creo": "", "ts": last_ts,
                        "rev": "", "action": ""})
        elif kind == "pc":
            comp, creo = data
            # компьютер относится к ПОСЛЕДНЕЙ записи времени (сохранение модели)
            if out:
                out[-1]["computer"] = comp
                out[-1]["creo"] = creo
            else:
                out.append({"user": "USER", "computer": comp, "creo": creo,
                            "ts": last_ts, "rev": "", "action": ""})
        elif kind == "rev":
            if out:
                out[-1]["rev"] = data
    return out


def model_history(model, limit=500):
    """V126: ИСТОРИЯ ПРАВОК модели из базы: [{ts, user, computer, creo, rev}] — «кто и когда».

    Владелец: «+ что когда правилось и кем (имя компьютера + юзер)». Берём из таблицы `history`
    (её наполняет скан из файла: `user_name`, «Наименование компьютера: 'X'», `modif_time`,
    `Proe_version`). Возвращает свежие записи последними.
    """
    try:
        con = connect(ro=True)
    except Exception:                  # noqa: BLE001
        return []
    try:
        return [{"ts": r[0], "user": r[1], "computer": r[2], "creo": r[3], "rev": r[4]}
                for r in con.execute(
                    "SELECT ts, user, computer, creo, rev FROM history WHERE model=? "
                    "ORDER BY rowid DESC LIMIT ?", (model, int(limit)))]
    except Exception:                  # noqa: BLE001
        return []
    finally:
        try:
            con.close()
        except Exception:              # noqa: BLE001
            pass


def who_edited(model, limit=50):
    """V126: КТО правил модель (сводка по компьютерам): [(компьютер, записей, последняя дата)]."""
    try:
        con = connect(ro=True)
    except Exception:                  # noqa: BLE001
        return []
    try:
        return [(r[0], r[1], r[2]) for r in con.execute(
            "SELECT computer, COUNT(*), MAX(ts) FROM history WHERE model=? AND computer != '' "
            "GROUP BY computer ORDER BY COUNT(*) DESC LIMIT ?", (model, int(limit)))]
    except Exception:                  # noqa: BLE001
        return []
    finally:
        try:
            con.close()
        except Exception:              # noqa: BLE001
            pass


# --- V127: ЗДОРОВЬЕ ФАЙЛА CREO (регенерация, статус модели, «не использовать») ---------------
# Владелец: «Нужно знать историю и ЗДОРОВЬЕ файлов крео». Разведано в файлах (DIN912, G11738,
# DIN931, O-RING): `reg_status` (флаг регенерации: `\x00` = ок, иное = требует регенерации),
# `MdlStatus`/`Sld_MdlStatus` (статус модели), `mdl_geom_rev` (ревизия геометрии),
# `inactive_geom` («не использовать» — неактивная геометрия).
_RX_REG = re.compile(rb"reg_status\x00(.)", re.S)


def creo_health(raw):
    """ЗДОРОВЬЕ файла Creo: {regen, reg_status, inactive, geom_rev} — без запуска Creo.

    Владелец: «Нужно знать историю и здоровье файлов крео». Читаем признаки, которые Creo
    пишет в файл: `reg_status` (0 = модель регенерирована, иное = требует регенерации),
    наличие неактивной геометрии (`inactive_geom`), ревизию геометрии (`mdl_geom_rev`).
    """
    out = {"regen": "", "reg_status": "", "inactive": 0, "geom_rev": ""}
    m = _RX_REG.search(raw)
    if m:
        b = m.group(1)[0]
        out["reg_status"] = str(b)
        out["regen"] = "ok" if b == 0 else "требует регенерации"
    elif b"MdlStatus" in raw or b"Sld_MdlStatus" in raw:
        out["regen"] = "статус есть"
    out["inactive"] = len(re.findall(rb"inactive_geom", raw))
    m2 = re.search(rb"mdl_geom_rev\x00(.{0,12}?)\x00", raw, re.S)
    if m2:
        _g = _creo_clean(m2.group(1).decode("utf-8", "replace"))
        # V127: значение бывает «ссылочным» (нечитаемые байты) — берём только печатаемое
        if _g and all(ch.isprintable() for ch in _g):
            out["geom_rev"] = _g
    return out


def model_health(model):
    """V127: ЗДОРОВЬЕ модели из базы: {regen, reg_status, inactive, geom_rev} или {}."""
    try:
        con = connect(ro=True)
    except Exception:                  # noqa: BLE001
        return {}
    try:
        r = con.execute("SELECT regen, reg_status, inactive, geom_rev FROM health WHERE model=? "
                        "LIMIT 1", (model,)).fetchone()
        if not r:
            return {}
        return {"regen": r[0], "reg_status": r[1], "inactive": r[2], "geom_rev": r[3]}
    except Exception:                  # noqa: BLE001
        return {}
    finally:
        try:
            con.close()
        except Exception:              # noqa: BLE001
            pass


def bad_health(limit=500):
    """V127: «БОЛЬНЫЕ» файлы — требуют регенерации. [(model, regen, inactive)] для окна."""
    try:
        con = connect(ro=True)
    except Exception:                  # noqa: BLE001
        return []
    try:
        return [(r[0], r[1], r[2]) for r in con.execute(
            "SELECT model, regen, inactive FROM health WHERE regen != '' AND regen != 'ok' "
            "ORDER BY model LIMIT ?", (int(limit),))]
    except Exception:                  # noqa: BLE001
        return []
    finally:
        try:
            con.close()
        except Exception:              # noqa: BLE001
            pass


def health_summary():
    """V127: СВОДКА здоровья: {total, ok, bad, inactive} — сколько файлов проверено/больны."""
    try:
        con = connect(ro=True)
    except Exception:                  # noqa: BLE001
        return {}
    try:
        total = con.execute("SELECT COUNT(*) FROM health").fetchone()[0]
        ok = con.execute("SELECT COUNT(*) FROM health WHERE regen='ok'").fetchone()[0]
        bad = con.execute("SELECT COUNT(*) FROM health WHERE regen != '' AND regen != 'ok'").fetchone()[0]
        inact = con.execute("SELECT COUNT(*) FROM health WHERE inactive > 0").fetchone()[0]
        return {"total": total, "ok": ok, "bad": bad, "inactive": inact}
    except Exception:                  # noqa: BLE001
        return {}
    finally:
        try:
            con.close()
        except Exception:              # noqa: BLE001
            pass


# --- ЗАМОК СКАНА: один писатель на общую базу (файл рядом с базой) ---
LOCK_FILE = os.path.join(os.path.dirname(DB), "plm.lock")
LOCK_STALE_SEC = 180


def _machine_name():
    """Имя компьютера, сделавшего запись (V110). Windows: COMPUTERNAME; иначе hostname.
    Нужно для колонки «КОМП/ЮЗЕР» в истории файла — автор из паспорта Creo часто пуст."""
    import socket
    return (os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME")
            or socket.gethostname() or "?").strip() or "?"


def _lock_owner():
    import socket
    return {"machine": os.environ.get("COMPUTERNAME") or socket.gethostname(),
            "user": os.environ.get("USERNAME") or os.environ.get("USER") or "?",
            "pid": os.getpid(), "ts": time.time()}


def lock_status():
    """(занят, текст). Нет/битый/протухший замок = свободно."""
    try:
        with open(LOCK_FILE, "r", encoding="utf-8") as f:
            info = json.load(f)
    except Exception:
        return False, ""
    ts = float(info.get("ts") or 0)
    if time.time() - ts > LOCK_STALE_SEC:
        return False, ""                        # протух — владелец, похоже, упал
    return True, "идёт скан на %s с %s (пользователь %s)" % (
        info.get("machine", "?"), time.strftime("%H:%M", time.localtime(ts)), info.get("user", "?"))


def lock_acquire():
    """Атомарно занять замок. (True,'') либо (False, текст «занято»)."""
    try:
        os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
    except Exception:
        pass
    for _ in range(2):
        try:
            with open(LOCK_FILE, "x", encoding="utf-8") as f:
                json.dump(_lock_owner(), f)
            return True, ""
        except FileExistsError:
            busy, txt = lock_status()
            if busy:
                return False, txt
            try:
                os.remove(LOCK_FILE)            # забрать протухший и повторить
            except Exception:
                return False, "замок занят: не удалось отобрать протухший"
        except Exception as e:
            return False, "нет доступа к замку: %s" % e
    return False, "замок занят"


def lock_heartbeat():
    try:
        with open(LOCK_FILE, "w", encoding="utf-8") as f:
            json.dump(_lock_owner(), f)
    except Exception:
        pass


def lock_release():
    try:
        with open(LOCK_FILE, "r", encoding="utf-8") as f:
            mine = int(json.load(f).get("pid") or -1) == os.getpid()
    except Exception:
        mine = True
    if mine:
        try:
            os.remove(LOCK_FILE)
        except Exception:
            pass


# --- ПУБЛИКАЦИЯ: боевая база меняется только целиком и атомарно ---
def _backup_dir():
    """Папка бэкапов — РЯДОМ С БОЕВОЙ БАЗОЙ (не в папке инструмента, если база на складе).

    ГРАБЛЯ 27.10.2026: бэкапы копились в `D:\\...\\plm_reader\\db\\backup`, а боевая база жила
    на складе — при переносе инструмента бэкапы «терялись». Теперь папка считается от ТОЙ базы,
    которую реально читает инструмент (`active_db()`), с запасным вариантом — папка `DB`.
    """
    try:
        live = active_db()
        if live and os.path.isfile(live):
            return os.path.join(os.path.dirname(live), "backup")
    except Exception:                            # noqa: BLE001
        pass
    return os.path.join(os.path.dirname(DB), "backup")


def _rotate_backups(keep=BACKUP_KEEP):
    """Оставить последние `keep` бэкапов базы в db\\backup; старые удалить (best-effort).
    Бэкапы больше не копятся бесконечно (грабля 30.09.2026: db\\backup дорос до 2 ГБ)."""
    try:
        bdir = _backup_dir()
        if not os.path.isdir(bdir):
            return 0
        files = sorted(f for f in os.listdir(bdir)
                       if f.startswith("plm_reader_") and f.endswith(".db"))
        removed = 0
        for old in files[:max(0, len(files) - keep)]:
            try:
                os.remove(os.path.join(bdir, old))
                removed += 1
            except Exception:
                pass
        if removed:
            log("backup: удалено старых копий %d, оставлено %d" % (removed, keep))
        return removed
    except Exception:
        return 0


def _publish(draft, to_mirror=True):
    """Публикация БЕЗ замены файла: пишем НОВЫЙ versioned-файл — открытые файлы на шаре не мешают.

    `to_mirror=False` — НЕ копировать в зеркала (обычный инкрементальный скан: зеркало обновляем
    только после ПОЛНОГО скана, настройка `mirror_full_only`)."""
    import shutil
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    d = _base_dir()
    os.makedirs(d, exist_ok=True)
    # ГДЕ ЖИВЁТ БОЕВАЯ БАЗА. ГРАБЛЯ 27.10.2026 (вторая половина той же ошибки): `DB` берётся из
    # настроек (`db_dir`), а он БЫЛ ПУСТ → `DB` = локальная папка инструмента, а `active_db()`
    # читала БОЕВУЮ на складе. Публикация обновляла ЛОКАЛЬНЫЙ `plm_reader.db`, а читали СКЛАДСКОЙ
    # → «последняя копия» оставалась «памятником» от 05.10, и рассинхрон не лечился никогда.
    # Теперь «последняя копия» пишется РЯДОМ С ТОЙ БАЗОЙ, ОТКУДА ВЗЯТА ОСНОВА (`prev`), — тогда
    # и публикация, и чтение всегда смотрят в ОДНУ папку.
    try:                                         # бэкап текущей активной базы
        prev = active_db()
        if os.path.isfile(prev):
            bdir = _backup_dir()
            os.makedirs(bdir, exist_ok=True)
            shutil.copy2(prev, os.path.join(bdir, "plm_reader_%s.db" % ts))
    except Exception as e:
        log("backup fail: %s" % e)
    _rotate_backups()                            # окно последних N бэкапов (не копим бесконечно)
    ver = os.path.join(d, "plm_reader_%s.db" % ts)
    shutil.copy2(draft, ver)                     # НОВЫЙ файл — существующее не заменяем
    log("publish: новая база %s" % ver)
    # «ПОСЛЕДНЯЯ КОПИЯ» = `plm_reader.db` РЯДОМ С БОЕВОЙ. Атомарная замена (tmp+rename), чтобы
    # читатели не увидели полуфайл. Боевой источник остаётся версионным файлом.
    try:
        live_dir = os.path.dirname(prev) if (prev and os.path.isfile(prev)) else d
        main_db = os.path.join(live_dir, "plm_reader.db")
        tmp_main = main_db + ".tmp%d" % os.getpid()
        shutil.copy2(ver, tmp_main)
        os.replace(tmp_main, main_db)            # атомарная подмена
        log("publish: обновлён %s" % main_db)
    except Exception as e:                       # noqa: BLE001 — открытый файл на шаре не должен рушить скан
        try:
            if os.path.isfile(tmp_main):
                os.remove(tmp_main)
        except Exception:                        # noqa: BLE001
            pass
        log("publish: не удалось обновить %s (%s)" % (main_db, e))
    _rotate(3)
    try:                                         # ЗЕРКАЛА (другой диск): копия свежей базы
        if to_mirror:
            mirror_published(ver)
        else:
            log("mirror: пропущено (зеркало только после полного скана)")
    except Exception as e:
        log("mirror FAIL: %s" % e)               # зеркало не должно рушить уже опубликованный скан
    return ver


def scan_to_base(roots, max_mb=8, limit=120, depth=None, progress_cb=None, stop_cb=None, full=False,
                 param_cfg=None, exclude=None, recurse=None, latest_only=None):
    """СКАН С ЗАЩИТОЙ: замок → скан в ЛОКАЛЬНЫЙ черновик → публикация (бэкап + подмена).

    Боевая база не меняется до успешного завершения; при любом сбое остаётся прежней.
    recurse/latest_only=None → берутся из settings\\settings.json (настройки работают и в CLI).
    """
    import shutil
    import tempfile
    import threading
    if recurse is None or latest_only is None:
        _cfg = _settings_json()
        if recurse is None:
            recurse = bool(_cfg.get("recurse", True))
        if latest_only is None:
            latest_only = bool(_cfg.get("latest_only", True))
    ok, info = lock_acquire()
    if not ok:
        return {"error": info, "busy": True}          # окно покажет «Занято: …»
    stop_hb = threading.Event()

    def _hb():
        while not stop_hb.wait(30):
            lock_heartbeat()

    threading.Thread(target=_hb, daemon=True).start()
    draft = os.path.join(tempfile.gettempdir(), "plm_reader_draft_%d.db" % os.getpid())
    published = False
    try:
        src = active_db()
        # V132 ЗАЩИТА ОТ ПОТЕРИ БАЗЫ (владелец: «а у кого-то уже есть база данных, нужно
        # продолжить её»): скан обязан ПРОДОЛЖАТЬ существующую базу, а не начинать с нуля.
        # Если активная база не найдена (или пустая), а где-то рядом ЕСТЬ непустая база —
        # берём ЕЁ как основу, иначе накопленная история молча обнулилась бы.
        if not (os.path.isfile(src) and os.path.getsize(src) > 0):
            best = None
            for _d in _db_search_dirs():
                try:
                    for _f in os.listdir(_d):
                        if not _f.endswith(".db") or _f.endswith("-journal"):
                            continue
                        _p = os.path.join(_d, _f)
                        try:
                            _sz = os.path.getsize(_p)
                        except Exception:              # noqa: BLE001
                            continue
                        if _sz > 0 and (best is None or os.path.getmtime(_p) > os.path.getmtime(best)):
                            best = _p
                except Exception:                      # noqa: BLE001
                    pass
            if best:
                log("scan: активная база пуста/не найдена → продолжаю с %s" % best)
                src = best
        if os.path.isfile(src) and os.path.getsize(src) > 0:
            shutil.copy2(src, draft)                  # работаем на локальной копии активной базы
            log("scan: база-основа %s (%d МБ)"
                % (os.path.basename(src), os.path.getsize(src) // 1048576))
        else:
            log("scan: база-основа НЕ найдена — скан начнёт новую (истории ещё нет)")
        # правила параметров изменились → принудительно ПЕРЕЧИТАТЬ всё и запомнить подпись
        sig = json.dumps(param_cfg or {}, sort_keys=True, ensure_ascii=False) + "|" + PARSER_TAG
        eff_full = bool(full)
        try:
            c0 = connect(db=draft)
            try:
                r0 = c0.execute("SELECT v FROM meta WHERE k='param_sig'").fetchone()
            except Exception:
                r0 = None
            if (r0[0] if r0 else None) != sig:
                eff_full = True
                log("param_sig changed → полный скан")
            c0.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
            c0.execute("INSERT OR REPLACE INTO meta VALUES ('param_sig', ?)", (sig,))
            c0.commit()
            c0.close()
        except Exception:
            pass
        res = do_scan(roots, max_mb, limit, depth, progress_cb, stop_cb, eff_full, db=draft,
                      param_cfg=param_cfg, exclude=exclude, recurse=recurse, latest_only=latest_only)
        _publish(draft, to_mirror=(eff_full or not mirror_full_only()))
        published = True
        res["published"] = True
        return res
    except Exception as e:
        log("scan_to_base ERROR: %s" % e)
        return {"error": str(e), "published": False}
    finally:
        stop_hb.set()
        lock_release()
        if published:
            try:
                if os.path.isfile(draft):
                    os.remove(draft)
            except Exception:
                pass
        else:
            log("draft kept (publish failed): %s" % draft)   # скан не потерян


def inventory(roots, max_mb=8, store=True, max_depth=None):
    """СТРОЕНИЕ СКЛАДА (быстро, секунды): папки/подпапки, файлы, модели — и сразу в базу `folders`.

    Считаем ТРИ разные вещи, чтобы цифры не путались (V35):
      папок  — сколько каталогов обойдено;
      файлов — сколько файлов моделей (.prt/.asm/.drw и копии версий) ЛЕЖИТ на диске;
      изделий— сколько РАЗНЫХ моделей (без дублей версий .1/.2/...): имя без номера версии.
    """
    t0 = time.time()
    rows, folders, files, models = [], 0, 0, 0
    seen_models = set()
    for root in roots:
        root = os.path.abspath(root)
        if not os.path.isdir(root):
            continue
        for dp, dirs, fs in os.walk(root):
            rel0 = os.path.relpath(dp, root)
            d0 = 0 if rel0 == "." else rel0.count(os.sep) + 1
            if max_depth is not None and d0 > max_depth:
                dirs[:] = []
                continue
            folders += 1
            rel = os.path.relpath(dp, root)
            depth = 0 if rel == "." else rel.count(os.sep) + 1
            m = 0
            for f in fs:
                if not MODEL.search(f):
                    continue
                m += 1
                seen_models.add(stem(f))      # без номера версии — изделие одно
            models += m
            files += len(fs)
            rows.append((dp, os.path.dirname(dp), depth, m, len(fs)))
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if store:
        con = connect()
        con.execute("DELETE FROM folders")
        con.executemany("INSERT INTO folders (path,parent,depth,models,files,seen) VALUES (?,?,?,?,?,?)",
                        [(r[0], r[1], r[2], r[3], r[4], now) for r in rows])
        con.commit()
        con.close()
    items = len(seen_models)
    print("строение склада: папок %d · изделий %d (без копий версий) · файлов моделей %d (с копиями версий) "
          "· прочих файлов в папках %d (за %.1f с)%s"
          % (folders, items, models, files - models, time.time() - t0,
             " → в базу folders" if store else ""),
          flush=True)
    return folders, files


def do_scan(roots, max_mb, limit, depth=None, progress_cb=None, stop_cb=None, full=False, db=None,
            param_cfg=None, exclude=None, recurse=True, latest_only=True):
    """Скан в базу `db` (по умолчанию боевая). Обычно зовётся через scan_to_base — в черновик.
    recurse/latest_only — настройки «с подпапками» и «только последние версии» (работают в главном скане)."""
    t0 = time.time()
    roots = as_roots(roots)               # строка-корень = ОДИН корень (иначе обход всего диска)
    lim = float("inf") if (limit or 0) <= 0 else limit      # --limit 0 = без предела по времени
    files_stat = collect_stat(roots, max_mb, depth, exclude, recurse)
    if latest_only:
        files_stat = _filter_latest(files_stat)
    total = len(files_stat)
    codes = {stem(os.path.basename(p)) for p, _, _, _ in files_stat}
    fstems = defaultdict(set)
    for p, _, _, _ in files_stat:
        fstems[os.path.dirname(p)].add(stem(os.path.basename(p)))
    con = connect(db=db)
    prev = {r[0]: r for r in con.execute(
        "SELECT path,volume,material,name,designation,rev,author,revdate,role,size,mtime,created "
        "FROM snapshots")}
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    done = new = mod = skipped = 0
    seen = set()
    seen_der = set()          # модели, у которых связи «из чего» уже почищены (у имени много файлов)
    seen_derp = set()         # пары (изделие, основа, вид) — чтобы не плодить дубли
    n = 0
    stopped = False
    for path, size, mtime, ctime in files_stat:
        if time.time() - t0 > lim:
            break
        if stop_cb and stop_cb():
            stopped = True
            break
        n += 1
        s = stem(os.path.basename(path))
        old = prev.get(path)
        if not full and old and int(old[9] or 0) == size and abs(float(old[10] or 0) - mtime) < 1.0:
            skipped += 1                     # НЕ изменился (размер+время) — НЕ читаем и не трогаем
            if old[11] is None or float(old[11] or 0) <= 0:   # дозаполнить «Создан» (без чтения файла)
                try:
                    con.execute("UPDATE snapshots SET created=? WHERE path=?", (ctime, path))
                except Exception:
                    pass
            if progress_cb and n % 25 == 0:
                progress_cb(n, total)
            continue
        try:
            it = scan_item(s, path, codes, fstems.get(os.path.dirname(path), set()),
                           **(param_cfg or {}))
        except Exception as e:
            log("ERROR %s: %s" % (path, e))
            continue
        diffs = []
        # V110: ИМЯ КОМПЬЮТЕРА ОБЯЗАТЕЛЬНО. Автор из паспорта Creo часто пуст или служебный
        # («USER», «ADMIN») — тогда владельцу непонятно, «кто». Подставляем машину, сделавшую
        # запись: `COMPUTERNAME` (Windows) или hostname. Своё имя НЕ трогаем (реальные ZEH116,
        # FENICS, GORSHKOV сохраняются).
        who_rec = (it["author"] or "").strip()
        if not who_rec or who_rec.upper() in ("USER", "ADMIN", "?"):
            who_rec = _machine_name()
        if old:
            if abs(float(old[1] or 0) - float(it["volume"] or 0)) >= 0.5:
                diffs.append("объём %d→%d" % (old[1] or 0, it["volume"] or 0))
            for key, idx in (("material", 2), ("name", 3), ("designation", 4),
                             ("rev", 5), ("author", 6), ("revdate", 7), ("role", 8)):
                a, b = old[idx] or "", it[key]
                if str(a) != str(b):
                    diffs.append("%s: %s→%s" % (key, a or "-", b or "-"))
            if diffs:
                con.execute("INSERT INTO changes (item,rev,kind,descr,who,ts) VALUES (?,?,?,?,?,?)",
                            (path, it["rev"], "modify", "; ".join(diffs), who_rec, now))
                mod += 1
        else:
            con.execute("INSERT INTO changes (item,rev,kind,descr,who,ts) VALUES (?,?,?,?,?,?)",
                        (path, it["rev"], "new", "первая запись паспорта", who_rec, now))
            new += 1
        # ГЛАВНАЯ ГРАБЛЯ 27.10.2026 — ПОЧЕМУ «СКАН НЕ РАБОТАЛ» (владелец: «скан не работает»).
        # Было `INSERT ... snapshots VALUES (17 знаков ?)` БЕЗ списка колонок. SQLite в такой
        # форме требует значения для ВСЕХ колонок таблицы. А в боевой базе `snapshots` имеет
        # 18 колонок: кто-то (НЕ наш код — в доме 0 вхождений слова `pdata`) добавил колонку
        # `pdata` (склейка «имя | параметры», заполнена у 12 956 из 47 289 записей).
        # Итог: `table snapshots has 18 columns but 17 values were supplied` → скан падал
        # КАЖДЫЙ раз, черновик не публиковался, база не менялась.
        # ТЕПЕРЬ пишем СПИСКОМ КОЛОНОК: скан работает и на базе с чужой колонкой, и без неё,
        # а `pdata` не затирается (её значение остаётся как было — мы её не трогаем).
        con.execute("INSERT OR REPLACE INTO snapshots "
                    "(path,model,folder,size,mtime,volume,material,name,designation,rev,"
                    "author,revdate,role,seen,hist,creo,created) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (it["path"], it["model"], os.path.dirname(path), it["size"], it["mtime"],
                     it["volume"], it["material"], it["name"], it["designation"], it["rev"],
                     it["author"], it["revdate"], it["role"], now, it.get("hist", 0),
                     it.get("creo", ""), ctime))
        # 🔴 V137: пишем ВСЕ родители наследования (`derived_all`: MERGE_BASE_PART + ref_part_tab),
        # а не только первого. Замер 28.10.2026: у `500-55-500-ящик-верх-форма.prt.1` — 5 родителей.
        _dall = list(it.get("derived_all") or [])
        if not _dall and (it.get("base") or ""):
            _dall = [(it.get("base"), it.get("dkind", ""))]        # совместимость: старое поле
        if _dall or it.get("copy_from"):        # изделие ← заготовка/отливка/зеркало/КОПИЯ
            if s not in seen_der:               # у одного имени несколько файлов — чистим ОДИН раз,
                con.execute("DELETE FROM derived WHERE child=? AND source='plm_tree'", (s,))
                seen_der.add(s)                 # иначе последний файл затирал связи предыдущих
            _pairs = list(_dall) + [(it.get("copy_from") or "", "копия")]
            for b, k in _pairs:
                if not b:
                    continue
                bb = stem(b)
                if bb.lower() == (s or "").lower():
                    continue                # «скопирована от себя» (save-as с переименованием) — не связь
                dk = (s, bb, k)
                if dk not in seen_derp:
                    seen_derp.add(dk)
                    con.execute("INSERT INTO derived (child,base,kind,source) VALUES (?,?,?,?)",
                                (s, bb, k, "plm_tree"))
        if s not in seen:                       # связи код-родителя чистим ОДИН раз
            con.execute("DELETE FROM links WHERE parent=? AND source='plm_tree'", (s,))
            seen.add(s)
        # 🔴 ГРАБЛЯ 28.10.2026 (владелец: «у дин912 связей 5»): связи `plm_tree` пишутся по
        # ВХОЖДЕНИЮ ИМЕНИ В БАЙТЫ файла. Для .prt/.drw это ЛОЖЬ: имя другой детали лежит там
        # как ЗНАЧЕНИЕ ПАРАМЕТРА или комментарий, а не как состав. ДОКАЗАНО на живом файле:
        # `din931.prt.1` (3 МБ) содержит `DIN912` 2 раза — внутри `..._DIN912-UNC\x00...`,
        # то есть в ПАРАМЕТРЕ таблицы семейства. Отсюда рождалась «связь» DIN931 → DIN912,
        # и у DIN912 из 5 «связей» реальной была ОДНА (сборка SCREWS_VZ).
        # Состав по вхождению имени бывает ТОЛЬКО у СБОРОК (.asm): там имена компонентов
        # действительно записаны. Для деталей/чертежей канал `plm_tree` не пишем вовсе —
        # настоящий состав даёт `asm_comp` (структура файла).
        is_asm = ".asm" in path.lower()
        if is_asm:
            for child, qty in it["refs"].items():
                if (s, child) in seen:
                    continue
                seen.add((s, child))
                con.execute("INSERT INTO links (parent,child,qty,source) VALUES (?,?,?,?)",
                            (s, child, qty, "plm_tree"))
        else:
            # деталь/чертёж: вхождение имени — не состав. Пишем отдельным источником `mentions`,
            # чтобы данные НЕ терялись (видно в SQL), но в состав/граф по умолчанию не попадали.
            for child, qty in it["refs"].items():
                if (s, child) in seen:
                    continue
                seen.add((s, child))
                con.execute("INSERT INTO links (parent,child,qty,source) VALUES (?,?,?,?)",
                            (s, child, qty, "mentions"))
        # СВЯЗИ ИЗ СТРУКТУРЫ ФАЙЛА (эта сессия): состав .asm и модели .asm-обработки. Идут своим
        # источником `asm_comp`, а «имя по вхождению» остаётся как было (`plm_tree`) — их видно
        # отдельно в SQL, поэтому связь можно ПРОВЕРИТЬ, а не верить ей (грабля «приёмка по строкам»).
        parts = it.get("parts") or []
        if parts:
            con.execute("DELETE FROM links WHERE parent=? AND source='asm_comp'", (s,))
            for child, _role, qty in parts:
                con.execute("INSERT INTO links (parent,child,qty,source) VALUES (?,?,?,?)",
                            (s, child, qty or 1, "asm_comp"))
        # ── V125: ВСЕ ПАРАМЕТРЫ МОДЕЛИ (имя + тип + значение) и ТАБЛИЦА СЕМЕЙСТВА ─────────────
        # Владелец: «хранить как все параметры детали, так и все параметры исполнения, тогда
        # связи будут реальные и выводиться будут без плясок». Пишем по ПУТИ файла (как snapshots).
        cp = it.get("cparams") or []
        con.execute("DELETE FROM params WHERE path=?", (path,))
        for _pn, _pt, _pv in cp:
            con.execute("INSERT INTO params (path,model,name,type,value) VALUES (?,?,?,?,?)",
                        (path, s, _pn, _pt, _pv))
        # ── V135: ЧЕРТЁЖ СТАРЫХ БАЗ ЧИСТИМ, ХОТЯ ПАРТС ПУСТ ────────────────────────────────────
        # Грабля 28.10.2026: в базе уже лежат 25 977 `asm_comp` с родителем-ЧЕРТЕЖОМ (и 11 490
        # `family` у чертежей/сборок). Правило: если файл — НЕ сборка, а в базе у него есть
        # `asm_comp` — снести (иначе мусор живёт вечно: старые строки никуда не исчезают сами).
        if is_drawing_file(path):
            con.execute("DELETE FROM links WHERE parent=? AND source IN ('asm_comp','plm_tree')", (s,))
        fam = it.get("family") or []
        # V135: таблица семейства — ТОЛЬКО у ДЕТАЛИ. У сборок/чертежей сносим и СТАРЫЕ строки
        # (в базе их 15 937 + 11 490), иначе мусор переживёт перескан: DELETE срабатывает даже
        # при пустом `fam`, а запись — только когда `fam` непустой И файл деталь.
        if not is_part_file(path):
            con.execute("DELETE FROM family WHERE generic=?", (s,))
            con.execute("DELETE FROM links WHERE parent=? AND source='family'", (s,))
            fam = []
        con.execute("DELETE FROM family WHERE generic=?", (s,))
        for _item in fam:
            # V127: family теперь пары (исполнение, РОДИТЕЛЬ) — таблица бывает МНОГОУРОВНЕВОЙ.
            if isinstance(_item, (tuple, list)):
                _inst, _par = _item[0], (_item[1] if len(_item) > 1 else s)
            else:
                _inst, _par = _item, s
            con.execute("INSERT INTO family (generic,instance,params,source) VALUES (?,?,?,?)",
                        (_par or s, _inst, "", "plm_tree"))
        # ── V126: ИСТОРИЯ ПРАВОК (компьютер + юзер + время + Creo) ──────────────────────────
        # Владелец: «+ что когда правилось и кем (имя компьютера + юзер)».
        h2 = it.get("hist2") or []
        con.execute("DELETE FROM history WHERE path=?", (path,))
        for _h in h2:
            con.execute("INSERT INTO history (path,model,ts,user,computer,creo,rev,action) "
                        "VALUES (?,?,?,?,?,?,?,?)",
                        (path, s, _h.get("ts", ""), _h.get("user", ""), _h.get("computer", ""),
                         _h.get("creo", ""), _h.get("rev", ""), _h.get("action", "")))
        # ── V127: ЗДОРОВЬЕ ФАЙЛА (регенерация/статус/неактивная геометрия) ────────────────────
        # Владелец: «Нужно знать историю и ЗДОРОВЬЕ файлов крео». Пишем в meta (одна строка на путь).
        # ── V127: ЗДОРОВЬЕ ФАЙЛА (регенерация/статус/неактивная геометрия) ────────────────────
        # Владелец: «Нужно знать историю и ЗДОРОВЬЕ файлов крео». V135: таблица создаётся в
        # `SCHEMA` (в `connect()`), здесь только ЗАПИСЬ — `CREATE` внутри `try` глотал исключение
        # и таблицы в боевой базе не было вовсе.
        try:
            _hl = creo_health(raw)
            con.execute("INSERT OR REPLACE INTO health (path,model,regen,reg_status,inactive,geom_rev) "
                        "VALUES (?,?,?,?,?,?)",
                        (path, s, _hl.get("regen", ""), _hl.get("reg_status", ""),
                         int(_hl.get("inactive", 0) or 0), _hl.get("geom_rev", "")))
        except Exception:              # noqa: BLE001
            pass
        # ── V127: СВЯЗЬ СЕМЕЙСТВА С СОСТАВОМ (`family` → `links`). ──────────────────────────
        # Владелец: «все пункты наконец доделай, связи фемили-линкс». Генерик показывает свои
        # исполнения в СОСТАВЕ (источник `family`), а исполнение — своего генерика. Так связи
        # «реальные» и видны без «плясок»: DIN912 → 1375 исполнений.
        if fam:
            con.execute("DELETE FROM links WHERE parent=? AND source='family'", (s,))
            for _item in fam:
                _inst = _item[0] if isinstance(_item, (tuple, list)) else _item
                con.execute("INSERT INTO links (parent,child,qty,source) VALUES (?,?,?,?)",
                            (s, _inst, 1, "family"))
        done += 1
        if progress_cb and n % 25 == 0:
            progress_cb(n, total)
        if n % 500 == 0:
            con.commit()            # частичный коммит: база не заперта на весь прогон
            _p = "progress: %d/%d (%.0f%%), %.1f s, изменённых %d" % (
                n, total, 100.0 * n / max(total, 1), time.time() - t0, mod)
            print(_p, flush=True)
            log(_p)
    # --- ИСКЛЮЧЕНИЯ: строки исключённых папок из базы УБИРАЕМ (иначе «исключённое» видно в таблице) ---
    # Фильтр чтения (collect_stat) не даёт читать исключённые папки, но СТАРЫЕ строки из базы не исчезают.
    # Здесь чистим память: файл исключённой папки уходит из snapshots; осиротевшие стволы — из links/derived.
    purged_excl = 0
    if exclude:
        try:
            ex = [str(x).replace("/", "\\").rstrip("\\").lower() for x in exclude if str(x).strip()]

            def _under_excl(p):
                pl = p.lower()
                return any(pl == k or pl.startswith(k + "\\") for k in ex)

            dead = [p for (p,) in con.execute("SELECT path FROM snapshots") if _under_excl(p)]
            if dead:
                dead_stems = {stem(os.path.basename(p)) for p in dead}
                for p in dead:
                    con.execute("DELETE FROM snapshots WHERE path=?", (p,))
                live = {m for (m,) in con.execute("SELECT DISTINCT model FROM snapshots")}
                gone_stems = [s for s in dead_stems if s not in live]
                if gone_stems:
                    q = ",".join(["?"] * len(gone_stems))
                    con.execute("DELETE FROM links WHERE parent IN (%s) OR child IN (%s)" % (q, q),
                                tuple(gone_stems) * 2)
                    con.execute("DELETE FROM derived WHERE child IN (%s) OR base IN (%s)" % (q, q),
                                tuple(gone_stems) * 2)
                purged_excl = len(dead)
                log("scan: убрано из базы строк исключённых папок: %d (осиротевших стволов: %d)"
                    % (len(dead), len(gone_stems)))
        except Exception as e:
            log("scan: чистка исключённых не удалась: %s" % e)
    try:                        # корни скана — чтобы «проверка актуальности» знала, что обходить
        con.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
        con.execute("INSERT OR REPLACE INTO meta VALUES ('roots', ?)", (json.dumps(roots),))
        con.execute("INSERT OR REPLACE INTO meta VALUES ('exclude', ?)", (json.dumps(exclude or []),))
    except Exception:
        pass
    con.commit()
    con.close()
    dt = time.time() - t0
    log("scan: файлов %d, новых %d, изменённых %d, пропущено %d, за %.1f с"
        % (done, new, mod, skipped, dt))
    print("scan: обработано %d из %d | новых %d | изменённых %d | пропущено (без изменений) %d | за %.1f с%s | база %s"
          % (done, total, new, mod, skipped, dt, " | ОСТАНОВЛЕНО" if stopped else "", db or DB))
    return {"done": done, "total": total, "new": new, "mod": mod, "skipped": skipped, "stopped": stopped, "secs": round(dt, 1), "gone": 0, "purged": 0, "excluded": purged_excl, "need": False, "verdict": ""}


def summary():
    """Сколько чего в базе (для окна при старте)."""
    out = {}
    try:
        con = connect()
        for t in ("snapshots", "links", "folders", "changes"):
            try:
                out[t] = con.execute("SELECT COUNT(*) FROM " + t).fetchone()[0]
            except Exception:
                out[t] = 0
        try:
            out["models"] = con.execute("SELECT COUNT(DISTINCT model) FROM snapshots").fetchone()[0]
        except Exception:
            out["models"] = 0
        con.close()
    except Exception:
        out = {}
    return out


def meta_set(k, v):
    con = connect()
    con.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
    con.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (k, v))
    con.commit()
    con.close()


def meta_get(k, default=None):
    try:
        con = connect()
        r = con.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
        con.close()
        return r[0] if r else default
    except Exception:
        return default


def purge_plan(folder=None, keep=2):
    """ПУРГЕ-план ПО ДИСКУ (файлы НЕ трогаются): сколько версий лишних РЕАЛЬНО сейчас.

    Раньше план строился по таблице snapshots — ИСТОРИИ сканов. База хранит старые
    записи о версиях, которых на диске давно нет, поэтому план показывал «лишние»
    (владелец: 661 версия / 676 МБ), а исполнение читало диск и переносило 0
    (расхождение «в плане 661, перенесено 0», найдено 07.10.2026). Хуже: план мог
    отметить ЕДИНСТВЕННУЮ версию файла как лишнюю — её перенос уничтожил бы данные.
    Теперь план и исполнение — ОДИН обход диска (purge_execute dry=True).

    Возвращает: candidates [(путь, байт, модель, версия)], count, bytes, models, keep, kept.
    """
    keep = max(1, int(keep or 1))
    roots = [folder] if folder else (base_roots() or DEFAULT_ROOTS)
    cand, free, groups, kept, missing = [], 0, 0, 0, 0
    for r in roots:
        try:
            rep = purge_execute(r, keep, None, dry=True)
        except Exception:
            continue
        for path, size, ver in rep["лишние"]:
            cand.append((path, size, stem(os.path.basename(path)), ver))
        free += rep["освобождено_байт"]
        groups += rep["групп"]
        kept += rep["оставлено"]
        missing += len(rep["пропущено_с_причиной"])
    cand.sort(key=lambda x: -x[1])
    return {"candidates": cand, "count": len(cand), "bytes": free, "models": groups,
            "keep": keep, "kept": kept, "missing": missing}


def purge_plan_text(plan, limit=400):
    """Текст плана для окна."""
    lines = ["Purge (план ПО ДИСКУ — один обход с исполнением; файлы НЕ трогаются)",
             "изделий %d · оставить по %d новейшие версии · лишних версий %d · освободится %.1f МБ"
             % (plan["models"], plan["keep"], plan["count"], plan["bytes"] / 1048576.0), ""]
    _miss = plan.get("missing", 0)
    if _miss:
        lines.insert(2, "в базе ещё %d записей об уже отсутствующих файлах (перенесены ранее) — пропущены" % _miss)
    for path, size, model, ver in plan["candidates"][:limit]:
        lines.append("%9.1f КБ | v%d | %s" % (size / 1024.0, ver, path))
    if plan["count"] > limit:
        lines.append("... ещё %d" % (plan["count"] - limit))
    return "\n".join(lines)


# --- ПУРГЕ: перенос лишних версий в БЭКАП (встроено; внешний purge_versions не нужен) ---
PURGE_EXTS = {".prt", ".asm", ".drw", ".frm", ".lay", ".sec"}


def version_groups(root):
    """Группы версий Creo-файлов в папке: ({базовое имя: [файлы по возрастанию версии]}, одиночки)."""
    from pathlib import Path
    root = Path(root)
    if not root.exists():
        return {}, []
    fs = sorted([f for f in root.iterdir() if f.is_file()])
    grps, sings, ass = {}, [], set()
    for f in fs:
        if not (re.match(r".+\.\d+$", f.name) or f.suffix.lower() in PURGE_EXTS):
            continue
        if re.search(r"[-_](01|v2|v3)$", f.stem, re.IGNORECASE):
            if f.name not in ass:
                sings.append(f)
                ass.add(f.name)
            continue
        m = re.match(r"^(.*)\.(\d+)$", f.name)
        if m:
            base = m.group(1)
            base_path = root / base
            if base_path.is_file() and base_path.suffix.lower() in PURGE_EXTS:
                grps.setdefault(base, [base_path]).append(f)
            else:
                grps.setdefault(base, []).append(f)
                if f.name not in ass:
                    sings.append(f)
            ass.add(f.name)
            ass.add(base)
    for _b in grps:                      # 07.10.2026: НОВЕЙШАЯ = числовой максимум (иначе
        grps[_b].sort(key=lambda x: _ver_num(x.name.rsplit(".", 1)[-1]))   # ".9" встанет после ".10")
    return grps, sings


def purge_execute(root, keep=2, backup_dir=None, dry=False, items=None):
    """ПЕРЕНЕСЕНИЕ лишних версий в backup_dir (только move, БЕЗ удаления).

    Обход РЕКУРСИВНЫЙ: версии группируются ВНУТРИ каждой папки (Creo держит версии
    рядом), поэтому лишние переносятся и из ПОДПАПОК, а не только из корня.
    dry=True — ТОЛЬКО СЧЁТ, ничего не двигает: тем же обходом строится ПЛАН,
    поэтому план и исполнение разойтись не могут (расхождение «661 / 0», 07.10.2026).
    Возвращает: перенесено, освобождено_байт, пропущено_с_причиной, seconds,
    лишние [(путь,байт,версия)], групп, оставлено.
    """
    import shutil
    from pathlib import Path
    keep = max(1, int(keep or 1))
    root = Path(root)
    backup_dir = Path(backup_dir) if backup_dir else (
        root / "_purge_backup" / datetime.datetime.now().strftime("%Y%m%d"))
    babs = os.path.abspath(str(backup_dir)) + os.sep   # V99: не ходить по самой бэкап-папке
    rep = {"root": str(root), "keep": keep, "dry": bool(dry), "было_версий": 0,
           "перенесено": [], "пропущено_с_причиной": [], "освобождено_байт": 0,
           "seconds": 0.0, "лишние": [], "групп": 0, "оставлено": 0}
    t0 = time.time()
    if items:                                 # 07.10.2026: перенос по ГОТОВОМУ плану — БЕЗ второго обхода
        for _it in items:                     # план даёт 4 поля (путь, байт, ИЗДЕЛИЕ, версия) —
            path, size = _it[0], _it[1]       # берём по индексам, иначе «too many values to unpack»
            x = Path(path)
            try:
                rel = os.path.relpath(str(x.parent), str(root))
                dst_dir = backup_dir if rel == "." else backup_dir / rel
                dst_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(x), str(dst_dir / x.name))
                rep["перенесено"].append("%s->%s" % (x.name, x.name))
                rep["освобождено_байт"] += (size or 0)
            except Exception as e:
                rep["пропущено_с_причиной"].append("%s: %s" % (x.name, e))
        rep["seconds"] = round(time.time() - t0, 2)
        log("purge: %s — перенесено %d (по готовому плану), %.1f МБ, за %.1f с"
            % (root, len(rep["перенесено"]), rep["освобождено_байт"] / 1048576.0, rep["seconds"]))
        return rep
    for dp, dirs, _fs in os.walk(root):
        dirs[:] = [d for d in dirs
                   if d != "_purge_backup"
                   and not (os.path.abspath(os.path.join(dp, d)) + os.sep).lower()
                   .startswith(babs.lower())]      # V99: своя бэкап-папка внутри склада — не чистится
        grps, _ = version_groups(dp)
        for base, members in grps.items():
            rep["групп"] += 1
            rep["было_версий"] += len(members)
            rep["оставлено"] += min(len(members), keep)
            if len(members) <= keep:          # оставляем keep новейших, остальное — в бэкап
                continue
            rel = os.path.relpath(dp, root)
            dst_dir = backup_dir if rel == "." else backup_dir / rel
            for x in members[:-keep]:
                try:
                    sz = x.stat().st_size
                except Exception:
                    sz = 0
                try:
                    ver = int(x.name.rsplit(".", 1)[1])
                except Exception:
                    ver = 0
                rep["лишние"].append((str(x), sz, ver))
                rep["освобождено_байт"] += sz
                if dry:
                    continue
                try:
                    dst_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(x), str(dst_dir / x.name))
                    rep["перенесено"].append("%s->%s" % (x.name, x.name))
                except Exception as e:
                    rep["пропущено_с_причиной"].append("%s: %s" % (x.name, e))
    rep["seconds"] = round(time.time() - t0, 2)
    log("purge%s: %s — лишних %d, перенесено %d, %.1f МБ, за %.1f с"
        % (" (план)" if dry else "", root, len(rep["лишние"]), len(rep["перенесено"]),
           rep["освобождено_байт"] / 1048576.0, rep["seconds"]))
    return rep


def do_check(roots=None, max_mb=8.0, depth=None, exclude=None, latest_only=None, recurse=None):
    """БЫСТРАЯ проверка актуальности базы: обход + stat, БЕЗ чтения файлов.

    Отвечает на вопрос владельца «актуально / нужен скан?». Исключённые папки не обходятся
    и не считаются «пропавшими».

    V118 ГЛАВНАЯ ГРАБЛЯ (вечный цикл «НУЖЕН СКАН»): проверка шла **без** настроек скана —
    не применялся `latest_only` («только последние версии») и `recurse`. Поэтому файлы версий
    `.2/.3/.4` (после Purge / промежуточные) считались «новыми» (476 шт.), хотя скан их
    **сознательно не берёт**. Владелец сканировал — сообщение возвращалось. Теперь проверка
    использует ТЕ ЖЕ правила, что и скан.
    """
    t0 = time.time()
    # правила — как в do_scan: из аргументов, иначе из настроек
    if recurse is None or latest_only is None:
        try:
            import plm_settings
            _cfg = plm_settings.load_settings_file()
        except Exception:
            _cfg = {}
        if recurse is None:
            recurse = bool(_cfg.get("recurse", True))
        if latest_only is None:
            latest_only = bool(_cfg.get("latest_only", True))
    if not roots:
        try:
            roots = json.loads(meta_get("roots") or "null") or DEFAULT_ROOTS
        except Exception:
            roots = DEFAULT_ROOTS
    if exclude is None:
        try:
            exclude = json.loads(meta_get("exclude") or "null") or []
        except Exception:
            exclude = []
    roots = as_roots(roots)          # в базе корни могут лежать СТРОКОЙ — лечим (грабля 29.09)
    # V118: собираем файлы ТЕМИ ЖЕ правилами, что скан (иначе «новые» — это версии, которые
    # скан не берёт, и сообщение «НУЖЕН СКАН» висит вечно).
    files = collect_stat(roots, max_mb, depth, exclude, recurse=bool(recurse))
    if latest_only:
        files = _filter_latest(files)
    con = connect()
    prev = {r[0]: (r[1], r[2]) for r in con.execute("SELECT path,size,mtime FROM snapshots")}
    con.close()
    prev = {p: v for p, v in prev.items() if under_roots(p, roots) and not excluded(p, exclude)}
    # V118: «пропало» не должно требовать скана — но фильтровать prev через _filter_latest НЕЛЬЗЯ:
    # у файла на диске может быть «старший» сосед ТОЛЬКО в базе (его уже нет на диске), и тогда
    # известный файл выглядел «новым» (33 ложных). Поэтому prev берём КАК ЕСТЬ, а rules применяем
    # только к файлам диска (files) — именно так делает скан.
    # ^ строки ВНЕ текущих корней — не «пропало»: база могла собираться по более широкой папке
    found, new, changed, same = set(), 0, 0, 0
    for p, size, mtime, _ctime in files:
        found.add(p)
        old = prev.get(p)
        if old is None:
            new += 1
        elif int(old[0] or 0) == size and abs(float(old[1] or 0) - mtime) < 1.0:
            same += 1
        else:
            changed += 1
    gone_paths = set(prev) - found
    live_models = {stem(os.path.basename(p)) for p in found}
    really_gone = [p for p in gone_paths if stem(os.path.basename(p)) not in live_models]
    purged = len(gone_paths) - len(really_gone)      # старые версии после ПУРГЕ — норма, не тревога
    gone = len(really_gone)
    # V118: «ПРОПАЛО» НЕ ТРЕБУЕТ СКАНА. Владелец: «при старте всегда пишет НУЖЕН СКАН … пропало 584»
    # — и так каждый раз. Причина: `need` включалось и от `gone` (файлы из базы, которых больше нет
    # на диске). Таких записей скан НЕ добавит — он лишь уберёт их из базы, и до скана сообщение
    # висит вечно, раздражая. Скан нужен только когда есть ЧТО ЧИТАТЬ: новые или изменённые файлы.
    need = bool(new or changed)
    verdict = ("НУЖЕН СКАН: новых %d, изменённых %d, пропало %d" % (new, changed, gone)) if need \
        else "АКТУАЛЬНО (скан не нужен)"
    if not need and gone:
        verdict = ("АКТУАЛЬНО (скан не нужен) · устаревших записей (нет на диске): %d "
                   "— уйдут при следующем скане" % gone)
    if purged:
        verdict += " · старые версии после Purge: %d (норма)" % purged
    # V35: models — изделия БЕЗ дублей версий; total — файлы моделей с копиями версий (для отчёта и статуса)
    res = {"total": len(files), "models": len(live_models), "mod": changed, "new": new, "skipped": same,
           "gone": gone, "purged": purged, "need": need, "verdict": verdict, "secs": round(time.time() - t0, 1)}
    msg = ("проверка: изделий %d | файлов моделей с копиями версий %d | без изменений %d | новых %d"
           " | изменённых %d | пропало %d"
           " | старые версии после Purge %d | за %.1f с → %s"
           % (res["models"], res["total"], same, new, changed, gone, purged, res["secs"], verdict))
    print(msg, flush=True)
    log(msg)
    return res


def find_models(text="", limit=300):
    """Список моделей из базы (для выбора в окне): фильтр по части имени."""
    try:
        con = connect()
        if text:
            rows = con.execute("SELECT DISTINCT model FROM snapshots WHERE model LIKE ? "
                               "ORDER BY model LIMIT ?", ("%" + text + "%", limit)).fetchall()
        else:
            rows = con.execute("SELECT DISTINCT model FROM snapshots ORDER BY model LIMIT ?",
                               (limit,)).fetchall()
        con.close()
        return [r[0] for r in rows]
    except Exception:
        return []


def count_models(text=""):
    try:
        con = connect()
        if text:
            n = con.execute("SELECT COUNT(DISTINCT model) FROM snapshots WHERE model LIKE ?",
                            ("%" + text + "%",)).fetchone()[0]
        else:
            n = con.execute("SELECT COUNT(DISTINCT model) FROM snapshots").fetchone()[0]
        con.close()
        return n
    except Exception:
        return 0


def mark_change(item, kind, descr, who=None, rev=""):
    """Записать в журнал правку КОДА/паспорта (kind='code') — чтобы отличать от правок человека.

    V110: `who` по умолчанию — ИМЯ КОМПЬЮТЕРА (владелец: «нужно имя компьютера обязательно»).
    """
    try:
        con = connect()
        con.execute("INSERT INTO changes (item,rev,kind,descr,who,ts) VALUES (?,?,?,?,?,?)",
                    (item, rev, kind, descr, who or _machine_name(),
                     datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        con.commit()
        con.close()
        return True
    except Exception:
        return False


def do_changes_model(model, n=200):
    """Изменения по КОНКРЕТНОЙ модели: по ТОЧНЫМ путям её файлов + записи по имени модели.

    ГРАБЛЯ (07.10.2026, найдено владельцем): искать только `item LIKE '%модель%'` НЕЛЬЗЯ —
    в журнале путь записан СВОИМ регистром (часто строчными: `ал116-2-1_323927.prt.1`), а
    SQLite LIKE складывает регистр только латиницы: кириллица «АЛ…» и «ал…» НЕ совпадают,
    и изменения «пропадали» (по кнопке было видно 2 записи вместо 12). Теперь сначала берём
    точные пути файлов модели из базы и ищем по ним, а имя добавляем в обоих регистрах.
    """
    m = stem(model)
    con = connect()
    paths = [r[0] for r in con.execute("SELECT path FROM snapshots WHERE model=?", (m,))]
    cond, args = ["item = ?"], [m]
    if paths:
        cond.append("item IN (%s)" % ",".join("?" * len(paths)))
        args += paths
    for v in sorted({m, m.lower(), m.upper()}):
        cond.append("item LIKE ?")
        args.append("%" + v + "%")
    rows = con.execute("SELECT ts,kind,rev,who,descr,item FROM changes WHERE (%s) "
                       "ORDER BY id DESC LIMIT ?" % " OR ".join(cond), args + [n]).fetchall()
    con.close()
    print("изменения «%s»: %d  (файлов у изделия: %d)" % (m, len(rows), len(paths)))
    for ts, kind, rev, who, descr, item in rows:
        mark = " [КОД]" if (kind or "").startswith("code") else ""
        fname = "" if item == m else os.path.basename(item or "")
        print("   %s | %-6s%s | рев.%-5s | %-8s | %-26s | %s"
              % (ts, kind or "-", mark, rev or "-", who or "-", fname[:26], descr or "-"))
    try:
        bases = derived_bases(m)
    except Exception:
        bases = []
    print("из чего пересохранено: " + ("; ".join("%s: %s" % (k, b) for b, k in bases)
                                       if bases else
                                       "нет данных (наследования/производной у изделия нет)"))


def base_roots():
    """Верхние папки базы (те, чьего родителя нет в таблице folders)."""
    try:
        con = connect()
        rows = con.execute("SELECT path FROM folders WHERE parent NOT IN "
                           "(SELECT path FROM folders) ORDER BY path").fetchall()
        con.close()
        return [r[0] for r in rows]
    except Exception:
        return []


def folder_children(parent):
    """Подпапки и файлы одной папки — ИЗ БАЗЫ (для ленивого дерева, без обхода диска)."""
    try:
        con = connect()
        subs = [r[0] for r in con.execute(
            "SELECT path FROM folders WHERE parent=? ORDER BY path", (parent,))]
        files = con.execute(
            "SELECT path,designation,name,material,volume,rev,role FROM snapshots "
            "WHERE folder=? ORDER BY path", (parent,)).fetchall()
        con.close()
        return subs, files
    except Exception:
        return [], []


def folder_files_count(folder):
    """Возвращает (всего_папок_рекурсивно, всего_файлов_рекурсивно) для указанной папки."""
    try:
        con = connect()
        like = folder + "\\%"
        a = con.execute("SELECT COUNT(*) FROM folders WHERE path LIKE ?", (like,)).fetchone()[0]
        b = con.execute("SELECT COUNT(*) FROM snapshots WHERE path LIKE ?", (like,)).fetchone()[0]
        con.close()
        return a, b
    except Exception:
        return 0, 0


# Поля поиска = ВСЕ столбцы, которые видно в окне по настройкам (требование владельца 24.10.2026).
# Текст ищется LIKE-ом; числа/даты — приведением к строке (CAST), чтобы «2026» находило и дату.
FILE_COLS = ("path", "designation", "name", "material", "rev", "role", "model",
             "author", "creo", "folder", "revdate")
# Числовые/временные поля — ищем по CAST(... AS TEXT), чтобы слово находило и объём, и записей.
# V106: ЧИСЛА В ПОИСК НЕ БЕРЁМ. Грабля владельца: запрос «170» находил записи по цифрам
# внутри объёма (`CAST(volume AS TEXT) LIKE '%170%'` — «выводит совсем не по фильтру»).
# Числа (объём/записей/даты) ищутся только точным сравнением/диапазоном — см. FILE_NUM_COLS.
FILE_NUM_COLS = ("volume", "hist", "mtime", "created")


def file_search_cols():
    """Колонки поиска: ТОЛЬКО текстовые поля (LIKE). Числа/даты в подстрочный поиск не входят."""
    return ["%s LIKE ?" % c for c in FILE_COLS]


def _like_cond(words, cols=None):
    """«каждое слово встречается в любой из колонок» — фильтр по ВСЕМ словам, что видно в окне.

    `cols` принимает И просто имена колонок (`"model"`), И готовые выражения (`"path LIKE ?"`,
    `"CAST(volume AS TEXT) LIKE ?"`) — V104: раньше смешение давало битый SQL
    (`(model OR designation …)`), из-за чего фильтр вкладки «Дерево» молчал.
    """
    exprs = list(cols) if cols else file_search_cols()
    exprs = [c if "LIKE" in c.upper() else ("%s LIKE ?" % c) for c in exprs]
    conds, params = [], []
    for w in words:
        like = "%" + w + "%"
        conds.append("(" + " OR ".join(exprs) + ")")
        params += [like] * len(exprs)
    return " AND ".join(conds), params


# Строки паспорта, которые отдаёт база (порядок = распаковка в _row_dict).
ROW_SQL = ("path,model,volume,material,name,designation,rev,author,revdate,role,hist,creo,"
           "mtime,created")


def is_drawing_file(path):
    """ЧЕРТЁЖ ли это (`.drw`) — по ПУТИ файла.

    Нужна для проверки типа ПЕРЕД записью связей (грабля 28.10.2026): чертёж не содержит
    компонентов, поэтому `asm_components()` для него обязан вернуть [] ещё до разбора байтов.
    """
    p = (path or "").lower()
    return ".drw." in p or p.endswith(".drw")


def is_part_file(path):
    """ДЕТАЛЬ ли это (`.prt`) — по ПУТИ файла.

    Таблица семейства есть только у деталей-генериков, поэтому `family_of()` для сборок и
    чертежей обязан вернуть [] ещё до разбора байтов.
    """
    p = (path or "").lower()
    return ".prt." in p or p.endswith(".prt")


def _kind_of(path, role):
    """V111: ТИП ФАЙЛА для окна, с РАЗДЕЛЕНИЕМ сборки и мануфактуринга.
    Было: `"Тип": ""` — пусто, и владелец видел «всё — сборка» (в окнах, графах, связях).
    Теперь: `СБОРКА МФГ` (роль MFG) · `СБОРКА` (.asm) · `ДЕТАЛЬ` (.prt) · `ЧЕРТЁЖ` (.drw).
    """
    p = (path or "").lower()
    if (role or "").upper() == "MFG":
        return "СБОРКА МФГ"                      # мануфактуринг (обработка ЧПУ) — ОТДЕЛЬНО от сборки
    if ".asm." in p or p.endswith(".asm"):
        return "СБОРКА"
    if ".prt." in p or p.endswith(".prt"):
        return "ДЕТАЛЬ"
    if ".drw." in p or p.endswith(".drw"):
        return "ЧЕРТЁЖ"
    return ""


def _row_dict(t):
    """Кортеж из ROW_SQL → словарь строки окна (единый вид для окна и поиска)."""
    (p, model, volume, material, name, desig, rev, author, revdate, role, hist, creo,
     mtime, created) = (list(t) + [None] * 14)[:14]
    return {
        "Файл": os.path.basename(p or ""), "Тип": _kind_of(p, role), "Обозначение": desig or "",
        "Наименование": name or "", "Материал": material or "",
        "Объём, мм³": ("%.0f" % volume) if volume else "", "Габарит, мм": "",
        "Роль": role or "", "Родитель": "", "Ревизия": rev or "",
        "Дата": revdate or "", "Пользователь": author or "", "Версия Creo": creo or "",
        "Записей": str(hist or ""), "Создан": _fs_date(created),
        "_created_ts": float(created or 0), "Изменён": _fs_date(mtime),
        "_mtime_ts": float(mtime or 0), "_path": p or "", "_model": model or "",
    }


def search_files(text, limit=3000):
    """Фильтр по ВСЕЙ базе (SQL, не Python): каждое слово — в любом видимом поле паспорта.

    V103: раньше читалась ВСЯ таблица в Python и фильтровалась там (медленно на 40k+ строк);
    теперь фильтр и LIMIT делает SQLite — быстро и масштабируемо.
    """
    words = [w for w in (text or "").split() if w]
    if not words:
        return []
    where, params = _like_cond(words)
    try:
        con = connect(ro=True)
        rows = con.execute(
            "SELECT path,folder,designation,name,material,volume,rev,role FROM snapshots "
            "WHERE %s ORDER BY path LIMIT ?" % where, params + [limit]).fetchall()
        con.close()
        return rows
    except Exception:
        return []


def count_files(text):
    words = [w for w in (text or "").split() if w]
    if not words:
        return 0
    where, params = _like_cond(words)
    try:
        con = connect(ro=True)
        n = con.execute("SELECT COUNT(*) FROM snapshots WHERE %s" % where, params).fetchone()[0]
        con.close()
        return n
    except Exception:
        return 0


def _passport_rank(row):
    """Насколько полон паспорт: важнее всего непустые ревизия и материал, затем имя и обозначение."""
    d, n, mat, _v, rev, _r = (list(row) + [""] * 6)[:6]
    return (1 if rev else 0) + (1 if mat else 0) + (1 if n else 0) + (1 if d else 0)


def _passport_better(new_row, new_mt, old_row, old_mt):
    """Новый паспорт лучше: сначала — полнее; при равной полноте — свежее по времени файла."""
    rn, ro = _passport_rank(new_row), _passport_rank(old_row)
    if rn != ro:
        return rn > ro
    return (new_mt or 0) > (old_mt or 0)


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


def role_of(model):
    """Роль модели: MFG = модельная оснастка; proizv.X/nasled.X = производная/наследование от X."""
    try:
        con = connect()
        r = con.execute("SELECT role FROM snapshots WHERE model=? AND role IS NOT NULL AND role<>'' "
                        "LIMIT 1", (stem(model),)).fetchone()
        con.close()
        return r[0] if r else ""
    except Exception:
        return ""


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
    if path and is_drawing_file(path):
        return []
    m = P_ASM_COMP.search(raw[:400])
    inter = (m.group(1) == b"/" or b"ASSEM_MFG" in raw[:400] or b"ASSEMBLY/CAST" in raw[:400]) \
        if m else (b"ASSEM_MFG" in raw[:400])
    seen, out = {}, []
    for rx in (P_ASM_COMP, P_ASM_D):
        for g in rx.findall(raw):
            nm = g[1].decode("utf-8", "replace") if isinstance(g[1], bytes) else g[1]
            nm = _clean_model_name(nm.encode("utf-8", "replace")) if not nm.isascii() else nm
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


def role_bases(model):
    """Отливка/заготовка из РОЛИ (`proizv.X` / `nasled.X`) — там хранятся реальные имена."""
    r = role_of(model)
    out = []
    for pref in ("proizv.", "nasled."):
        if (r or "").startswith(pref):
            nm = r[len(pref):]
            if nm and not _hash_like(nm) and len(nm) <= 64:
                out.append((nm, "наследование" if pref == "nasled." else "производная"))
    return out


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


def count_tops():
    try:
        con = connect()
        n = con.execute("SELECT COUNT(*) FROM (SELECT DISTINCT parent FROM links WHERE parent NOT IN "
                        "(SELECT DISTINCT child FROM links))").fetchone()[0]
        con.close()
        return n
    except Exception:
        return 0


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


def models_kind(models):
    """Тип модели для графа: {модель: 'ASSEMBLY'|'PART'|'DRAWING'|'ASSEM_MFG'|...} — по расширению.

    V107: графу нужен ТИП узла (деталь/сборка/манифактуринг), чтобы рисовать маркеры Д/С/М/Ч.
    Определяем по расширению пути из базы — БЕЗ чтения файлов (быстро, работает всегда).
    Роль `MFG` (из базы) уточняет: это обработка → мануфактуринг.
    """
    out = {}
    models = [m for m in (models or []) if m]
    if not models:
        return out
    try:
        con = connect(ro=True)
        q = ",".join("?" * len(models))
        for m, p, role in con.execute(
                "SELECT model, path, role FROM snapshots WHERE model IN (%s)" % q, models):
            low = (p or "").lower()
            kind = ("ASSEMBLY" if (".asm." in low or low.endswith(".asm")) else
                    "PART" if (".prt." in low or low.endswith(".prt")) else
                    "DRAWING" if (".drw." in low or low.endswith(".drw")) else "")
            if (role or "").upper() == "MFG" and kind == "ASSEMBLY":
                kind = "ASSEM_MFG"
            # приоритет: сборка/обработка важнее детали и чертежа (у модели бывает .prt и .asm)
            prev = out.get(m, "")
            rank = {"": 0, "DRAWING": 1, "PART": 2, "ASSEMBLY": 3, "ASSEM_MFG": 4}
            if rank.get(kind, 0) > rank.get(prev, 0):
                out[m] = kind
        con.close()
    except Exception:
        return out
    return out


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


_SERVICE_STEMS = None


def _settings_json():
    """Настройки окна (settings\\settings.json) словарём; {} при неудаче."""
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def reset_service_cache():
    """Сбросить кэш служебных стволов (после правки настроек «папки шаблонов»)."""
    global _SERVICE_STEMS
    _SERVICE_STEMS = None


def config_pro_dirs(path=None):
    """ПАПКИ ИЗ `config.pro` Creo — ЕДИНЫЙ источник «служебности» (решение владельца 28.10.2026).

    Владелец: «Давай через конфиг.про тогда работать, но его нужно тогда указать через настройки,
    вместо как раз "Шаблоны" (они уже будут лишними)».

    Читаем опции (замер живого файла `Z:\\PTC\\CREO-START\\START-STD\\config.pro`: 385 строк,
    243 опции, UTF-8 BOM, CRLF):
      * `start_model_dir`  — ПАПКА шаблонов           ⇒ модели служебные;
      * `template_*` (9 опций) — конкретные ФАЙЛЫ шаблонов ⇒ их модели служебные;
      * `pro_library_dir`  — БИБЛИОТЕКА стандартных изделий ⇒ НЕ служебная сама по себе
        (там НАСТОЯЩИЕ модели: крепёж, втулки, кольца), отсеиваются лишь её шаблоны `MM_*`;
      * `pro_format_dir`, `pro_catalog_dir`, `pro_group_dir`, `pro_mf_*_dir` — служебные папки.

    Возвращает (папки_служебные, файлы_шаблонов, папки_библиотек) — списки в нижнем регистре.
    Пусто/нет файла → ([], [], []) — не падаем (грабля §83: не глотать, а сообщить в лог).
    """
    if path is None:
        path = str((_settings_json() or {}).get("config_pro") or "").strip()
    dirs, tpl_files, libs = [], [], []
    if not path or not os.path.isfile(path):
        if path:
            log("config.pro: файл не найден по пути %s — работаю без него" % path)
        return dirs, tpl_files, libs
    raw = b""
    try:
        raw = open(path, "rb").read()
    except Exception as e:                          # noqa: BLE001
        log("config.pro: чтение не удалось (%s)" % e)
        return dirs, tpl_files, libs
    try:
        if raw[:3] == b"\xef\xbb\xbf":              # UTF-8 BOM (у живого файла он есть)
            raw = raw[3:]
        text = raw.decode("utf-8", "replace")
    except Exception:                               # noqa: BLE001
        text = raw.decode("cp1251", "replace")
    # Опция = первое слово строки; значение — остаток (пути Creo пишет с прямыми слэшами).
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("!"):              # `!` — комментарий config.pro
            continue
        parts = s.split(None, 1)
        if len(parts) < 2:
            continue
        key, val = parts[0].strip().lower(), parts[1].strip().strip('"')
        if not val:
            continue
        v = val.replace("/", "\\").rstrip("\\")
        low = v.lower()
        if key == "start_model_dir":
            dirs.append(low)
        elif key.startswith("template_") or key.startswith("mfg_template_dir") or \
                key.startswith("mfg_process_template_dir") or \
                key.startswith("simulation_process_template_dir"):
            tpl_files.append(low)                   # это ФАЙЛ шаблона — отсеиваем по имени файла
            d = os.path.dirname(low)
            if d:
                dirs.append(d)
        elif key == "pro_library_dir":
            libs.append(low)                        # библиотека: модели НАСТОЯЩИЕ — не отсеиваем
        elif key.startswith("pro_format_dir") or key.startswith("pro_catalog_dir") or \
                key.startswith("pro_group_dir") or key.startswith("pro_mf_") or \
                key.startswith("pro_plot_config_dir") or key.startswith("pro_texture"):
            dirs.append(low)
    # Дедупликация с сохранением порядка (одна папка приходит от нескольких опций `template_*`).
    seen = set()
    dirs = [d for d in dirs if not (d in seen or seen.add(d))]
    seen = set()
    tpl_files = [t for t in tpl_files if not (t in seen or seen.add(t))]
    seen = set()
    libs = [l for l in libs if not (l in seen or seen.add(l))]
    return dirs, tpl_files, libs


def service_stems():
    """Стволы СЛУЖЕБНЫХ моделей (шаблоны/библиотеки: папки НАСТРОЙКИ\\ШАБЛОНЫ, TEMPLATE).

    Их связи — мусор: шаблонная деталь/сборка (напр. `MM_PART`, `SBORKA_MFG`) стоит в КАЖДОЙ
    модели, созданной из шаблона, поэтому «входит в 6000 сборок» — ЛОЖЬ. Отсеиваем."""
    global _SERVICE_STEMS
    if _SERVICE_STEMS is not None:
        return _SERVICE_STEMS
    cfg = _settings_json()
    tf = [str(x).strip().lower().replace("/", "\\\\").rstrip("\\")
          for x in (cfg.get("template_folders") or []) if str(x).strip()]
    # 🔴 28.10.2026 (владелец): ГЛАВНЫЙ источник служебных папок — `config.pro` (настройка
    # `config_pro`). Он заменяет настройку «ШАБЛОНЫ»: у Creo там и папка шаблонов, и файлы
    # шаблонов, и библиотека, и форматы/каталог/UDF. Если `config.pro` задан — он ГЛАВНЫЙ,
    # старый список `template_folders` добавляется к нему (совместимость).
    cp_dirs, cp_tpl_files, cp_libs = config_pro_dirs()
    for d in cp_dirs:
        if d not in tf:
            tf.append(d)
    out = {(str(x)).strip().upper() for x in (cfg.get("service_models") or []) if str(x).strip()}
    try:
        con = connect()
        for m, p in con.execute("SELECT DISTINCT model, path FROM snapshots"):
            nm = (m or "").upper()
            pl = (p or "").lower().replace("/", "\\")
            lib = any(pl == l or pl.startswith(l + "\\") for l in cp_libs)   # библиотека — НЕ служебная
            if tf and not lib:
                if any(pl == f or pl.startswith(f + "\\") for f in tf):
                    out.add(nm)
            elif not tf and not lib:
                if "шаблон" in pl or "template" in pl:
                    out.add(nm)
            # ФАЙЛЫ шаблонов из config.pro (template_solidpart и т.п.) — служебные ПО ИМЕНИ ФАЙЛА,
            # даже если лежат не в папке шаблонов.
            if not lib:
                for t in cp_tpl_files:
                    if pl == t or pl == t + ".1" or pl.startswith(t + "."):
                        out.add(nm)
                        break
        con.close()
    except Exception:
        pass
    if cp_dirs or cp_tpl_files:
        log("config.pro: служебных папок %d, файлов шаблонов %d, библиотек %d"
            % (len(cp_dirs), len(cp_tpl_files), len(cp_libs)))
    _SERVICE_STEMS = out
    return out


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


def find_plm_models(text, limit=400):
    """Модели по фильтру (все слова — в ЛЮБОМ видимом поле паспорта, как и в таблице)."""
    words = [w for w in (text or "").split() if w]
    if not words:
        return []
    where, params = _like_cond(words)          # V104: полный набор полей (как в окне/HTML)
    try:
        con = connect()
        models = [r[0] for r in con.execute(
            "SELECT DISTINCT model FROM snapshots WHERE %s ORDER BY model LIMIT ?" % where,
            params + [limit]).fetchall()]
        con.close()
    except Exception:
        return []
    info = models_info(models)                 # счётчики — ОДНИМ пакетом, без запроса на модель
    return [(m, info.get(m, ("",) * 6 + (0, 0))[6], info.get(m, ("",) * 6 + (0, 0))[7])
            for m in models]


def do_tree_up(model, depth=4):
    """Дерево ВХОДИМОСТИ вверх: в какие сборки входит изделие (рекурсивно)."""
    m = stem(model)
    print("ВХОДИМОСТЬ (вверх): «%s»" % m)
    _up(m, depth, 1, set())


def _up(m, depth, level, seen):
    if depth <= 0 or m in seen:
        return
    seen.add(m)
    par = plm_parents(m)
    if not par:
        print("   %s└─ %s  (выше нигде не используется)" % ("   " * level, m))
        return
    for p, q in par:
        print("   %s↑ %s  x%d" % ("   " * level, p, q))
        _up(p, depth - 1, level + 1, seen)


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


def do_full_tree(model, depth=6):
    """ПОЛНОЕ дерево изделия ТЕКСТОМ — ВСЕ связи, а не только состав (печать в консоль/файл).

    Показывает: СОСТАВ ВНИЗ (`links`), ВХОДИМОСТЬ ВВЕРХ (`links`), НАСЛЕДОВАНИЕ и
    ПРОИЗВОДНУЮ (`derived`: заготовка/отливка/отражение), оснастку (роль `MFG`).
    Окно зовёт `full_tree_lines` (там же — клики «сделать корнем» / «весь список»)."""
    for t, _k, _p in full_tree_lines(model, depth):
        print(t)


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


def do_changes(n):
    con = connect()
    rows = con.execute("SELECT ts, item, rev, kind, descr, who FROM changes ORDER BY id DESC LIMIT ?",
                       (n,)).fetchall()
    con.close()
    print("последние изменения (%d):" % len(rows))
    for ts, item, rev, kind, descr, who in rows:
        print("   %s  %-30s rev%-8s %-7s %s" % (ts, item, rev, kind, descr[:70]))


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


# --- АВТООБНОВЛЕНИЕ ЧЕРЕЗ РЕПОЗИТОРИЙ (V31) ---
UPDATE_REPO = "https://raw.githubusercontent.com/fenics555/creo-agent/master/agent/plm_reader/"
UPDATE_MANIFEST = UPDATE_REPO + "version.json"
UPDATE_API = "https://api.github.com/repos/fenics555/creo-agent/contents/agent/plm_reader/"
UPDATE_REF = "?ref=master"
BACKUP_UPDATE_DIR = os.path.join(HERE, "settings", "backup_update")
UPDATE_KEEP = 3


def _ver_num(v):
    """'V31' -> 31 (0, если не разобрать)."""
    try:
        return int(re.sub(r"[^0-9]", "", str(v)) or 0)
    except Exception:
        return 0


def check_updates(timeout=10):
    """Проверить обновление в репозитории. Возвращает dict:
    {ok, local, remote, available, notes, files} или {ok:False, error}.
    Манифест берём через API (ВСЕГДА свежий), raw — резерв: его CDN кэширует надолго."""
    import urllib.request
    data, last = None, ""
    for url, accept in ((UPDATE_API + "version.json" + UPDATE_REF, "application/vnd.github.raw"),
                        (UPDATE_MANIFEST, "")):
        try:
            headers = {"User-Agent": "PLM-Reader"}
            if accept:
                headers["Accept"] = accept
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode("utf-8"))
            break
        except Exception as e:
            last = str(e)
    if data is None:
        return {"ok": False, "error": last, "local": VERSION}
    remote = str(data.get("version") or "")
    return {"ok": True, "local": VERSION, "remote": remote,
            "available": _ver_num(remote) > _ver_num(VERSION),
            "notes": (data.get("notes") or "").strip(),
            "files": data.get("files") or {}}


def _download(url, timeout=15):
    """Скачать: файлы инструмента — сначала через API (ВСЕГДА свежий), затем raw (кэш CDN)."""
    import urllib.request
    urls = [(url, "")]
    if url.startswith(UPDATE_REPO):
        name = url[len(UPDATE_REPO):]
        urls.insert(0, (UPDATE_API + name + UPDATE_REF, "application/vnd.github.raw"))
    last = ""
    for u, accept in urls:
        try:
            headers = {"User-Agent": "PLM-Reader"}
            if accept:
                headers["Accept"] = accept
            req = urllib.request.Request(u, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            last = str(e)
    raise RuntimeError("не удалось скачать %s: %s" % (url, last))


def _sha256_file(path):
    """SHA256 НОРМАЛИЗОВАННОГО содержимого (CRLF->LF) — не зависит от переводов строк."""
    import hashlib
    with open(path, "rb") as f:
        data = f.read().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def _rotate_update_backups(keep=UPDATE_KEEP):
    """Оставить последние `keep` снимков кода в settings\\backup_update; старые удалить."""
    import shutil
    try:
        if not os.path.isdir(BACKUP_UPDATE_DIR):
            return 0
        dirs = sorted(d for d in os.listdir(BACKUP_UPDATE_DIR)
                      if os.path.isdir(os.path.join(BACKUP_UPDATE_DIR, d)))
        removed = 0
        for old in dirs[:max(0, len(dirs) - keep)]:
            try:
                shutil.rmtree(os.path.join(BACKUP_UPDATE_DIR, old))
                removed += 1
            except Exception:
                pass
        if removed:
            log("update: удалено старых снимков %d" % removed)
        return removed
    except Exception:
        return 0


def sync_by_manifest(files, timeout=15):
    """Привести папку к состоянию манифеста: скачать/заменить файлы, лишние — в obsolete\\.
    Возвращает {ok, updated, obsolete, error}. Перед заменой — снимок кода в settings\\backup_update\\<дата>\\."""
    import shutil
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    snap = os.path.join(BACKUP_UPDATE_DIR, stamp)
    obsolete_dir = os.path.join(snap, "obsolete")
    result = {"ok": False, "updated": [], "obsolete": [], "error": "", "warnings": []}
    try:
        os.makedirs(snap, exist_ok=True)
        tmp_dir = os.path.join(snap, "_new")
        os.makedirs(tmp_dir, exist_ok=True)
        for name, want in (files or {}).items():
            if os.path.basename(name) != name:          # без путей — только имена файлов
                continue
            raw = _download(UPDATE_REPO + name, timeout=timeout)
            tmp = os.path.join(tmp_dir, name)
            with open(tmp, "wb") as f:
                f.write(raw)
            if want and _sha256_file(tmp).lower() != str(want).lower():
                # 06.10.2026: НЕ рушим всё обновление из-за устаревшего SHA одного файла
                # (манифест мог отстать от кода) — ставим как есть и предупреждаем.
                result["warnings"].append(name)
                log("update: SHA256 не совпал: %s (ставлю как есть)" % name)
        for name in (files or {}):
            if os.path.basename(name) != name:
                continue
            target = os.path.join(HERE, name)
            if os.path.isfile(target):
                shutil.copy2(target, os.path.join(snap, name))
            shutil.move(os.path.join(tmp_dir, name), target)
            result["updated"].append(name)
        known = set(files or {})
        keep = {"settings", "db", "log", "__pycache__", "version.json"}
        for f in os.listdir(HERE):
            if f in known or f in keep:
                continue
            if not (f.endswith(".py") or f.endswith(".bat") or f.endswith(".md")):
                continue
            os.makedirs(obsolete_dir, exist_ok=True)
            shutil.move(os.path.join(HERE, f), os.path.join(obsolete_dir, f))
            result["obsolete"].append(f)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        _rotate_update_backups()
        # V109: ГЛАВНАЯ ГРАБЛЯ ШАРЫ. `CREO_GRAPH.html` и `CREO_GRAPH_data.js` НЕ идут в git
        # (в .gitignore: собираются на месте) — поэтому после обновления на шаре оставалась
        # СТАРАЯ страница: без новых превью и без истории. Владелец видел «нет картинок».
        # Теперь страница ПЕРЕСОБИРАЕТСЯ сразу после обновления (в фоне, сбои не ломают апдейт).
        try:
            import plm_graph
            if os.path.isfile(os.path.join(HERE, "plm_graph_page.html")):
                result["graph_rebuild"] = True
        except Exception:                            # noqa: BLE001
            result["graph_rebuild"] = False
        log("update: обновлено %d, устаревших %d, снимок %s"
            % (len(result["updated"]), len(result["obsolete"]), snap))
        result["ok"] = True
        return result
    except Exception as e:
        result["error"] = str(e)
        log("update: ОШИБКА %s" % e)
        return result


# --- УБОРКА ТЯЖЁЛЫХ АРХИВНЫХ ТАБЛИЦ (06.10.2026) -------------------------------------------
# Разум: сырой импорт архивных срезов (снимки/правки/карта) занимал ~6,5 млн строк и раздувал
# боевую базу до 3,2 ГБ. ТЕКУЩЕЕ состояние изделий живёт в `snapshots`/`links`/`derived`,
# история правок — в `changes` (kind='архив'). Окну из архива нужны ТОЛЬКО размеры/история
# (`arch_dims`/`arch_dim_ch`). Остальное — сырьё, удаляем.
ARCH_HEAVY = ("arch_snapshots", "arch_changes", "arch_links", "arch_derived", "arch_tools",
              "arch_fixtures", "arch_mfg_items", "arch_diffs", "arch_extra",
              "arch_dwg_links", "arch_runs")
ARCH_KEEP = ("arch_dims", "arch_dim_ch")


def cleanup_archive_tables(do=False):
    """Убрать ТЯЖЁЛЫЕ архивные таблицы, оставив только РАЗМЕРЫ/ИСТОРИЮ (arch_dims/arch_dim_ch).

    do=False — только показать, сколько занимает; do=True — DROP + VACUUM.
    Возвращает {tables, rows, dropped, error}. Не трогает snapshots/links/derived/changes."""
    out = {"tables": [], "rows": 0, "dropped": [], "error": ""}
    try:
        con = connect()
        have = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for t in ARCH_HEAVY:
            if t in have:
                try:
                    out["rows"] += con.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
                    out["tables"].append(t)
                except Exception:
                    pass
        if do and out["tables"]:
            for t in out["tables"]:
                try:
                    con.execute("DROP TABLE IF EXISTS %s" % t)
                    out["dropped"].append(t)
                except Exception:
                    pass
            con.commit()
            try:
                con.execute("VACUUM")
            except Exception as ex:
                out["vacuum_error"] = str(ex)
        con.close()
    except Exception as ex:
        out["error"] = str(ex)
    return out



def main():
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    # Аудит 02.10.2026: CLI обязан видеть те же корни/исключения/порог, что и окно
    _s = {}
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            _s = json.load(f)
    except Exception:
        _s = {}
    _roots, _excl = scan_config(_s)
    _mbv = _s.get("max_size_mb", 24)                   # V86: единое умолчание24; 0 = без ограничения
    _max_mb = float(_mbv) if _mbv not in (None, "") else 24.0
    # V122 ГРАБЛЯ (владелец: «параметры детали задаются ЧЕЛОВЕКОМ, они у всех РАЗНЫЕ»):
    # CLI-скан НЕ передавал правила параметров (`param_cfg`) → `param_sig` записывался как `{}`,
    # и `name`/`designation` собирались ЗАШИТЫМИ правилами БЕЗ склейки владельца:
    # `G11738` получал `name='Винт'` вместо `'Винт ГОСТ 11738-72'` (по правилу `{NAME_1} {NAME_2}`).
    # Поэтому поиск «ГОСТ 11738» ничего не находил. Теперь CLI берёт те же правила, что и окно
    # («Столбцы и параметры…»): `param_designation` / `param_name` / `param_material`.
    _pcfg = {"pdes": _s.get("param_designation"), "pname": _s.get("param_name"),
             "pmat": _s.get("param_material")}
    _pcfg = {k: v for k, v in _pcfg.items() if v}      # пустые не передаём (возьмутся умолчания кода)
    ap = argparse.ArgumentParser(description="PLM Reader " + VERSION)
    ap.add_argument("cmd", choices=["scan", "check", "count", "where", "changes", "tree", "rename-plan"])
    ap.add_argument("model", nargs="?")
    ap.add_argument("new", nargs="?")
    ap.add_argument("--roots", nargs="+", default=None,
                    help="корни скана; по умолчанию — папки сканирования ИЗ НАСТРОЕК")
    ap.add_argument("--limit", type=float, default=120.0)
    ap.add_argument("--max-mb", type=float, default=_max_mb,
                    help="порог размера файла, МБ (по умолчанию из настроек: %s)" % _max_mb)
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--depth", type=int, default=4)
    ap.add_argument("--max-depth", type=int, default=0)
    ap.add_argument("--full", action="store_true", help="перечитать все файлы заново (дозаполнить поля)")
    a = ap.parse_args()
    roots = a.roots or _roots or DEFAULT_ROOTS
    if a.cmd == "scan":
        scan_to_base(roots, a.max_mb, a.limit, (a.max_depth or None), full=a.full, exclude=_excl,
                     param_cfg=_pcfg)
    elif a.cmd == "check":
        do_check(roots if roots != DEFAULT_ROOTS else None, a.max_mb, (a.max_depth or None),
                 exclude=_excl)
    elif a.cmd == "count":
        inventory(roots, a.max_mb, max_depth=(a.max_depth or None))
    elif a.cmd == "where":
        do_where(a.model or "")
    elif a.cmd == "tree":
        do_tree(a.model, a.depth)
    elif a.cmd == "rename-plan":
        do_rename_plan(a.model or "", a.new or "")
    else:
        do_changes(a.n)


if __name__ == "__main__":
    main()


