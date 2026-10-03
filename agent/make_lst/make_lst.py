# -*- coding: utf-8 -*-
"""make_lst.py — сборка боевого файла ограничений параметров дома (`list.lst`).

Класс Р (чистый Python, Creo НЕ нужен). Живая приёмка 23.09.2026: файл, собранный этим кодом,
Creo принимает, ограничения в диалоге «Параметры» работают (проверено на живой сессии).

Что делает:
  1) собирает `list.lst` из таблицы DEFS (ниже) в точном формате дома: cp1251, CRLF,
     между записями ТРИ пустые строки, последняя запись без запятой;
  2) делает БЕКАП прежнего файла (рядом, в папке `_pre`, с меткой времени);
  3) пишет журнал прогона в `D:\\AI\\log\\make_lst\\run_<дата>_<время>.txt`;
  4) `--dry`  — только показать, НЕ писать;
  5) `--from <refs.txt>` — сверить с отчётом чесалки (`creo_comb refs`): какие параметры шаблона
     заданы значениями, есть ли они в ограничениях, совпадают ли значения.

Запуск:
  python make_lst.py                     # записать боевой файл (с бэкапом)
  python make_lst.py --dry               # только показать
  python make_lst.py --from refs.txt     # сверка с шаблонами + запись
  python make_lst.py --target <путь>     # другой файл (для пробы)
"""
import datetime
import os
import re
import shutil
import sys

TARGET = r"Z:\PTC\CREO-START\НАСТРОЙКИ\ФАЙЛЫ_ОГРАНИЧЕНИЙ_ПАРАМЕТРОВ\list.lst"
LOG_DIR = r"D:\AI\log\make_lst"
BACKUP_KEEP = 20        # сколько бэкапов храним в `_pre` рядом с файлом (живая правка 03.10.2026)


def rotate_backups(target, keep=BACKUP_KEEP, log=print):
    """Оставляем `keep` последних бэкапов, остальные убираем — папка `_pre` на Z: иначе копится вечно.
    Удаляются ТОЛЬКО файлы с нашей меткой имени (`<дата>_<время>[_N]_list.lst`)."""
    d = os.path.join(os.path.dirname(target), "_pre")
    if not os.path.isdir(d):
        return 0
    import re
    pat = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{6}(_\d+)?_list\.lst$")
    ours = [os.path.join(d, f) for f in os.listdir(d) if pat.match(f)]
    ours.sort(key=lambda p: (os.path.getmtime(p), p))
    removed = 0
    for p in ours[:-keep] if len(ours) > keep else []:
        try:
            os.remove(p)
            removed += 1
        except Exception:
            pass
    if removed:
        log("бэкапов убрано (старше %d последних): %d" % (keep, removed))
    return removed

# ВАЖНО: PTC_MATERIAL_NAME/PTC_MASTER_MATERIAL сюда НЕ пишем — в шаблоне они ограничены одним
# материалом (STEEL_40X), но в доме есть и другие (STAL_45 и т.д.); глобальное ограничение их бы заблокировало.
DEFS = [
    ("ТИП", "Деталь", [" ", "Деталь", "Сборка", "Стандарт", "Прочие", "Документация",
                       "Материал", "Производство"]),
    ("ТИП2", " ", [" ", "Комплекты", "Технология"]),
    ("ФОРМАТ", "А3", [" ", "-", "А0", "А2", "А3", "А4", "БЧ"]),
    ("РОЛЬ_В_ЛИТЕЙНОЙ_СИСТЕМЕ", " ", [" ", "Литниковая_система", "Модель", "Сборка_ящика",
                                       "Стержень", "Формовочный_объем", "Ящик"]),
]
# ПРИМЕЧАНИЕ (пробы 23.09.2026): пустой вариант дома пишется как ' ' (как в прежнем боевом list.lst).
# Creo НЕ даёт создать ограниченный параметр со значением-пробелом или пустым через API
# (XToolkitNotValid) — только значение из списка; в диалоге «Параметры» пустой вариант выбирается руками.
# Поэтому чесалка такие параметры пропускает и докладывает (или берёт первое значение при --empty-first).


def build():
    """Точный формат дома (из боевого list.lst): строки разделены ТРЕМЯ пустыми,
    последняя запись — без запятой, затем пустые и закрывающая }."""
    lines = ["ND_ParamDefArr_K01 = {"]
    for idx, (name, default, values) in enumerate(DEFS):
        last = (idx == len(DEFS) - 1)
        lines += ["", "", "",
                  "{ Name = %s" % name, "", "", "",
                  "  Type = string", "", "", "",
                  "  Default = '%s'" % default, "", "", "",
                  "  Enum = { %s}" % ", ".join("'%s'" % v for v in values),
                  "", "", "",
                  "}" if last else "},"]
    lines += ["", "", "", "", "}"]
    return "\r\n".join(lines) + "\r\n"
def check_against_refs(refs_path, log):
    """Сверка ограничений с отчётом чесалки (creo_comb refs): строки вида '   ИМЯ = ЗНАЧЕНИЕ'."""
    if not os.path.exists(refs_path):
        log("сверка: файла '%s' нет — пропуск" % refs_path)
        return
    vals = {}
    for ln in open(refs_path, encoding="utf-8", errors="replace"):
        m = re.match(r"^\s{2,}([A-Za-zА-Яа-яЁё_0-9]+)\s*=\s*(.*?)\s*(?:\(из уравнения\))?\s*$", ln)
        if m:
            vals.setdefault(m.group(1), m.group(2))
    log("сверка с шаблоном '%s': параметров прочитано %d" % (os.path.basename(refs_path), len(vals)))
    for name, default, values in DEFS:
        if name not in vals:
            log("   %-24s В ШАБЛОНЕ НЕ НАЙДЕН (ограничение всё равно пишем)" % name)
            continue
        v = vals[name]
        if v and v != default:
            log("   %-24s значение шаблона '%s' != default '%s' — ПРОВЕРИТЬ глазами" % (name, v, default))
        elif v not in values:
            log("   %-24s значение шаблона '%s' НЕ входит в список" % (name, v))
        else:
            log("   %-24s ок (шаблон '%s' есть в списке)" % (name, v))


def _backup_path(target):
    """Путь бэкапа С МЕТКОЙ СЕКУНД и без перезаписи.

    Живая находка 03.10.2026 (аудит): метка была с точностью до МИНУТЫ (`%Y-%m-%d_%H%M`), поэтому два
    прогона в одну минуту писали бэкап в одно и то же имя. Второй затирал первый, и если между ними
    файл правили руками, оригинал исчезал безвозвратно — живая проба: файл 48 байт, после двух
    прогонов в одной минуте в `_pre` лежал один бэкап на 697 байт (уже перезаписанный)."""
    d = os.path.join(os.path.dirname(target), "_pre")
    os.makedirs(d, exist_ok=True)
    base = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    p = os.path.join(d, base + "_list.lst")
    n = 1
    while os.path.exists(p):          # та же секунда — добавляем номер, старый НЕ трогаем
        p = os.path.join(d, "%s_%d_list.lst" % (base, n))
        n += 1
    return p


def write_file(target, text, log=print):
    """Записать файл: бэкап прежнего (в `_pre` рядом), запись в cp1251, проверка чтением.
    Вынесено из main(), чтобы этим пользовалось и окно программы."""
    parent = os.path.dirname(target)
    if parent:
        os.makedirs(parent, exist_ok=True)
    if os.path.exists(target):
        bak = _backup_path(target)
        shutil.copy2(target, bak)
        log("бэкап прежнего файла: %s" % bak)
    with open(target, "wb") as f:
        f.write(text.encode("cp1251"))
    log("записан: %s (%d байт, cp1251)" % (target, os.path.getsize(target)))
    got = open(target, "rb").read().decode("cp1251")
    for name, _, _ in DEFS:
        if ("Name = %s" % name) not in got:
            log("   ПРОВЕРКА: имя %s в файле НЕ найдено!" % name)
    log("проверка чтением: ок (cp1251, %d записей)" % len(DEFS))
    rotate_backups(target, BACKUP_KEEP, log)
    return True


def make_logger(log_dir=LOG_DIR):
    """Журнал прогона: консоль + файл `run_<дата>_<время>.txt`.

    Живая находка 03.10.2026 (аудит): раньше журнал создавался ТОЛЬКО в main(), то есть писала
    только консоль — ОКНО не оставляло следа вовсе (а канон `audit_tools_canon.txt` показывал
    `Log: True`, потому что искал слово 'log' в коде, а не след на диске). Теперь функция общая:
    окно зовёт её же. Имя — с МЕТКОЙ СЕКУНД, иначе два прогона в одну минуту затирают журнал."""
    try:
        os.makedirs(log_dir, exist_ok=True)
        path = os.path.join(log_dir, "run_" + datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S") + ".txt")
    except Exception:
        path = None
    lines = []

    def log(s):
        print(s)
        lines.append(s)
        if path:                       # пишем сразу — след виден, даже если программу прервали
            try:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(s + "\n")
            except Exception:
                pass
    return log, path


def main():
    args = sys.argv[1:]
    target = TARGET
    refs = None
    dry = False
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--dry":
            dry = True
        elif a == "--from" and i + 1 < len(args):
            i += 1
            refs = args[i]
        elif a == "--target" and i + 1 < len(args):
            i += 1
            target = args[i]
        else:
            print("неизвестный ключ: %s" % a)
            print("ключи: --dry | --from <refs.txt> | --target <путь>")
            return 2
        i += 1

    log, logpath = make_logger()
    log("make_lst: цель %s" % target)
    log("режим: %s" % ("СУХОЙ (ничего не пишем)" if dry else "запись + бэкап"))
    try:
        text = build()
    except Exception as e:
        log("НЕ СОБРАН файл: %s" % e)
        return 2
    if refs:
        check_against_refs(refs, log)

    rc = 0
    if dry:
        log("--- содержимое, которое было бы записано ---")
        log(text)
    else:
        try:
            write_file(target, text, log)
        except Exception as e:
            log("НЕ ЗАПИСАН файл: %s" % e)
            return 2
        if not os.path.exists(target):
            log("НЕ ЗАПИСАН файл: цель не появилась на диске: %s" % target)
            rc = 2

    log("готово (%s), журнал: %s" % ("сухой прогон" if dry else "запись выполнена", logpath))
    return rc


if __name__ == "__main__":
    sys.exit(main())