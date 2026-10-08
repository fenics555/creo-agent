# -*- coding: utf-8 -*-
r"""make_version_json.py — собрать version.json (манифест обновления) рядом с инструментом.

Считает SHA256 всех файлов кода и пишет version.json: версия, номер, дата, заметки, файлы.
Запуск:  python make_version_json.py "кратко: что нового"
Файл version.json кладётся в репозиторий рядом с кодом; программа тянет его по raw-URL.
"""
import datetime
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Что входит в поставку (файлы кода). Всё, чего нет в манифесте, при обновлении уедет в obsolete\.
CODE_FILES = [
    "engine.py", "plm_reader.py", "plm_toolwin.py", "plm_history.py", "plm_parse.py", "plm_dbview.py",
    "plm_settings.py", "creo_read.py", "README.md", "SHARE_copy.bat", "plm_reader.bat",
    "plm_reader_gui.bat", "make_version_json.py", ".gitignore",
]


def sha256(path):
    """SHA256 НОРМАЛИЗОВАННОГО содержимого (CRLF->LF) — хеш не зависит от переводов строк."""
    with open(path, "rb") as f:
        data = f.read().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def current_version():
    """Версия и номер из plm_reader.py (APP_VERSION = \"V31\")."""
    try:
        with open(os.path.join(HERE, "plm_reader.py"), encoding="utf-8") as f:
            for line in f:
                m = re.match(r'\s*APP_VERSION\s*=\s*"V(\d+)"', line)
                if m:
                    return "V" + m.group(1), int(m.group(1))
    except Exception:
        pass
    return "V0", 0


def main():
    ver, num = current_version()
    files = {}
    for name in CODE_FILES:
        p = os.path.join(HERE, name)
        if os.path.isfile(p):
            files[name] = sha256(p)
    manifest = {
        "version": ver,
        "version_num": num,
        "date": datetime.date.today().strftime("%d.%m.%Y"),
        "notes": (sys.argv[1] if len(sys.argv) > 1 else "").strip(),
        "files": files,
    }
    out = os.path.join(HERE, "version.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print("version.json: %s (num=%d), files=%d -> %s" % (ver, num, len(files), out))


if __name__ == "__main__":
    main()
