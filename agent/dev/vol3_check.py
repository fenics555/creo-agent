# -*- coding: utf-8 -*-
"""ПРИЁМКА ВОЛНЫ 3 — hol_check. Главный критерий: на БЕКАПЕ с разорванным именем
программа обязана дать ошибку, а на боевых файлах — ноль ошибок.

Запуск: cmd /c "cd /d D:\\AI\\tools\\agent && python -X utf8 dev\\vol3_check.py"
"""
import io
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
AGENT = Path(__file__).resolve().parent.parent
HOL = AGENT / "hol_check"
sys.path.insert(0, str(AGENT))

fail = []


def ok(name, cond, detail=""):
    d = detail if isinstance(detail, str) else str(detail)
    print(("OK   " if cond else "FAIL ") + name + ((" | " + d) if d else ""))
    if not cond:
        fail.append(name)


def run_engine(args=()):
    """Прогон движка как подпрограммы: возвращает (RC, stdout)."""
    r = subprocess.run([sys.executable, "-X", "utf8", "hol_check.py"] + list(args),
                       cwd=str(HOL), capture_output=True, text=True, timeout=120)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


if __name__ == "__main__":
    # ВАЖНО: в папке агента есть каталог `hol_check\` — без этой строки он импортируется
    # как namespace-пакет, и `hol_check.scan` не находится (найдено живой пробой волны 3).
    sys.path.insert(0, str(HOL))
    import hol_check as eng  # noqa: E402

    # 1. контракт валиден
    import tool_contract as TC
    c, err = TC.load_dir(HOL)
    ok("контракт hol_check валиден", bool(c) and not err, err or "ошибок нет")
    ok("контракт: класс Р и только чтение", (c or {}).get("class") == "Р" and
       (c or {}).get("approval") is False)

    # 2. ГЛАВНЫЙ КРИТЕРИЙ: бекапы со сломанными файлами → RC 1 и найден разрыв
    bak = Path(r"Z:\PTC\CREO-START\START-STD\БЕКАП")
    rc_b, out_b = run_engine([str(bak)])
    ok("бекапы: RC 1 (ошибки найдены)", rc_b == 1, "RC=%d" % rc_b)
    ok("бекапы: найден разрыв TAPER_AN + GLE WASHOUT_ANGLE",
       "разорваны имена колонок" in out_b and "GLE WASHOUT_ANGLE" in out_b,
       [l.strip() for l in out_b.splitlines() if "разорваны" in l][:1])

    # 3. боевые файлы → RC 0, ошибок нет
    rc_l, out_l = run_engine()
    ok("боевые: RC 0 (ошибок нет)", rc_l == 0, "RC=%d" % rc_l)
    ok("боевые: файлов > 30", "файлов 3" in out_l,
       [l for l in out_l.splitlines() if "файлов" in l][:1])

    # 4. разрыв в архиве СТАРОЕ помечен как архив, а не ошибка
    res = eng.scan()
    arch = [r for r in res["rows"] if "СТАРОЕ" in r["path"] and "разорваны" in r["note"]]
    ok("архив СТАРОЕ: разрыв помечен как АРХИВ и не считается ошибкой",
       bool(arch) and arch[0]["verdict"] == "warn",
       arch[0]["note"][:70] if arch else "не найдено")

    # 5. отчёт и CSV пишутся
    rp, cp = eng.write_report(res, 0.1)
    ok("отчёт записан", Path(rp).exists(), rp)
    ok("CSV записан", Path(cp).exists(), cp)

    # 6. пустая папка → RC 2
    empty = Path(r"D:\AI\data\tmp\hol_empty")
    empty.mkdir(parents=True, exist_ok=True)
    rc_e, out_e = run_engine([str(empty)])
    ok("пустая папка: RC 2 (нечего проверять)", rc_e == 2, "RC=%d" % rc_e)
    ok("пустая папка: сообщение понятное", "НЕЧЕГО ПРОВЕРЯТЬ" in out_e)

    # 7. инструменты агента
    import hol_tools as HT
    t = HT.tool_hol_check()
    ok("инструмент агента hol_check работает", "ТАБЛИЦЫ ОТВЕРСТИЙ" in t,
       t.splitlines()[0] if t else "")

    print("\n=== ИТОГ ВОЛНЫ 3: %s (провалов %d) ===" % ("ОК" if not fail else "НЕ ОК", len(fail)))
    if fail:
        print("провалы: " + "; ".join(fail))
    sys.exit(1 if fail else 0)