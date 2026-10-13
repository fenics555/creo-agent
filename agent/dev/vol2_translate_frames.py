# -*- coding: utf-8 -*-
r"""vol2_translate_frames — перевод каркасных окон на канон настроек (Волна 2.2).

Рычаг ui_common.tool_dir готов (Волна 2.1). Этот скрипт переводит окна:
  1. gui.py: U.load_settings/save_settings получают tool_dir=<переменная пути HERE/PROG_DIR>
     -> настройки уезжают в <tool>\settings\settings.json.
  2. Создаёт <tool>\settings\settings.json, копируя данные из data\<имя>_settings.json.
  3. tool.json: "settings" -> "settings/settings.json".
Старые data\<имя>_settings.json НЕ удаляются (п.5 манифеста). Каждая правка проверяется.
"""
import json
import py_compile
import shutil
import sys
from pathlib import Path

AGENT = Path(r"D:\AI\tools\agent")
DATA = AGENT / "data"

# имя -> (переменная пути в gui.py, [(old, new), ...])
FRAMES = {
    "log_clean": ("PROG_DIR", [
        ('return U.load_settings("log_clean", DEFAULTS)',
         'return U.load_settings("log_clean", DEFAULTS, tool_dir=PROG_DIR)'),
        ('out = U.save_settings("log_clean", self.st)',
         'out = U.save_settings("log_clean", self.st, tool_dir=PROG_DIR)'),
    ]),
    "creo_comb": ("HERE", [
        ('return U.load_settings("creo_comb", DEFAULTS)',
         'return U.load_settings("creo_comb", DEFAULTS, tool_dir=HERE)'),
        ('out = U.save_settings("creo_comb", self.st)',
         'out = U.save_settings("creo_comb", self.st, tool_dir=HERE)'),
    ]),
    "excel": ("HERE", [
        ('return U.load_settings("excel", DEFAULTS)',
         'return U.load_settings("excel", DEFAULTS, tool_dir=HERE)'),
        ('out = U.save_settings("excel", {"last_path": p})',
         'out = U.save_settings("excel", {"last_path": p}, tool_dir=HERE)'),
    ]),
}


def main():
    fails = []
    for name, (var, edits) in FRAMES.items():
        gui = AGENT / name / "gui.py"
        if not gui.exists():
            fails.append("%s: нет gui.py" % name)
            continue
        src = gui.read_text(encoding="utf-8")
        for old, new in edits:
            if old not in src:
                fails.append("%s: якорь не найден: %r" % (name, old[:40]))
                continue
            src = src.replace(old, new)
            print("OK %-12s gui.py  %s" % (name, old[:44]))
        gui.write_text(src, encoding="utf-8")

        # settings\settings.json из data\<имя>_settings.json
        sdir = AGENT / name / "settings"
        sdir.mkdir(parents=True, exist_ok=True)
        oldp = DATA / ("%s_settings.json" % name)
        data = {}
        if oldp.exists():
            try:
                data = json.loads(oldp.read_text(encoding="utf-8"))
            except Exception as e:
                fails.append("%s: data-настройки не прочитаны: %s" % (name, e))
        (sdir / "settings.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print("OK %-12s settings\\settings.json (%d ключей из data)" % (name, len(data)))

        # tool.json: settings -> settings/settings.json
        tj = AGENT / name / "tool.json"
        if tj.exists():
            tjs = tj.read_text(encoding="utf-8")
            needle = '"settings": "%s_settings.json"' % name
            if needle in tjs:
                tjs = tjs.replace(needle, '"settings": "settings/settings.json"')
                tj.write_text(tjs, encoding="utf-8")
                print("OK %-12s tool.json settings -> settings/settings.json" % name)
            else:
                fails.append("%s: в tool.json нет %r" % (name, needle))
        try:
            py_compile.compile(str(gui), doraise=True)
            print("compile OK %s" % name)
        except Exception as e:
            fails.append("%s: py_compile: %s" % (name, e))

    print("--- итог ---")
    if fails:
        print("ОШИБКИ (%d):" % len(fails))
        for f in fails:
            print("  " + f)
        return 1
    print("КАРКАСНЫЕ ОКНА ПЕРЕВЕДЕНЫ, КОМПИЛЯЦИЯ ЧИСТА")
    return 0


if __name__ == "__main__":
    sys.exit(main())
