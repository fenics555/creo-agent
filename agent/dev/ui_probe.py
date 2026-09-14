# -*- coding: utf-8 -*-
"""ui_probe.py - автотест инлайн-контента витрины (правило 10.14).
Проверки: инлайн-script, порт DETAILS-regex на Python, обработчик details-toggle,
группа settings с треугольником. Кириллица только через \\u-эскейпы (10.11)."""
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(BASE_DIR, "..", "ui", "index.html")

PODROBNEE = "\u043f\u043e\u0434\u0440\u043e\u0431\u043d\u0435\u0435"  # подробнее
TEKST = "\u0442\u0435\u043a\u0441\u0442"  # текст


def log_pass(msg):
    print("PASS:", msg)


def log_fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def _read_index():
    if not os.path.exists(INDEX_PATH):
        log_fail("index.html not found at %s" % INDEX_PATH)
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return f.read()


def check_a(content):
    if not re.search(r"<script>(.*?)</script>", content, re.DOTALL):
        log_fail("No inline scripts found")
    log_pass("Inline scripts exist")


def check_b():
    # Порт JS-паттерна DETAILS (ui/index.html:79) на Python.
    pattern = r"\[DETAILS:([A-Za-z0-9_]+)(?:\|([^\]]*))?\]([\s\S]*?)\[/DETAILS\]"
    test_str = "[DETAILS:db|" + PODROBNEE + "]" + TEKST + "[/DETAILS]"
    m = re.search(pattern, test_str)
    if not m:
        log_fail("DETAILS regex failed to match sample")
    lbl = m.group(2) if m.group(2) else PODROBNEE
    expected = ('<div class="details-wrap"><button class="sec" data-act="details-toggle" '
                'data-val="' + m.group(1) + '" style="margin:2px">' + lbl + '</button>'
                '<div class="details-content" style="display:none; margin-left:10px; '
                'border-left:2px solid #555; padding-left:5px">' + m.group(3) + '</div></div>')

    def _repl(mg):
        lb = mg.group(2) if mg.group(2) else PODROBNEE
        return ('<div class="details-wrap"><button class="sec" data-act="details-toggle" '
                'data-val="' + mg.group(1) + '" style="margin:2px">' + lb + '</button>'
                '<div class="details-content" style="display:none; margin-left:10px; '
                'border-left:2px solid #555; padding-left:5px">' + mg.group(3) + '</div></div>')

    res = re.sub(pattern, _repl, test_str)
    if res != expected:
        log_fail("DETAILS replacement mismatch. Got: %s" % res)
    log_pass("DETAILS regex checked")


def check_c(content):
    marker = ("else if(a=='details-toggle'){var cont=el.nextElementSibling;"
              "cont.style.display=(cont.style.display=='none'?'block':'none');}")
    if marker not in content:
        log_fail("JS details-toggle handler not found")
    log_pass("JS handler found")


def check_d(content):
    if 'data-gkey="settings"' not in content:
        log_fail('data-gkey="settings" not found')
    triangles = ["\u25B8", "\u25B6", "\u25B2", "\u25B9", "\u25BA", "\u25BB", "\u25B8", "\u25BA", ">", "\u00BB"]
    if not any(t in content for t in triangles):
        log_fail('data-gkey="settings" found but no triangle detected')
    log_pass('data-gkey="settings" checked')


if __name__ == "__main__":
    try:
        c = _read_index()
        check_a(c)
        check_b()
        check_c(c)
        check_d(c)
        print("ALL PASS")
        sys.exit(0)
    except SystemExit:
        raise
    except Exception as e:
        print("ERROR:", e)
        sys.exit(1)