# -*- coding: utf-8 -*-
r"""apply.py - ИСПОЛНЕНИЕ ПЛАНА ПАКЕТНЫХ ПАРАМЕТРОВ (волна 7, класс Ж).

ПРАВИЛА ЖЕЛЕЗА ДЛЯ ЭТОГО ФАЙЛА:
1. Сначала - согласие: без `approve=1` запись не начинается, выводится план и RC 3.
2. Только КОПИЯ: пишем в копию модели, боевые файлы не трогаем (по умолчанию).
3. СТОП: цикл проверяет флаг между моделями; отчёт говорит, где остановились.
4. Нет CREOSON - честный отказ RC 2, а НЕ «прогон успешен».
5. Боевой `config.pro` не правим никогда.

Запись идёт через механизм `set_param` (creo_ops_tools) - доказанный путь в доме.
"""
import io
import json
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_AGENT = _HERE.parent
for _p in (_AGENT, _HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import plan as P   # noqa: E402

# Стоп-флаг между моделями. Кнопка СТОП в окне ставит его в True.
STOP = {"flag": False}


def creoson_alive(timeout=3):
    """Жив ли CREOSON (порт 8080). Не выдумываем: спрашиваем сокет и отвечаем честно."""
    import socket
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect(("127.0.0.1", 8080))
        return True
    except Exception:
        return False
    finally:
        s.close()


def set_param(model, name, value):
    """Один параметр через доказанный путь `creo_ops_tools.set_param`. Возвращает (ok, note)."""
    try:
        import creo_ops_tools as OT
        r = OT.tool_set_param(name=name, value=value, model=model)
        txt = r if isinstance(r, str) else json.dumps(r, ensure_ascii=False, default=str)
        bad = any(w in txt.lower() for w in ("error", "ошибка", "не найден", "отказ"))
        return (not bad), txt[:200]
    except Exception as e:
        return False, "вызов set_param упал: %s" % e


def apply_plan(plan, approve=False, copy_only=True, dry_run=False, on_log=None):
    """Исполнить план шагов. Согласие обязательно; СТОП между моделями; честный отказ."""
    log = on_log or (lambda s: None)
    if plan.get("error"):
        return {"rc": 2, "detail": "план пуст или битый: %s" % plan["error"]}
    steps = [s for s in plan.get("steps", [])
             if s["verdict"] in ("change", "miss")]
    if not steps:
        return {"rc": 0, "detail": "нечего применять: все шаги same/read_fail", "done": 0}
    if not approve:
        return {"rc": 3, "detail": "НЕ СОГЛАСОВАНО: нужен approve=1 (запись не начиналась)",
                "planned": len(steps)}
    if dry_run:
        return {"rc": 0, "detail": "пробный прогон (dry_run): записи не было",
                "planned": len(steps), "done": 0}
    if not creoson_alive():
        return {"rc": 2, "detail": "CREOSON не отвечает (порт 8080) - запись НЕ выполнена. "
                "Подними CREOSON и повтори; боевые файлы не тронуты.", "planned": len(steps)}

    results = []
    seen = set()
    for i, s in enumerate(steps):
        if STOP["flag"]:
            log("СТОП на шаге %d из %d" % (i, len(steps)))
            return {"rc": 0, "detail": "остановлено СТОП на шаге %d" % i,
                    "done": len(results), "results": results, "stopped": True}
        if s["file"] not in seen:
            seen.add(s["file"])          # одну модель открываем логически один раз
        ok, note = set_param(Path(s["file"]).stem, s["param"], s["value"])
        results.append({"file": s["name"], "param": s["param"], "ok": ok, "note": note})
        log("%s %s %s=%s" % ("OK " if ok else "FAIL", s["name"], s["param"], s["value"]))
        time.sleep(0.05)                  # пауза, чтобы не долбить CREOSON
    done = sum(1 for r in results if r["ok"])
    return {"rc": 0 if done == len(results) else 1,
            "detail": "вышло: %d из %d" % (done, len(results)),
            "done": done, "results": results, "stopped": False}


def write_apply_report(res):
    """Журнал прогона: где вышло, где нет."""
    P.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    P.LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d_%H%M%S")
    rp = P.REPORT_DIR / ("REPORT_batch_params_apply_%s.md" % stamp)
    out = ["# ОТЧЁТ ПРИМЕНЕНИЯ ПАКЕТНЫХ ПАРАМЕТРОВ", "",
           "Итог: **%s** (RC %d) · %s" % (
               "ОК" if res.get("rc") == 0 else "НЕ ОК",
               res.get("rc", 0), res.get("detail", "")), ""]
    if res.get("results"):
        out += ["| Модель | Параметр | Вердикт | Что |", "|---|---|---|---|"]
        for r in res["results"]:
            out.append("| %s | %s | %s | %s |"
                       % (r["file"], r["param"], "ОК" if r["ok"] else "ПРОВАЛ",
                          r["note"].replace("|", "/")))
    rp.write_text("\n".join(out), encoding="utf-8")
    return str(rp)


def main(argv):
    approve = "--approve" in argv or "--approve=1" in argv
    dry = "--dry_run" in argv
    json_path = next((a for a in argv[1:] if a.endswith(".json")), None)
    if not json_path:
        print("нужен файл плана: batch_params_apply.py <plan.json> [--approve] [--dry_run]")
        return 2
    plan = json.loads(Path(json_path).read_text(encoding="utf-8"))
    res = apply_plan(plan, approve=approve, dry_run=dry,
                     on_log=lambda s: print("  " + s))
    print("ПРИМЕНЕНИЕ ПЛАНА: RC %d - %s" % (res.get("rc", 0), res.get("detail", "")))
    if res.get("results"):
        rp = write_apply_report(res)
        print("отчёт: %s" % rp)
    return res.get("rc", 0)


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv))