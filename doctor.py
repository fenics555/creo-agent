# -*- coding: utf-8 -*-
# doctor.py — ЕДИНЫЙ файл правок. Перезаписывается каждым следующим патчем.
# Цикл: cd D:\AI\tools\agent; python doctor.py; .\AI_RESTART.bat; .\GIT_SYNC.bat
import io
from pathlib import Path
AG = Path(r"D:\AI\tools\agent")

def rep(path, old, new, tag):
    p = AG / path
    s = p.read_text(encoding="utf-8")
    if new in s: print("[~] %s: уже" % tag); return
    if old not in s: print("[x] %s: якорь не найден" % tag); return
    p.write_text(s.replace(old, new, 1), encoding="utf-8")
    print("[+] %s" % tag)

# 1) settings: группы Пути + Creo в REGISTRY
anchor = '("Сканер", "retention", "Глубина бэкапов", "int", 7, "Копий базы храним.", True),'
add = '''
    ("Пути", "creoson_url", "URL CREOSON", "str", "http://127.0.0.1:8080/creoson", "Мост Creo.", True),
    ("Пути", "creoson_dir", "Папка CREOSON", "str", r"D:\\AI\\creoson\\CreosonServer-3.0.2-win64", "Где creoson_run.bat.", True),
    ("Пути", "pdf_out", "Папка PDF", "str", "", "Пусто = agent/pdf_out.", True),
    ("Пути", "backup_dir", "Папка бэкапов", "str", "", "Пусто = agent/data/backups.", True),
    ("Пути", "trail_dirs", "Папки трейлов", "list", [], "Пусто = trail_dir из Creo + CREO-LOCAL-SETUP.", True),
    ("Creo", "bom_sections", "Порядок разделов спецы", "list", ["Документация", "Комплексы", "Сборочные единицы", "Детали", "Стандартные изделия", "Прочие изделия", "Материалы", "Комплекты"], "Порядок ГОСТ-разделов.", True),
    ("Creo", "copy_synonyms", "Синонимы поиска", "str", "турновер=переворот, turnover=переворот, ворошитель=переворот", "Для models_find.", True),'''
rep("settings.py", anchor, anchor + add, "settings: Пути+Creo")

# 2) creo_tools: URL из настроек
rep("creo_tools.py",
    'CREOSON_URL = "http://127.0.0.1:8080/creoson"',
    'CREOSON_URL = settings.get("creoson_url") or "http://127.0.0.1:8080/creoson"',
    "creo_tools: creoson_url из настроек")

# 3) creo_ops: pdf_out из настроек + импорт
rep("creo_ops_tools.py",
    'outdir = dirname or str(core.BASE / "pdf_out")',
    'outdir = dirname or (settings.get("pdf_out") or str(core.BASE / "pdf_out"))',
    "creo_ops: pdf_out из настроек")
p = AG / "creo_ops_tools.py"; s = p.read_text(encoding="utf-8")
if "import settings" not in s:
    p.write_text(s.replace("import creo_tools as CT", "import creo_tools as CT\nimport settings", 1), encoding="utf-8")
    print("[+] creo_ops: import settings")

# 4) ctl: creoson_dir из config.json
rep("ctl.py",
    'CREOSON_DIR = r"D:\\AI\\creoson\\CreosonServer-3.0.2-win64"',
    'def _cfg(key, defl):\n    try:\n        import json as _j\n        d = _j.load(open(TOOLS + r"\\agent\\data\\config.json", encoding="utf-8"))\n        return d.get(key) or defl\n    except Exception:\n        return defl\nCREOSON_DIR = _cfg("creoson_dir", r"D:\\AI\\creoson\\CreosonServer-3.0.2-win64")',
    "ctl: creoson_dir из config")

# 5) fleet_tools: настоящий блок вместо постороннего скрипта
FLEET = '''# -*- coding: utf-8 -*-
r"""FLEET: агенты офиса: кто жив, модель, блоки (через /status соседей)."""
import json
import urllib.request
import settings

DEFAULT_HOSTS = "192.168.88.159"

def _hosts():
    raw = settings.get("fleet_hosts") or DEFAULT_HOSTS
    return [h.strip() for h in str(raw).replace(";", ",").split(",") if h.strip()]

def _info(host, t=2):
    try:
        with urllib.request.urlopen("http://%s:8765/status" % host, timeout=t) as r:
            d = json.loads(r.read().decode("utf-8"))
        d["alive"] = True; d["host"] = host
        return d
    except Exception as e:
        return {"host": host, "alive": False, "error": str(e)[:60]}

def tool_fleet_status(**kw):
    out = []
    for d in (_info(h) for h in _hosts()):
        if not d.get("alive"):
            out.append("- %s: недоступен (%s)" % (d["host"], d.get("error")))
        else:
            out.append("- %s | жив | %s | блоков: %s | инструментов: %s"
                       % (d["host"], d.get("model"), d.get("blocks"), d.get("tools")))
    return "\\n".join(out) or "список хостов пуст"

def tool_fleet_hosts(hosts="", **kw):
    if hosts:
        settings.set_val("fleet_hosts", hosts)
        return "хосты обновлены: %s" % hosts
    return "текущие хосты: %s" % ", ".join(_hosts())

TOOLS = [
    {"name": "fleet_status", "desc": "Флот: какие агенты в сети живы (модель, блоки, инструменты)", "params": {}, "approval": False, "fn": tool_fleet_status},
    {"name": "fleet_hosts", "desc": "Показать/задать список машин флота (IP через запятую)", "params": {"hosts": "список"}, "approval": False, "fn": tool_fleet_hosts},
]
'''
(AG / "fleet_tools.py").write_text(FLEET, encoding="utf-8")
print("[+] fleet_tools.py: настоящий блок флота")

# 6) README агента
README = '''# АГЕНТ v12 — ИИ-напарник КБ (Creo Parametric)

Веб-агент: чат с локальной LLM (Ollama), живые данные Creo через CREOSON,
база знаний, трейлы, ГОСТ-спецификации, флот. Только стандартная библиотека Python.

## Вход
По умолчанию: `admin` / `admin` (роль Администратор). Смена: 👤 → Сменить пароль.

## Быстрый старт
1. Python 3.10+, Ollama, CREOSON 3.x, Creo 8–13.
2. `AI_START.bat` (или `python ctl.py up --browser`).
3. Открыть http://127.0.0.1:8765 (или сетевой_IP:8765).
Рестарт — `AI_RESTART.bat`, стоп — `AI_STOP.bat`, статус — `python ctl.py status`.

## Пути — где править
Панель → НАСТРОЙКИ → группа «Пути»: creoson_url, creoson_dir, pdf_out,
backup_dir, trail_dirs. Лежат в `agent/data/config.json`, можно править руками.
Корни индекса и исключения — `kb_roots.txt` / `kb_exclude.txt` рядом с агентом.
Корень установки (BASE, REPO) — `core.py` и `ctl.py` (TOOLS) при переезде.

## Блоки (автоподключение *_tools.py)
CREO (чтение), CREO-ОПЕРАЦИИ (запись под щитом ✅), SPEC (ГОСТ XLSX),
FIND/USAGE, ЗНАНИЯ/СКАНЕР, ПАМЯТЬ/ТРЕЙЛЫ/LEARN, 1С, ПАСПОРТ, ДОСТУПЫ,
ФЛОТ, ЧАТ, ВИЗИЯ, WEB, БЭКАПЫ, ДИАГНОСТИКА.
Новый блок = файл `my_tools.py` со списком TOOLS + рестарт.

## Диагностика
`diag_run` — полная самопроверка (вердикт ПРОЙДЕН/НЕ ПРОЙДЕН),
`diag_test` — быстрый прогон, `creoson_full_test` — пишущий цикл на копии.
Логи: `agent_log_*.txt`, `diag_full.log`, `diag_creoson.log`.

## Правки
Один файл `doctor.py`: перезаписать содержимое, затем
`python doctor.py`, `.\\AI_RESTART.bat`, `.\\GIT_SYNC.bat`.

## Смежный репозиторий
`creo-repo` — скиллы и справочники (Creo, Python, инженерные, производство).
'''
(AG / "README.md").write_text(README, encoding="utf-8")
print("[+] README.md обновлён")
print("ГОТОВО: .\\AI_RESTART.bat, затем .\\GIT_SYNC.bat")