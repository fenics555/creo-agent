# -*- coding: utf-8 -*-
"""vol9_check.py — приёмка ЭТАПА 9 (волна 10): карта плагинов PLUGINS.md + живая проверка.

Что проверяет:
  1) карта `dev\\PLUGINS.md` есть и содержит живой раздел со строками `- protkdat`;
  2) `config_audit.audit_protk()` на БОЕВОМ config.pro: все строки `protkdat` зафиксированы,
     активные — есть на диске;
  3) ЗАЩИТА ПРОТИВ ЛОЖНОГО «ВСЁ ХОРОШО»: на СИНТЕТИЧЕСКОМ config.pro с новым
     непокрытым `protkdat` функция обязана дать расхождение `нет_в_карте`;
  4) проверка `plugins_registry` зарегистрирована в каркасе `checks.py` и даёт вердикт;
  5) CLI-путь: `config_audit.main()` на боевом конфиге не падает (RC 0 или 1 — не 2).

Запуск: cmd /c "python -X utf8 dev\\vol9_check.py > data\\tmp\\vol9.txt 2>&1"
"""
import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path

AGENT = Path(r"D:\AI\tools\agent")
sys.path.insert(0, str(AGENT))
sys.path.insert(0, str(AGENT / "config_audit"))

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ok = [0]
fail = [0]


def crit(cond, text):
    if cond:
        ok[0] += 1
        print("  OK   %s" % text)
    else:
        fail[0] += 1
        print("  ПРОВАЛ %s" % text)


print("== 1. КАРТА ПЛАГИНОВ НА ДИСКЕ ==")
card = AGENT / "dev" / "PLUGINS.md"
crit(card.is_file(), "dev\\PLUGINS.md существует")
txt = card.read_text(encoding="utf-8") if card.is_file() else ""
lines = [ln.strip() for ln in txt.splitlines()]
entries = [ln for ln in lines if ln.startswith("- protkdat")]
crit(len(entries) >= 1, "в карте есть живые строки `- protkdat`: %d" % len(entries))
for need in ("## 1. ЖИВАЯ ПРОВЕРКА", "## 3. АРХИВ B&W", "## 4. УСТАНОВКА: МЕХАНИЗМ",
             "## 5. СВЯЗКИ С ДОМОМ", "## 6. ПРАВИЛА ВЕДЕНИЯ КАРТЫ"):
    crit(need in txt, "раздел есть: %s" % need)
crit("VERICUT" in txt, "плагин в бою (VERICUT) описан")
crit("RM-23710" in txt and "RM-24179" in txt, "вендорские ссылки цитатой с номерами RM-")

print("\n== 2. ЖИВАЯ ПРОВЕРКА НА БОЕВОМ config.pro ==")
import config_audit as CA                                        # noqa: E402

cfg = CA.CONFIG
crit(bool(cfg) and Path(cfg).is_file(), "боевой config.pro найден: %s" % cfg)
if cfg and Path(cfg).is_file():
    p = CA.audit_protk(cfg)
    print("   в config.pro: %d | в карте: %d | активных: %d | расхождений: %d"
          % (p["in_config"], p["in_card"], p["active"], len(p["problems"])))
    for r in p["rows"]:
        print("   строка %-4d %-9s %-7s %s" % (r["line"], "активен" if r["active"] else "ВЫКЛЮЧЕН",
                                                 "есть" if r["on_disk"] else "НЕТ", r["path"]))
    for pr in p["problems"]:
        print("   РАСХОЖДЕНИЕ [%s] строка %d: %s" % (pr["kind"], pr["line"], pr["path"]))
    crit(p["in_config"] >= 1, "в боевом config.pro найдены строки protkdat (%d)" % p["in_config"])
    crit(p["in_card"] >= 1, "карта прочитана программой (%d записей)" % p["in_card"])
    crit(p["hard"] == 0, "жёстких расхождений нет (hard=%d)" % p["hard"])
    crit(p.get("card_found") is True, "карта найдена программой: %s" % p.get("card"))
    active_rows = [r for r in p["rows"] if r["active"]]
    crit(all(r["on_disk"] for r in active_rows),
         "все активные плагины есть на диске (%d активных)" % len(active_rows))
    crit(all(r["in_card"] for r in p["rows"]),
         "каждая строка protkdat боя зафиксирована в карте")

print("\n== 3. ЗАЩИТА: новый protkdat без записи в карте ==")
tmp = Path(tempfile.mkdtemp(prefix="vol9_protk_"))
fake = tmp / "config.pro"
fake.write_text(
    "protkdat D:\\CGTech\\VERICUT 9.0.1\\windows64\\proev\\Creo60\\protk.dat\n"
    "!protkdat C:\\Program Files\\KeyShot7\\Plugins\\Creo 3.0 64bit\\protk.dat\n"
    "protkdat D:\\AWAY\\NEWPLUGIN 1.0\\protk.dat\n", encoding="utf-8")
p2 = CA.audit_protk(str(fake))
kinds = sorted({x["kind"] for x in p2["problems"]})
print("   расхождения на синтетическом конфиге: %s" % kinds)
crit("нет_в_карте" in kinds, "незафиксированный плагин пойман (есть 'нет_в_карте')")
crit(p2["hard"] >= 1, "жёсткое расхождение поднято (hard=%d)" % p2["hard"])
crit(any(x["path"].lower().endswith("newplugin 1.0\\protk.dat") for x in p2["problems"]),
     "проблема указывает именно на новый плагин")
# Регресс найденного дефекта: закомментированный (`!`) protkdat обязан попасть в разбор.
# 03.10.2026 без этого программа писала «нет_в_бою» на зафиксированный KeyShot.
crit(p2["in_config"] == 3, "разобраны все 3 строки protkdat, включая закомментированную (%d)"
     % p2["in_config"])
off_rows = [r for r in p2["rows"] if not r["active"]]
crit(len(off_rows) == 1 and "keyshot" in off_rows[0]["path"].lower(),
     "выключенный KeyShot прочитан как выключенный (%d выкл.)" % len(off_rows))
crit(not any(x["kind"] == "нет_в_бою" for x in p2["problems"]),
     "ложного «нет_в_бою» на зафиксированные модули нет")

print("\n== 3а. АВТОНОМНОСТЬ: копия движка БЕЗ карты ==")
# Регресс живого провала vol2 (03.10.2026): изоляция без `dev\PLUGINS.md` помечала
# каждый protkdat как «нет_в_карте» → RC 1. Правильный честный ответ — «нет данных».
iso = Path(tempfile.mkdtemp(prefix="vol9_iso_"))
SHARED = ("config_audit.py", "creo_boot.py")
SRCDIR = {"config_audit.py": AGENT / "config_audit", "creo_boot.py": AGENT}
for fn in SHARED:
    (iso / fn).write_bytes((SRCDIR[fn] / fn).read_bytes())
# Настройки программы — часть переноса (контракт 09_): без них не подставляется
# $PRO_DIRECTORY, и поиск Creo честно пишет «установка не найдена».
sset = AGENT / "data" / "config_audit_settings.json"
if sset.is_file():
    (iso / "config_audit_settings.json").write_bytes(sset.read_bytes())
cpath = AGENT / "creo_path.py"
if cpath.is_file():
    (iso / "creo_path.py").write_bytes(cpath.read_bytes())
import subprocess as _sp                                        # noqa: E402
# Путь config.pro передаём ЯВНО: изолированная копия не ищет боевой конфиг (RC 2 — это
# корректный ответ «нечего проверять», а не проверка автономности).
_r = _sp.run([sys.executable, "-X", "utf8", str(iso / "config_audit.py"), cfg],
             capture_output=True, text=True, encoding="utf-8", errors="replace",
             cwd=str(iso), env={**os.environ, "PYTHONPATH": str(iso)})
_out = _r.stdout or ""
crit(_r.returncode in (0, 1), "изолированная копия отработала по переданному config.pro (RC=%d)"
     % _r.returncode)
crit("ПРОТИВ: D:\\" in _out or "ПРОТИВ: C:\\" in _out,
     "изоляция с настройками нашла установку Creo (RC=%d)" % _r.returncode)
crit("карта плагинов не найдена" in _out,
     "без карты программа честно пишет «нет данных», а не провал")
crit("РАСХОЖДЕНИЕ" not in _out,
     "изоляция без карты не выдумывает расхождений (это был живой провал vol2)")

print("\n== 4. ПРОВЕРКА plugins_registry В КАРКАСЕ checks.py ==")
import checks as CH                                             # noqa: E402

spec = CH.get("plugins_registry")
crit(spec is not None, "паспорт plugins_registry зарегистрирован")
if spec:
    r = CH.run_one(spec)
    print("   вердикт: ok=%s · %s" % (r["ok"], r["detail"]))
    crit(isinstance(r["ok"], bool), "проверка отработала и вернула вердикт")
    crit(r["ok"] is True, "на боевой машине проверка зелёная (ok=%s)" % r["ok"])
    ids = [c["id"] for c in CH.CHECKS]
    crit(ids.count("plugins_registry") == 1, "проверка зарегистрирована один раз")

print("\n== 5. CLI-ПУТЬ config_audit.main() ==")
out = subprocess.run([sys.executable, "-X", "utf8", str(AGENT / "config_audit" / "config_audit.py")],
                     capture_output=True, text=True, encoding="utf-8", errors="replace",
                     cwd=str(AGENT / "config_audit"))
tail = (out.stdout or "").strip().splitlines()[-3:]
print("   RC=%s · хвост вывода: %s" % (out.returncode, " | ".join(tail)))
crit(out.returncode in (0, 1), "CLI не упал (RC=%s, 2 = файл не найден)" % out.returncode)
crit("ПЛАГИНЫ" in (out.stdout or ""), "CLI печатает блок ПЛАГИНЫ")

print("\nИТОГ: критериев %d, провалов %d" % (ok[0] + fail[0], fail[0]))
print("ВЕРДИКТ: %s" % ("ГОДЕНО" if not fail[0] else "НЕ ГОДЕНО"))
raise SystemExit(1 if fail[0] else 0)