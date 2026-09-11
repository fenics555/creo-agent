# Пятничный пакет: диагностика + гигиена + контракты. Ничего не правит вслепую.
import os, sys, json, shutil, socket, subprocess, traceback, py_compile

ROOT = r"D:\AI\tools\agent"
DATA = os.path.join(ROOT, "data")
TMP = os.path.join(DATA, "tmp")
BAK = os.path.join(DATA, "backup")
os.makedirs(TMP, exist_ok=True); os.makedirs(BAK, exist_ok=True)
R = []

def log(tag, msg):
    s = f"[{tag}] {msg}"; print(s); R.append(s)

def backup(path):
    if os.path.exists(path):
        shutil.copy2(path, os.path.join(BAK, "pre_pack_" + os.path.basename(path)))

# ШАГ 0: ДИАГНОСТИКА (read-only), в т.ч. причина незапуска
log("S0", "=== диагностика ===")
for port in (8765, 8000, 8080, 11434):
    s = socket.socket(); s.settimeout(1)
    try:
        s.connect(("127.0.0.1", port)); log("S0", f"порт {port}: занят (жив)")
    except Exception:
        log("S0", f"порт {port}: свободен")
    finally:
        s.close()
sys.path.insert(0, ROOT)
for mod in ("core", "settings", "users", "panel", "tools_registry", "pdf_tools"):
    try:
        __import__(mod); log("S0", f"import {mod}: OK")
    except Exception:
        log("S0", f"import {mod}: FAIL\n{traceback.format_exc()}")
try:
    p = subprocess.run([sys.executable, "-X", "utf8", "-c",
        f"import sys; sys.path.insert(0, r'{ROOT}'); import agent; print('IMPORT_AGENT_OK')"],
        capture_output=True, text=True, timeout=40)
    log("S0", f"import agent: {p.stdout.strip() or p.stderr.strip()[-800:]}")
except subprocess.TimeoutExpired:
    log("S0", "import agent: завис >40с (сервер стартует без __main__-гарда?)")
except Exception as e:
    log("S0", f"import agent: ошибка пробы {e}")
try:
    g = subprocess.run(["git", "-C", ROOT, "status", "--short"], capture_output=True, text=True, timeout=60)
    log("S0", "git status: " + (g.stdout.strip() or "(чисто)"))
except Exception as e:
    log("S0", f"git: {e}")

# ШАГ 1: гигиена tmp (pidfile и qa-логи НЕ трогаем)
JUNK = ["p1.json","conn.json","page.html","add_user.py","check_file.py","setm.json",
        "inv_agent.csv","inv_repo.csv","panel_new.py","panel_fixed.py","fix_panel.py",
        "new_doget.py","creo_root.json","agent_manual_out.txt","agent_manual_err.txt"]
for f in JUNK:
    p = os.path.join(TMP, f)
    if os.path.exists(p): os.remove(p); log("S1", f"удалён {f}")

# ШАГ 2: .bak в карантин, не удаление
q = os.path.join(TMP, "bak_quarantine"); os.makedirs(q, exist_ok=True)
for f in os.listdir(ROOT):
    if f.lower().endswith(".bak"):
        shutil.move(os.path.join(ROOT, f), os.path.join(q, f)); log("S2", f".bak в карантин: {f}")

# ШАГ 3: users.json (test_user всегда, engineer_bot только если нет ссылок в коде)
up = os.path.join(DATA, "users.json"); backup(up)
try:
    d = json.load(open(up, encoding="utf-8"))
    refs = ""
    for fn in ("qa/qa_run.py", "agent.py", "nightly_tools.py", "users_tools.py"):
        fp = os.path.join(ROOT, *fn.split("/"))
        if os.path.exists(fp): refs += open(fp, encoding="utf-8", errors="ignore").read()
    before = len(d.get("users", [])); keep = []
    for u in d.get("users", []):
        lg = u.get("login", "")
        if lg == "test_user": log("S3", "удалён test_user"); continue
        if lg == "engineer_bot" and "engineer_bot" not in refs:
            log("S3", "удалён engineer_bot (ссылок в коде нет)"); continue
        if lg == "engineer_bot": log("S3", "engineer_bot оставлен: найдена ссылка в коде")
        keep.append(u)
    d["users"] = keep
    json.dump(d, open(up, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    log("S3", f"users.json: {before} -> {len(keep)}")
except Exception:
    shutil.copy2(os.path.join(BAK, "pre_pack_users.json"), up)
    log("S3", f"FAIL, откат\n{traceback.format_exc()}")

# ШАГ 4: .clinerules — дописать отсутствующие блоки (проверка по маркерам)
cp = r"D:\AI\.clinerules"; t = open(cp, encoding="utf-8").read(); add = ""
if "хирургические патчи" not in t:
    add += ("\n5.7. ХИРУРГИЧЕСКИЕ ПАТЧИ: вставка/замена блоков в файлах >500 строк — НЕ editor с old_text,\n"
            "     а временным Python-скриптом в data\\tmp: прочитать, найти якорь (номер строки из findstr\n"
            "     или уникальный маркер); якорь НЕ найден — выйти с ошибкой, файл НЕ писать; вставить по якорю;\n"
            "     записать; py_compile; удалить скрипт. Цитировать номера якоря до и после.\n"
            "     editor — только малые правки, old_text скопирован из свежего read_file того же диапазона.\n")
if "SKILL_creoson_complete.md" not in t:
    add += ("\n8.1a. В задачах с Creo/CREOSON (копия, rename, pdf, параметры, спека, трейлы) сначала читай\n"
            "      D:\\AI\\repo\\Creo\\SKILL_creoson_complete.md и D:\\AI\\repo\\Creo\\SKILL_creoson_write_rules.md;\n"
            "      в задачах копирования/переименования дополнительно D:\\AI\\repo\\SKILL_copy_rename.md.\n")
if "10.1." not in t:
    add += ("\n10.1. JSON-тела для curl --data-binary писать с -Encoding ascii (или utf8 без BOM):\n"
            "      BOM в начале тела ломает парсер CREOSON; -Encoding utf8 — только файлы для python/человека.\n")
if add:
    backup(cp); open(cp, "a", encoding="utf-8").write(add); log("S4", ".clinerules: дописаны отсутствующие блоки")
else:
    log("S4", ".clinerules: все блоки уже на месте")

# ШАГ 5: протокол — маршрутизация журнальных вопросов + один ANSWER
sp = r"D:\AI\repo\SKILL_agent_protocol.md"; t = open(sp, encoding="utf-8").read()
if "кто и когда работал в Creo" not in t:
    backup(sp)
    open(sp, "a", encoding="utf-8").write(
        "\n- «кто и когда работал в Creo», «кто трогал/открывал модель», «журнал сессий» →\n"
        "  trail_analyze (раздел журнал) или trail_diagnose; НЕ search_kb, НЕ one_c_status, НЕ plm_audit.\n"
        "- Ровно один блок [ANSWER] за ход: уточнение ВНУТРИ того же блока,\n"
        "  второй [ANSWER] в том же сообщении — нарушение протокола.\n")
    log("S5", "протокол: дописаны маршрутизация и один ANSWER")
else:
    log("S5", "протокол: строки уже на месте")

# ШАГ 6: qa_night.bat (пре-флайт + детач; замок внутри qa_run)
qp = os.path.join(ROOT, "qa_night.bat")
if not os.path.exists(qp):
    open(qp, "w", encoding="ascii").write(
        "@echo off\n"
        "powershell -NoProfile -Command \"if ((curl.exe -s -o NUL -w '%%{http_code}' http://127.0.0.1:8765/status) -ne '200') { Start-Process -FilePath 'D:\\AI\\tools\\agent\\AI_RESTART.bat' -WindowStyle Hidden; Start-Sleep 25 }\"\n"
        "Start-Process python -ArgumentList \"D:\\AI\\tools\\agent\\qa\\qa_run.py\" -WindowStyle Hidden -RedirectStandardOutput \"D:\\AI\\tools\\agent\\data\\tmp\\qa_out.txt\" -RedirectStandardError \"D:\\AI\\tools\\agent\\data\\tmp\\qa_err.txt\"\n")
    log("S6", "создан qa_night.bat")
else:
    log("S6", "qa_night.bat уже есть")

# ШАГ 7: комфорт-строка в AI_RESTART.bat (аффинитет + приоритет ollama)
bp = os.path.join(ROOT, "AI_RESTART.bat"); t = open(bp, encoding="utf-8", errors="ignore").read()
if "ProcessorAffinity" not in t:
    backup(bp)
    open(bp, "a", encoding="ascii").write(
        "\npowershell -NoProfile -Command \"$p=Get-Process ollama -ErrorAction SilentlyContinue; if($p){$n=(Get-CimInstance Win32_Processor).NumberOfLogicalProcessors; $leave=[Math]::Max(3,[int]($n*0.17)); $mask=[long]((1 -shl ($n-$leave))-1); $p.ProcessorAffinity=[IntPtr]$mask; $p.PriorityClass='BelowNormal'}\"\n")
    log("S7", "AI_RESTART.bat: дописана комфорт-строка")
else:
    log("S7", "AI_RESTART.bat: аффинитет уже есть")

# ШАГ 8: компиляционный контроль
for f in ("agent.py", "ctl.py", "settings.py", "panel.py", "pdf_tools.py", "qa/qa_run.py"):
    p = os.path.join(ROOT, *f.split("/"))
    try:
        py_compile.compile(p, doraise=True); log("S8", f"py_compile {f}: OK")
    except Exception as e:
        log("S8", f"py_compile {f}: FAIL {e}")

open(os.path.join(TMP, "doctor_pack_report.txt"), "w", encoding="utf-8").write("\n".join(R))
print("\nОтчёт сохранён:", os.path.join(TMP, "doctor_pack_report.txt"))