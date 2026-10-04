# -*- coding: utf-8 -*-
"""env_probe.py — живой вызов модуля путей дома (creo_pdf_env), питон в .py-файле."""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"D:\AI\tools\agent\creo_pdf")
OUT = Path(r"D:\AI\tools\agent\postregen_clean\env_probe_out.txt")


def main():
    import creo_pdf_env as E
    data = E.load()
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1)[:2500],
                   encoding="utf-8")
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())