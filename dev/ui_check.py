# -*- coding: utf-8 -*-
"""Автоприёмка витрины и сервера: детерминированные пробы без браузера."""
import json, re, sys, urllib.request

BASE = "http://127.0.0.1:8765"


def get(p):
    r = urllib.request.Request(BASE + p, headers={"X-Token": ""})
    return urllib.request.urlopen(r, timeout=20).read().decode("utf-8", "ignore")


def main():
    ok = True
    page = get("/")
    checks = [
        ("витрина: один <script>", page.count("<script>") == 1),
        ("витрина: один buildSettings", page.count("function buildSettings") == 1),
        ("витрина: один buildPanel", page.count("function buildPanel") == 1),
        ("витрина: MK содержит model_vision", "'model_vision'" in page),
        ("витрина: опции селектов с value=", '<option value="' in page),
        ("витрина: рендер DETAILS-кнопок", "DETAILS:" in page),
        ("витрина: пространство PDF-РЕЕСТР", "PDF-РЕЕСТР" in page),
    ]
    pan = json.loads(get("/panel"))
    models = pan.get("models") or []
    checks.append(("панель: models непустой список", isinstance(models, list) and len(models) > 0))
    checks.append(("панель: имена моделей атомарны (без склейки)",
                   all(re.match(r"^[A-Za-z0-9_.\-]+:[A-Za-z0-9_.\-]+$", m) for m in models)))
    st = json.loads(get("/status"))
    checks.append(("сервер: blocks >= 32", st.get("blocks", 0) >= 32))
    checks.append(("сервер: tools >= 121", st.get("tools", 0) >= 121))
    keys = [i.get("key") for i in (json.loads(get("/settings")) or {}).get("items", [])]
    checks.append(("настройки: model_vision присутствует", "model_vision" in keys))
    for name, res in checks:
        print("%-45s %s" % (name, "PASS" if res else "FAIL"))
        ok = ok and res
    print("ИТОГ:", "ВСЁ ЗЕЛЁНОЕ" if ok else "ЕСТЬ ПРОВАЛЫ")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())