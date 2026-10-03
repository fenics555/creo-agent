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


def creoson_ready(timeout=3):
    """Готов ли стек к записи: (готов?, причина).

    Проверяются ДВА условия, потому что на машине они расходятся (живой факт 03.10.2026):
      1. порт 8080 (CREOSON поднят) — иначе поднимаем `creoson_run.bat`;
      2. процесс `parametric.exe` (сам Creo запущен) — без него `parameter:set`
         невозможен, даже когда сервер отвечает.
    Возвращаем ЧЕСТНЫЙ отказ с указанием, что именно не так, а не «прогон успешен».
    """
    import socket
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect(("127.0.0.1", 8080))
    except Exception:
        return False, "CREOSON не отвечает (порт 8080). Подними: creoson_run.bat"
    finally:
        s.close()
    try:
        import subprocess
        # КОДИРОВКА: tasklist в cp866, а дефолт utf-8 роняет reader-thread с
        # UnicodeDecodeError и stdout приходит None (живой факт 03.10.2026).
        ps = subprocess.run(["tasklist", "/FI", "IMAGENAME eq parametric.exe"],
                            capture_output=True, text=True, encoding="cp866",
                            errors="replace", timeout=20)
        out = ps.stdout or ""
        if "parametric.exe" not in out:
            return False, ("CREOSON отвечает, но Creo не запущен (parametric.exe нет). "
                           "Запись параметров без него невозможна.")
    except Exception as e:
        return False, "не удалось проверить parametric.exe: %s" % e
    return True, "стек готов: CREOSON отвечает, Creo запущен"


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


def ensure_active(target_file, retries=3, pause=1.0):
    """ЩИТ «ТОЛЬКО КОПИЯ»: активная модель в Creo ДОЛЖНА быть целевой.

    ИНЦИДЕНТ 03.10.2026 (см. dev\\incident_din439.py): `file:open` с полным путём
    НЕ переключает окно - активируется модель с тем же стемом, уже открытая в сессии
    (боевая `Z:\\...\\din439.prt` вместо копии `D:\\AI\\PROBA\\vol7_copy\\din439.prt`).
    Из-за этого `file:save` отвечал «ok», а параметр уходил в БОЕВУЮ модель.
    Поэтому перед любой записью сверяем: кто реально активен.
    Возвращает (ok, причина).
    """
    import time
    import creo_tools as CT
    want_name = str(Path(target_file).name).lower()
    want_dir = str(Path(target_file).parent).lower().rstrip("\\/")

    def norm_dir(s):
        # CREOSON отдаёт путь с УДВОЕННЫМ диском («Z:Z:/PTC/...») и слэшами.
        s = str(s).replace("\\", "/").lower()
        while "//" in s:
            s = s.replace("//", "/")
        while len(s) > 1 and s[1] == ":":
            s = s[1:]                      # убрать повтор диска
        return s.rstrip("/")

    for i in range(int(retries)):
        j = CT.creo_call("file", "get_active", {}, 20)
        d = j.get("data") if CT.ok(j) else None
        if isinstance(d, dict):
            got = str(d.get("file") or "").lower()
            got_dir = norm_dir(d.get("dirname") or "")
            # Сверка ПО ПУТИ: сверка по имени не годится - стен у боевой и копии
            # одинаковый, именно это и вызвало инцидент 03.10.2026.
            if got == want_name and got_dir == norm_dir(want_dir):
                return True, "активна целевая модель %s (%s)" % (got, d.get("dirname"))
            return False, ("активна ДРУГАЯ модель: %s (%s) — запись прервана, цель была %s (%s)"
                           % (got or "неизвестна", d.get("dirname") or "?", want_name,
                              Path(target_file).parent))
        time.sleep(pause)
    return False, "CREOSON не отдал активную модель — запись прервана"


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
    """Исполнить план шагов. Согласие обязательно; СТОП до всего; честный отказ."""
    log = on_log or (lambda s: None)
    # СТОП проверяется ПЕРВЫМ: человек нажал СТОП - запись не начинается вообще.
    # (ЖИВАЯ ПРОВЕРКА 03.10.2026: проверка СТОП внутри цикла не срабатывала при мёртвом
    #  CREOSON - цикл до неё не доходил, и кнопка СТОП выглядела бы «мёртвой».)
    if STOP["flag"]:
        return {"rc": 0, "detail": "СТОП нажат до начала: запись не начиналась",
                "done": 0, "stopped": True}
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
    ready, why = creoson_ready()
    if not ready:
        return {"rc": 2, "detail": "%s - запись НЕ выполнена; боевые файлы не тронуты."
                % why, "planned": len(steps), "stack_ready": False}

    results = []
    seen = set()
    for i, s in enumerate(steps):
        if STOP["flag"]:
            log("СТОП на шаге %d из %d" % (i, len(steps)))
            return {"rc": 0, "detail": "остановлено СТОП на шаге %d" % i,
                    "done": len(results), "results": results, "stopped": True}
        # ЩИТ «ТОЛЬКО КОПИЯ»: активная модель обязана совпадать с целевой.
        # Без этой сверки запись уходит в модель с тем же стемом (инцидент 03.10.2026).
        same, why_active = ensure_active(s["file"])
        if not same:
            results.append({"file": s["name"], "param": s["param"], "ok": False,
                            "note": why_active})
            log("СТОП-ЩИТ: %s" % why_active)
            return {"rc": 4, "detail": why_active, "done": sum(1 for r in results
                                                              if r["ok"]),
                    "results": results, "stopped": True, "shield": "wrong_active_model"}
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