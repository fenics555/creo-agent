# -*- coding: utf-8 -*-
r"""ЕДИНЫЙ ФАЙЛ НАСТРОЕК ИНСТРУМЕНТА CREO PDF (V3).

Один источник правды для путей. Раньше они были зашиты в трёх местах
(creo_pdf.bat, CreoPdf.java, окно) — смена установки Creo означала правку кода.

  --dump              строки  set "CREO_COMMON=..."  (их читает creo_pdf.bat)
  --show              настройки и откуда взят каждый путь
  --set КЛЮЧ=ЗНАЧ    записать значение
  --find-creo         найти установку Creo (реестр → Program Files → папки PTC)
  --find-java         найти javac/java

КЛЮЧИ: creo_install (корень Parametric с parametric.exe), creo_common (…\Common Files),
java_bin, pfcasync_jar, config_pro, work_dir, pdf_out.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CFG_DIR = os.path.join(HERE, "settings")
CFG = os.path.join(CFG_DIR, "creo_pdf_settings.json")
LEGACY = os.path.join(HERE, "gui_settings.json")
SETTINGS_VERSION = 3

ENV_KEYS = {
    "creo_install": "CREO_INSTALL",
    "creo_common": "CREO_COMMON",
    "java_bin": "JAVA_BIN",
    "pfcasync_jar": "PFCA_SYNC",
    "config_pro": "CONFIG_PRO",
    "work_dir": "WORK_DIR",
    "pdf_out": "PDF_OUT",
}


def _reg_install_dir():
    """InstallDir из реестра Windows."""
    try:
        p = subprocess.run(["reg", "query", r"HKLM\SOFTWARE\PTC\PTC Creo Parametric", "/s"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=25)
    except Exception:
        return ""
    for line in (p.stdout or "").splitlines():
        if "REG_SZ" in line and "InstallDir" in line:
            m = re.search(r"REG_SZ\s+(\S.*)$", line)
            if m:
                return m.group(1).strip()
    return ""


def _common_from_install(install):
    r"""…\<install>\Parametric → …\<install>\Common Files (уровнем выше)."""
    if not install:
        return ""
    d = os.path.dirname(os.path.normpath(install))
    return os.path.join(d, "Common Files") if d else ""


def _scan_drives():
    found = []
    for b in (r"C:\Program Files\PTC", r"C:\Program Files (x86)\PTC", r"D:\PTC", r"E:\PTC"):
        if not os.path.isdir(b):
            continue
        try:
            for name in sorted(os.listdir(b)):
                p = os.path.join(b, name)
                if os.path.isfile(os.path.join(p, "Parametric", "bin", "parametric.exe")):
                    found.append(os.path.join(p, "Parametric"))
        except Exception:
            pass
    return found


def find_creo():
    """Возвращает (install_dir, common_files, источник)."""
    ins = _reg_install_dir()
    if ins and os.path.isdir(ins):
        return ins, _common_from_install(ins), "реестр HKLM\\SOFTWARE\\PTC"
    for cand in _scan_drives():
        return cand, _common_from_install(cand), "скан Program Files\\PTC и папок PTC"
    return "", "", "не найдено"
def find_java():
    """Папка с javac.exe: JAVA_HOME → where javac → типовые папки дома."""
    for env in ("JAVA_HOME", "JDK_HOME"):
        v = os.environ.get(env)
        if v and os.path.isfile(os.path.join(v, "bin", "javac.exe")):
            return os.path.join(v, "bin"), "%s=%s" % (env, v)
    try:
        w = subprocess.run(["where", "javac.exe"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=15)
        for line in (w.stdout or "").splitlines():
            line = line.strip()
            if line and os.path.isfile(line):
                return os.path.dirname(line), "where javac"
    except Exception:
        pass
    for cand in (r"D:\AI\Java\bin", r"C:\Program Files\Java\jdk-25\bin",
                 r"C:\Program Files\Eclipse Adoptium\jdk-25\bin"):
        if os.path.isfile(os.path.join(cand, "javac.exe")):
            return cand, "типовой путь"
    return "", "не найдено"


def load():
    for path in (CFG, LEGACY):
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict) and d:
                return d
        except Exception:
            continue
    return {}


def save(data):
    os.makedirs(CFG_DIR, exist_ok=True)
    with open(CFG, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def _valid_common(p):
    r"""Common Files годен, если в нём есть библиотека JLINK x86e_win64\lib\pfcasyncmt.dll."""
    return bool(p) and os.path.isfile(os.path.join(p, "x86e_win64", "lib", "pfcasyncmt.dll"))


def resolve(d):
    """Настройки → фактические пути; пустые ключи достраиваются поиском.
    Указанный вручную путь проверяется: если он негоден, ищем заново и предупреждаем —
    иначе инструмент просто перестал бы работать после смены версии Creo."""
    out = {}
    warnings = []
    ins, common, src = find_creo()
    want_ins = d.get("creo_install") or ""
    want_common = d.get("creo_common") or ""
    if want_ins and _valid_common(_common_from_install(want_ins)):
        out["creo_install"] = want_ins
        out["creo_common"] = _common_from_install(want_ins)
    else:
        if want_ins:
            warnings.append("указанная установка Creo не найдена или не годна: %s — ищу автоматически"
                            % want_ins)
        if want_common and not _valid_common(want_common):
            warnings.append("указанный Common Files не годен: %s — ищу автоматически" % want_common)
        out["creo_install"] = ins
        out["creo_common"] = common
    jb, jsrc = find_java()
    out["java_bin"] = d.get("java_bin") or jb
    local_jar = os.path.join(HERE, "pfcasync.jar")
    out["pfcasync_jar"] = d.get("pfcasync_jar") or (
        local_jar if os.path.isfile(local_jar)
        else os.path.join(out["creo_common"], "text", "java", "pfcasync.jar"))
    out["config_pro"] = d.get("config_pro") or ""
    out["work_dir"] = d.get("work_dir") or ""
    out["pdf_out"] = d.get("pdf_out") or ""
    out["_src"] = {"creo": ("из настроек" if want_ins and not warnings and src else src),
                   "java": jsrc if not d.get("java_bin") else "из настроек"}
    out["_warnings"] = warnings
    return out
def main(argv):
    d = load()
    r = resolve(d)
    if not argv or argv[0] == "--dump":
        # BAT читает эти строки: имя переменной = значение.
        # ВАЖНО: предупреждения НЕ идут через `rem` — bat исполнит `rem` как команду и упадёт
        # на пробелах в тексте. Для bat отдельный режим --warnings, для --show они в вывод.
        for k, var in ENV_KEYS.items():
            print('set "%s=%s"' % (var, r.get(k, "")))
        return 0
    if argv[0] == "--warnings":
        for w in r.get("_warnings", []):
            print("ВНИМАНИЕ: " + w)
        return 0
    if argv[0] == "--show":
        print("файл настроек: " + (CFG if os.path.isfile(CFG) else "(создастся при первом сохранении)"))
        for w in r.get("_warnings", []):
            print("  ! " + w)
        for k, var in ENV_KEYS.items():
            v = r.get(k, "")
            print("  %-14s %-13s = %s" % (k, var, v if v else "(пусто)"))
        print("  источник Creo : " + r["_src"]["creo"])
        print("  источник Java : " + r["_src"]["java"])
        return 0
    if argv[0] == "--set" and len(argv) >= 2:
        kv = argv[1].split("=", 1)
        if len(kv) != 2:
            print("ERR: нужно КЛЮЧ=ЗНАЧ")
            return 1
        key, val = kv[0].strip(), kv[1].strip()
        if key not in ENV_KEYS and key not in ("folder", "limit", "open_pdf", "dup_near",
                                               "del_dups", "del_nomodel"):
            print("ERR: неизвестный ключ %s. Допустимые: %s" % (key, ", ".join(sorted(ENV_KEYS))))
            return 1
        if "\n" in val or "\r" in val:
            print("ERR: значение содержит перенос строки — так путь портится. Укажи в кавычках один путь.")
            return 1
        d["settings_version"] = SETTINGS_VERSION
        d[key] = val
        save(d)
        print("%s = %s  (записано в %s)" % (key, val, CFG))
        return 0
    if argv[0] == "--find-creo":
        ins, common, src = find_creo()
        print("установка Creo: " + (ins if ins else "НЕ НАЙДЕНА"))
        print("Common Files : " + (common if common else "-"))
        print("источник    : " + src)
        if ins:
            exe = os.path.join(ins, "bin", "parametric.exe")
            print("parametric.exe: %s (%s)" % (exe, "есть" if os.path.isfile(exe) else "НЕТ"))
            jar = os.path.join(common, "text", "java", "pfcasync.jar") if common else ""
            if jar:
                print("pfcasync.jar : %s (%s)" % (jar, "есть" if os.path.isfile(jar) else "нет"))
        return 0 if ins else 1
    if argv[0] == "--install-only":
        # ТОЛЬКО путь установки, одной строкой — безопасно класть в настройки и в bat.
        ins, _common, _src = find_creo()
        print(ins)
        return 0 if ins else 1
    if argv[0] == "--find-java":
        jb, src = find_java()
        print("javac.exe в папке: " + (jb if jb else "НЕ НАЙДЕН"))
        print("источник: " + src)
        return 0 if jb else 1
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))