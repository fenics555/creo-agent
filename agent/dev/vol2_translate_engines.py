# -*- coding: utf-8 -*-
r"""vol2_translate_engines — перевод своих движков на канон настроек (Волна 2.2).

Заменяет абсолютные пути data\<имя>_settings.json на <tool>\settings\settings.json
(канон №2 — без абс. путей, настройки в папке инструмента). Создаёт settings\settings.json
из data\<имя>_settings.json. Каждая замена проверяется; затронутое компилируется.
"""
import json
import py_compile
import sys
from pathlib import Path

AGENT = Path(r"D:\AI\tools\agent")
DATA = AGENT / "data"

# (относит. путь, old, new)
EDITS = [
    ("navigator/navigator.py",
     'SETTINGS = Path(r"D:\\AI\\tools\\agent\\data\\navigator_settings.json")',
     'SETTINGS = Path(__file__).resolve().parent / "settings" / "settings.json"'),
    ("drawing_audit/drawing_audit.py",
     'SETTINGS = _AGENT / "data" / "drawing_audit_settings.json"',
     'SETTINGS = _HERE / "settings" / "settings.json"'),
    ("orphan_scan/orphan_scan.py",
     'SETTINGS_PATH = r"D:\\AI\\tools\\agent\\data\\orphan_scan_settings.json"',
     'SETTINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings", "settings.json")'),
    ("config_audit/config_audit.py",
     'SETTINGS_FILE = os.path.normpath(os.path.join(_AGENT, "data", "config_audit_settings.json"))',
     'SETTINGS_FILE = os.path.join(_HERE, "settings", "settings.json")'),
    ("config_audit/gui.py",
     'SETTINGS = Path(r"D:\\AI\\tools\\agent\\data\\config_audit_settings.json")',
     'SETTINGS = Path(__file__).resolve().parent / "settings" / "settings.json"'),
    ("purge_versions/engine.py",
     'SETTINGS_FILE = Path(r"D:\\AI\\tools\\agent\\data\\purge_versions_settings.json")',
     'SETTINGS_FILE = PROG_DIR / "settings" / "settings.json"'),
    ("purge_versions/gui.py",
     'SETTINGS_FILE = Path(r"D:\\AI\\tools\\agent\\data\\purge_versions_settings.json")',
     'SETTINGS_FILE = Path(__file__).resolve().parent / "settings" / "settings.json"'),
    ("postregen_clean/gui.py",
     "saved = U.load_settings(SETTINGS) or {}",
     "saved = U.load_settings(SETTINGS, tool_dir=_HERE) or {}"),
    ("postregen_clean/gui.py",
     "out = U.save_settings(SETTINGS, vals)",
     "out = U.save_settings(SETTINGS, vals, tool_dir=_HERE)"),
]

# имя инструмента -> файл настроек в data\ (источник для settings\settings.json)
SETTINGS_SRC = {
    "navigator": "navigator_settings.json",
    "drawing_audit": "drawing_audit_settings.json",
    "orphan_scan": "orphan_scan_settings.json",
    "config_audit": "config_audit_settings.json",
    "purge_versions": "purge_versions_settings.json",
    "postregen_clean": "postregen_clean_settings.json",
}


def main():
    fails = []
    touched = {}
    for rel, old, new in EDITS:
        p = AGENT / rel
        if not p.exists():
            fails.append("%s: файла нет" % rel)
            continue
        src = p.read_text(encoding="utf-8")
        if old not in src:
            fails.append("%s: якорь не найден: %r" % (rel, old[:48]))
            continue
        p.write_text(src.replace(old, new), encoding="utf-8")
        touched[rel] = True
        print("OK %-32s %s" % (rel, old[:40]))
    # settings\settings.json для каждого движка
    for name, fname in SETTINGS_SRC.items():
        sdir = AGENT / name / "settings"
        sdir.mkdir(parents=True, exist_ok=True)
        oldp = DATA / fname
        data = {}
        if oldp.exists():
            try:
                data = json.loads(oldp.read_text(encoding="utf-8"))
            except Exception as e:
                fails.append("%s: data-настройки: %s" % (name, e))
        (sdir / "settings.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print("OK %-16s settings\\settings.json (%d ключей)" % (name, len(data)))
    # py_compile затронутого
    print("--- py_compile ---")
    for rel in touched:
        try:
            py_compile.compile(str(AGENT / rel), doraise=True)
            print("compile OK %s" % rel)
        except Exception as e:
            fails.append("%s: py_compile: %s" % (rel, e))
    print("--- итог ---")
    if fails:
        print("ОШИБКИ (%d):" % len(fails))
        for f in fails:
            print("  " + f)
        return 1
    print("СВОИ ДВИЖКИ ПЕРЕВЕДЕНЫ, КОМПИЛЯЦИЯ ЧИСТА")
    return 0


if __name__ == "__main__":
    sys.exit(main())
