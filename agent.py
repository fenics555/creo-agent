# -*- coding: utf-8 -*-
r"""
АГЕНТ v12 — agent.py (финальная сборка, единая)
ThreadingHTTPServer + pid + процедурный промт + invalid-парсер + approve в контекст.
Финал: детерминированные чипы, своротка всех секций, вход вместо undefined, юзер в шапке.
"""
import json, re, socket, threading, time, datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import core
from core import log, trace
import settings
import tools_registry as TR
import scanner
import users
import chat_tools
import panel
import vision_tools as VI

HOST, PORT = "0.0.0.0", 8765
HOSTNAME = socket.gethostname()
PENDING = {}

DEFAULT_PROTO = """# ПРОТОКОЛ ИНЖЕНЕРА-НАПАРНИКА
## 1. РОЛЬ
Ты — старший инженер-конструктор КБ, напарник пользователя. Говоришь кратко, по делу, только проверенными фактами.
Скиллы в репо — справочники; при противоречии этот протокол главный.
## 2. ЯЗЫК
Думаешь и отвечаешь ТОЛЬКО на русском. Исключение — имена файлов, переменные, команды, код.
## 3. ФОРМАТ — ОДИН БЛОК НА ХОД
После ровно ОДИН блок, ничего до и после:
[TOOL: имя_инструмента] {"параметр": "значение"} [/TOOL]
или
[ANSWER] готовый ответ [/ANSWER]
## 4. ПРОТИВ ВЫДУМЫВАНИЯ
ЖИВЫЕ ДАННЫЕ (Creo, файлы, трейлы, база, 1С, настройки, история, пружины, стандарты, масса) — ТОЛЬКО через инструмент.
Справочные факты — через search_kb/read_file. Пока нет [РЕЗУЛЬТАТ] — не называй имён, шифров, чисел.
## 5. ПОРЯДОК
1. Определи, каких данных не хватает. 2. Вызови инструмент, жди [РЕЗУЛЬТАТ].
3. Мало — следующий; достаточно — [ANSWER] только из фактов [РЕЗУЛЬТАТ].
## 6. ПИШУЩИЕ ОПЕРАЦИИ
[СОГЛАСОВАНИЕ] меняет данные; вызывай только по прямой просьбе.
## 7. ПРИМЕРЫ
«какая модель открыта в Creo?» → [TOOL: creo_get_active] {} [/TOOL]
после [РЕЗУЛЬТАТ] → [ANSWER] Активная модель — korpus.prt [/ANSWER]
«привет» → [ANSWER] Привет! С чем помочь по Creo? [/ANSWER]"""

def load_skill(name):
    p = core.REPO / name
    try: return p.read_text(encoding="utf-8") if p.exists() else ""
    except Exception: return ""

def build_system():
    p = load_skill("SKILL_agent_protocol.md") or DEFAULT_PROTO
    return p + "\n\n=== ТВОИ ИНСТРУМЕНТЫ (имя — описание — параметры) ===\n" + TR.describe()

def beh():
    steps = int(settings.get("steps_max") or 6)
    if settings.get("auto_mode"):
        return ({"temperature": (settings.get("auto_temperature") or 10) / 100.0,
                 "top_p": float(settings.get("top_p") or 0.9),
                 "num_predict": int(settings.get("num_predict") or 1536)}, steps)
    return ({"temperature": (settings.get("creativity") or 30) / 100.0,
             "top_p": float(settings.get("top_p") or 0.9),
             "num_predict": int(settings.get("num_predict") or 1024)}, steps)

def parse_model(text):
    m = re.search(r"\[TOOL:\s*([A-Za-z0-9_]+)\s*\]\s*(\{.*?\})\s*\[/TOOL\]", text, re.S)
    if m:
        try: args = json.loads(m.group(2))
        except Exception: args = {}
        if TR.get(m.group(1)): return "tool", m.group(1), args
        if isinstance(args, dict) and TR.get(args.get("action", "")): return "tool", args["action"], {}
    m = re.search(r"\[TOOL:\s*([A-Za-z0-9_]+)\s*\]", text)
    if m and TR.get(m.group(1)):
        rest = text[m.end():m.end() + 800]
        args = {}
        mj = re.search(r"\s*(\{.*?\})", rest, re.S)
        if mj:
            try: args = json.loads(mj.group(1))
            except Exception: args = {}
        if not isinstance(args, dict) or not args:
            args = {}
            for kv in re.finditer(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*(.+?)\s*$", rest, re.M):
                val = kv.group(2).strip().strip('"').strip("'")
                if not val or val.startswith("[/TOOL]"): continue
                args[kv.group(1)] = val
                if len(args) >= 8: break
        return "tool", m.group(1), args
    for mm in re.finditer(r"^\s*([A-Za-z0-9_]+)\s*(\{[^\n]*\})\s*$", text, re.M):
        if TR.get(mm.group(1)):
            try: args = json.loads(mm.group(2))
            except Exception: args = {}
            return "tool", mm.group(1), args
    m = re.search(r"\[ANSWER\]\s*(.*?)\[/ANSWER\]", text, re.S)
    if m: return "answer", m.group(1).strip(), None
    return "invalid", text.strip(), None

def hist_block(client):
    c = core.db()
    rows = c.execute("SELECT q,a FROM history WHERE client=? ORDER BY id DESC LIMIT 8", (client,)).fetchall()
    c.close()
    out = []
    for q, a in reversed(rows):
        out.append({"role": "user", "content": q[:500]})
        out.append({"role": "assistant", "content": a[:800]})
    return out

def run_loop(messages, client, has_link=False):
    opts, steps_max = beh()
    steps_log, last_res, sig_prev, invalid_cnt = [], "", None, 0
    for step in range(steps_max):
        r = None
        for attempt in (1, 2):
            try:
                r = core.post("/api/chat", {"model": settings.get("llm_model") or "deepseek-r1:14b",
                              "stream": False, "options": opts, "messages": messages}, t=600)
                break
            except Exception as e:
                if attempt == 1 and "500" in str(e):
                    time.sleep(2); continue
                return {"answer": "ошибка модели: %s" % e, "think": "", "steps": step + 1, "log": steps_log}
        raw = (r.get("message") or {}).get("content") or ""
        think = re.search(r"<think>([\s\S]*?)</think>", raw)
        think = think.group(1).strip() if think else ""
        kind, payload, args = parse_model(raw)
        if kind == "answer":
            used_web = any("web_fetch" in s for s in steps_log)
            if has_link and not used_web and step < steps_max - 1 and len(payload) < 400:
                messages.append({"role": "assistant", "content": raw})
                messages.append({"role": "user", "content": "[СЛУЖЕБНОЕ] В задаче была ссылка http — сначала прочитай её через web_fetch, потом отвечай."})
                steps_log.append("web_nudge"); continue
            txt = payload
            if len(txt) < 40 and last_res: txt = last_res + "\n\n" + txt
            return {"answer": txt, "think": think, "steps": step + 1, "log": steps_log}
        if kind == "invalid":
            invalid_cnt += 1
            if invalid_cnt < 2:
                messages.append({"role": "assistant", "content": raw})
                messages.append({"role": "user", "content": "[СЛУЖЕБНОЕ] Ответ не в формате. Дай ровно один блок: [TOOL: имя] {\"параметр\": \"значение\"} [/TOOL] или [ANSWER] текст [/ANSWER]. Ничего до и после. Повтори."})
                steps_log.append("parse_invalid"); continue
            return {"answer": payload, "think": think, "steps": step + 1, "log": steps_log}
        name = payload
        sig = (name, json.dumps(args, sort_keys=True, ensure_ascii=False))
        if sig == sig_prev:
            return {"answer": last_res or "зацикливание остановлено", "think": think, "steps": step + 1, "log": steps_log}
        sig_prev = sig
        t = TR.get(name)
        if not t:
            res = "нет такого инструмента: %s" % name
        elif t.get("approval"):
            pid = datetime.datetime.now().strftime("%H%M%S%f")
            PENDING[pid] = {"name": name, "args": args, "client": client, "messages": messages, "raw": raw}
            return {"answer": "[СОГЛАСОВАНИЕ] операция %s ждёт подтверждения пользователя (id %s)" % (name, pid),
                    "think": think, "steps": step + 1, "log": steps_log}
        else:
            t0 = time.time()
            try:
                res = str(t["fn"](**args))
            except Exception as e:
                res = "ошибка исполнения %s: %s" % (name, e)
            trace("AGENT %s" % name, "OK", int((time.time() - t0) * 1000))
        steps_log.append("%s(%s) → %s" % (name, "без параметров" if not args else json.dumps(args, ensure_ascii=False), res[:120]))
        last_res = res
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": "[РЕЗУЛЬТАТ %s]: %s" % (name, res[:4000])})
    return {"answer": last_res or "не уложился в шаги", "think": "", "steps": steps_max, "log": steps_log}

def ask(q, client, image=None):
    q2 = VI.attach(q, image, client)
    name = q.strip()
    t = TR.get(name)
    if t and not image:
        if t.get("approval"):
            pid = datetime.datetime.now().strftime("%H%M%S%f")
            PENDING[pid] = {"name": name, "args": {}, "client": client, "messages": [], "raw": ""}
            return {"answer": "[СОГЛАСОВАНИЕ] операция %s ждёт подтверждения пользователя (id %s)" % (name, pid), "think": "", "steps": 1, "log": ["%s(прямой вызов)" % name]}
        t0 = time.time()
        try:
            res = str(t["fn"]())
        except TypeError:
            try:
                res = str(t["fn"](**{k: "" for k in t.get("params", {})}))
            except Exception as e:
                res = "ошибка исполнения %s: %s" % (name, e)
        except Exception as e:
            res = "ошибка исполнения %s: %s" % (name, e)
        trace("AGENT %s" % name, "OK", int((time.time() - t0) * 1000))
        c = core.db()
        c.execute("INSERT INTO history(client,q,a,ts) VALUES(?,?,?,?)", (client, q, res[:2000], datetime.datetime.now().isoformat()))
        c.commit(); c.close()
        return {"answer": res, "think": "", "steps": 1, "log": ["%s(прямой вызов) → %s" % (name, res[:120])]}
    name = q.strip()
    t = TR.get(name)
    if t and not image:
        if t.get("approval"):
            pid = datetime.datetime.now().strftime("%H%M%S%f")
            PENDING[pid] = {"name": name, "args": {}, "client": client, "messages": [], "raw": ""}
            return {"answer": "[СОГЛАСОВАНИЕ] операция %s ждёт подтверждения пользователя (id %s)" % (name, pid),
                    "think": "", "steps": 1, "log": ["%s(прямой вызов)" % name]}
        t0 = time.time()
        try:
            res = str(t["fn"]())
        except TypeError:
            try:
                res = str(t["fn"](**{k: "" for k in t.get("params", {})}))
            except Exception as e:
                res = "ошибка исполнения %s: %s" % (name, e)
        except Exception as e:
            res = "ошибка исполнения %s: %s" % (name, e)
        trace("AGENT %s" % name, "OK", int((time.time() - t0) * 1000))
        c = core.db()
        c.execute("INSERT INTO history(client,q,a,ts) VALUES(?,?,?,?)",
                  (client, q, res[:2000], datetime.datetime.now().isoformat()))
        c.commit(); c.close()
        return {"answer": res, "think": "", "steps": 1, "log": ["%s(прямой вызов) → %s" % (name, res[:120])]}
    q2 = q2 + "\n\n[СЛУЖЕБНОЕ: отвечай только по-русски. Один ход = один [TOOL] или один [ANSWER]. Никакого текста до и после блока.]"
    messages = [{"role": "system", "content": build_system()}] + hist_block(client) + [{"role": "user", "content": q2}]
    r = run_loop(messages, client, has_link=("http" in q))
    c = core.db()
    c.execute("INSERT INTO history(client,q,a,ts) VALUES(?,?,?,?)",
              (client, q, r["answer"][:2000], datetime.datetime.now().isoformat()))
    c.commit(); c.close()
    return r

def do_approve(pid, okf):
    p = PENDING.pop(pid, None)
    if not p: return {"res": "заявка не найдена"}
    if not okf: return {"res": "отменено пользователем"}
    t = TR.get(p["name"])
    try:
        res = str(t["fn"](**p["args"]))
    except Exception as e:
        return {"res": "ошибка исполнения: %s" % e}
    msgs = p.get("messages")
    if msgs:
        msgs.append({"role": "assistant", "content": p.get("raw", "")})
        msgs.append({"role": "user", "content": "[РЕЗУЛЬТАТ %s]: %s" % (p["name"], res[:4000])})
        r = run_loop(msgs, p.get("client"), has_link=False)
        return {"res": res, "answer": r["answer"], "think": r.get("think", ""), "log": r.get("log", [])}
    return {"res": res}

PAGE = r"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>АГЕНТ v12</title>
<style>body{margin:0;background:#14181f;color:#dfe6ee;font:14px/1.5 Segoe UI,sans-serif}
#top{position:fixed;top:0;left:0;right:0;background:#1b222b;padding:8px 14px;display:flex;gap:10px;align-items:center;z-index:5}
#top b{color:#6db3f2}#chat{margin:52px 300px 70px 12px;padding:8px;overflow-y:auto}
#panel{position:fixed;top:44px;right:0;bottom:0;width:292px;background:#171d26;overflow-y:auto;padding:8px}
.msg{max-width:760px;margin:10px 0;padding:10px 14px;border-radius:10px;background:#202834;white-space:pre-wrap}
.msg.me{margin-left:auto;background:#2b4a6f}
.think{background:#1a2129;border:1px solid #2c3644;border-radius:8px;padding:6px 10px;margin-bottom:4px;color:#9fb0c3;cursor:pointer}
.thinkbody{background:#1a2129;border:1px solid #2c3644;border-radius:8px;padding:6px 10px;margin-bottom:8px;color:#9fb0c3;white-space:pre-wrap}
.log{color:#8fa3b8;font-size:12px;margin:6px 0;white-space:pre-wrap}
#inp{position:fixed;bottom:0;left:0;right:292px;background:#1b222b;padding:8px;display:flex;gap:8px}
#q{flex:1;background:#232b36;color:#dfe6ee;border:1px solid #334052;border-radius:8px;padding:10px}
button{background:#2b4a6f;color:#fff;border:0;border-radius:8px;padding:8px 14px;cursor:pointer}
.spin{display:inline-block;width:16px;height:16px;border:2px solid #6db3f2;border-top-color:transparent;border-radius:50%;animation:rot .8s linear infinite;vertical-align:middle;margin-left:8px}
@keyframes rot{to{transform:rotate(360deg)}}
.grp{border:1px solid #243040;border-radius:8px;margin:6px 0;padding:6px}
.grp h4{margin:2px 0 6px;color:#6db3f2;cursor:pointer}
.tool{background:#202834;border-radius:6px;padding:6px;margin:4px 0;cursor:pointer}
.tool b{color:#7cc0f4}.tool small{display:block;color:#8fa3b8}
#login{position:fixed;inset:0;background:#0009;display:none;align-items:center;justify-content:center;z-index:9}
#login div{background:#1b222b;padding:24px;border-radius:12px;display:flex;flex-direction:column;gap:10px}
#login input{background:#232b36;color:#dfe6ee;border:1px solid #334052;border-radius:8px;padding:10px}</style></head>
<body>
<div id="top"><b>АГЕНТ v12</b><span id="hdr"></span><span style="flex:1"></span>
<button data-act="showlog">Лог</button><button data-act="panel">Панель</button><button data-act="showpro">👤</button><button data-act="showchat">💬</button> <button data-act="logout">Выйти</button></div>
<div id="chat"></div>
<div id="panel"></div>
<div id="inp"><input id="q" placeholder="Задача для АГЕНТА... (Enter) | Ctrl+V — вставить скриншот">
<button data-act="snap">📷</button><button data-act="send">Спросить</button><span id="spin" class="spin" style="display:none"></span></div>
<div id="login"><div>
<input id="lg" placeholder="логин"><input id="pw" type="password" placeholder="пароль">
<button data-act="login">Войти</button><button data-act="reg">Регистрация</button></div></div>
<div id="pro" style="display:none;position:fixed;inset:0;background:#0009;align-items:center;justify-content:center;z-index:10">
<div style="background:#1b222b;padding:24px;border-radius:12px;width:340px;display:flex;flex-direction:column;gap:10px;border:1px solid #334052">
<b>👤 ПРОФИЛЬ</b><span id="proinfo" style="color:#9fb0c3;font-size:13px"></span>
<input id="pname" placeholder="Новое имя" style="background:#232b36;color:#dfe6ee;border:1px solid #334052;border-radius:6px;padding:8px">
<button data-act="savename" style="background:#2b4a6f;color:#fff;border:0;border-radius:6px;padding:8px;cursor:pointer">Сохранить имя</button>
<input id="pold" type="password" placeholder="Старый пароль" style="background:#232b36;color:#dfe6ee;border:1px solid #334052;border-radius:6px;padding:8px">
<input id="pnew" type="password" placeholder="Новый пароль (мин 4)" style="background:#232b36;color:#dfe6ee;border:1px solid #334052;border-radius:6px;padding:8px">
<button data-act="savepw" style="background:#2b4a6f;color:#fff;border:0;border-radius:6px;padding:8px;cursor:pointer">Сменить пароль</button>
<button id="adm_btn" data-act="openadm" style="display:none;background:#4a6f2b;color:#fff;border:0;border-radius:6px;padding:8px;cursor:pointer;margin-top:6px">👥 Админка</button>
<button data-act="closepro" style="background:#334052;color:#fff;border:0;border-radius:6px;padding:8px;cursor:pointer">Закрыть</button>
</div></div>
<div id="adm" style="display:none;position:fixed;inset:0;background:#0009;align-items:center;justify-content:center;z-index:10">
<div style="background:#1b222b;padding:24px;border-radius:12px;width:520px;max-height:80%;overflow:auto;display:flex;flex-direction:column;gap:8px;border:1px solid #334052">
<b>👥 АДМИНКА: пользователи</b><div id="ulist" style="max-height:40%;overflow:auto"></div>
<div style="display:flex;gap:6px;flex-wrap:wrap">
<input id="nlog" placeholder="логин" style="background:#232b36;color:#dfe6ee;border:1px solid #334052;border-radius:6px;padding:8px">
<input id="npw" type="password" placeholder="пароль" style="background:#232b36;color:#dfe6ee;border:1px solid #334052;border-radius:6px;padding:8px">
<select id="nrole" style="background:#232b36;color:#dfe6ee;border:1px solid #334052;border-radius:6px;padding:8px"></select>
<button data-act="adduser" style="background:#2b4a6f;color:#fff;border:0;border-radius:6px;padding:8px;cursor:pointer">+ добавить</button>
</div>
<button data-act="closeadm" style="background:#334052;color:#fff;border:0;border-radius:6px;padding:8px;cursor:pointer;margin-top:6px">Закрыть</button>
</div></div>
<div id="chatbox" style="display:none;position:fixed;top:44px;left:0;bottom:0;width:340px;background:#171d26;border-right:1px solid #243040;padding:10px;z-index:6;flex-direction:column;gap:8px">
<b>💬 КОМАНДА</b><div id="cmsg" style="flex:1;overflow:auto;display:flex;flex-direction:column;gap:6px"></div>
<div style="display:flex;gap:6px"><input id="cin" placeholder="Сообщение всем..." style="flex:1;background:#232b36;color:#dfe6ee;border:1px solid #334052;border-radius:6px;padding:8px">
<button data-act="chatsend" style="background:#2b4a6f;color:#fff;border:0;border-radius:6px;padding:8px;cursor:pointer">➤</button></div>
</div>
<script>
var TK=localStorage.getItem('tk')||'',IMG=null,CURM='';
var chat=document.getElementById('chat'),panel=document.getElementById('panel'),
qinp=document.getElementById('q'),login=document.getElementById('login'),
hdr=document.getElementById('hdr'),lg=document.getElementById('lg'),pw=document.getElementById('pw');
function J(u,b){return fetch(u,{method:b?'POST':'GET',headers:{'Content-Type':'application/json','X-Token':TK||''},body:b?JSON.stringify(b):undefined}).then(function(r){return r.json()})}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function att(s){return esc(s).replace(/"/g,'&quot;')}
function addMsg(html,me){var d=document.createElement('div');d.className='msg'+(me?' me':'');d.innerHTML=html;chat.appendChild(d);chat.scrollTop=chat.scrollHeight;return d}
function showLogin(){login.style.display='flex'}
function send(){var q=qinp.value;if(!q)return;qinp.value='';addMsg(esc(q),true);var d=addMsg('🤔 думаю...');var sp=document.getElementById('spin');if(sp)sp.style.display='inline-block';
J('/ask',{token:TK,q:q,image:IMG}).then(function(r){if(sp)sp.style.display='none';if(r&&r.error){localStorage.removeItem('tk');TK='';showLogin();d.innerHTML='⚠ нужен вход';return}IMG=null;render(d,r)}).catch(function(e){if(sp)sp.style.display='none';d.innerHTML='ошибка: '+esc(e)})}
function render(d,r){var h='';
if(r.think)h+='<div class="think" data-act="think">🧠 размышления (клик)</div><div class="thinkbody" style="display:none">'+esc(r.think)+'</div>';
if(r.log&&r.log.length)h+='<div class="log">🔎 ХОД РАБОТЫ:\n'+r.log.map(esc).join('\n')+'</div>';
h+='<div>'+esc(String(r.answer).replace(/<\/?think>/g,''))+'</div>';
var m=String(r.answer).match(/id (\d+)/);
if(String(r.answer).indexOf('[СОГЛАСОВАНИЕ]')>=0&&m)h+='<div style="margin-top:8px"><button data-act="appr" data-pid="'+m[1]+'" data-ok="1">✅ выполнить</button> <button data-act="appr" data-pid="'+m[1]+'" data-ok="0">❌ отмена</button></div>';
d.innerHTML=h;chat.scrollTop=chat.scrollHeight}
function buildPanel(p){var h='<div class="grp"><h4 data-act="fold">▸ ⚙ ДЕЙСТВИЯ (без ИИ)</h4><div class="gbody" style="display:none">';
p.actions.forEach(function(a){h+='<div class="tool" data-act="act" data-val="'+a.endpoint+'"><b>'+esc(a.label)+'</b></div>'});h+='</div></div>';
h+='<div class="grp"><h4 data-act="fold">▸ 🧠 МОДЕЛЬ ИИ (клик — смена)</h4><div class="gbody" style="display:none">';
p.models.forEach(function(m){h+='<div class="tool" data-act="setm" data-val="'+att(m)+'">'+esc(m)+(m==CURM?' ←':'')+'</div>'});h+='</div></div>';
h+='<div class="grp"><h4 data-act="fold">▸ ⚡ БЫСТРЫЕ ЗАДАЧИ</h4><div class="gbody" style="display:none">';
p.chips.forEach(function(c){h+='<div class="tool" data-act="chip" data-val="'+att(c)+'">'+esc(c)+'</div>'});h+='</div></div>';
p.groups.forEach(function(g){h+='<div class="grp"><h4 data-act="fold">▸ '+esc(g.title)+' ('+g.tools.length+')</h4><div class="gbody" style="display:none">';
g.tools.forEach(function(t){h+='<div class="tool" data-act="chip" data-val="'+att(t.name)+'"><b>'+esc(t.name)+(t.approval?' 🔒':'')+'</b><small>'+esc(t.desc)+'</small></div>'});h+='</div></div>'});
panel.innerHTML=h}
function buildSettings(s){var h='<div class="grp"><h4 data-act="fold">▸  НАСТРОЙКИ (ползунки)</h4><div class="gbody">';
s.items.forEach(function(it){h+='<div class="tool"><small>'+esc(it.space)+' · '+esc(it.name)+'</small>';
if(it.kind=='range'){h+='<input type="range" data-cfg="'+att(it.key)+'" min="'+it.min+'" max="'+it.max+'" step="'+it.step+'" value="'+it.value+'" style="width:100%"><b data-v="'+att(it.key)+'"> '+it.value+'</b>';}
else if(it.kind=='check'){h+='<input type="checkbox" data-cfg="'+att(it.key)+'" '+(it.value?'checked':'')+'>';}
else{h+='<input data-cfg="'+att(it.key)+'" value="'+att(String(it.value))+'" style="width:100%;background:#232b36;color:#dfe6ee;border:1px solid #334052;border-radius:6px;padding:4px">';}
h+='</div>';});
h+='</div></div>';panel.innerHTML+=h;}
function init(){J('/status').then(function(s){CURM=s.model;var u=localStorage.getItem('usr')||'';hdr.textContent=s.host+(u?' | '+u:'')+' | '+s.model+' | блоков: '+s.blocks;J('/panel').then(function(p){buildPanel(p);J('/settings').then(buildSettings)})})}
document.addEventListener('click',function(e){var el=e.target.closest('[data-act]');if(!el)return;var a=el.getAttribute('data-act');
if(a=='think'){var n=el.nextElementSibling;n.style.display=n.style.display=='none'?'block':'none'}
else if(a=='fold'){var b=el.nextElementSibling;var hid=b.style.display=='none';b.style.display=hid?'block':'none';el.textContent=(hid?'▾':'▸')+el.textContent.slice(1)}
else if(a=='send')send();
else if(a=='snap')J('/snap',{token:TK}).then(function(r){addMsg(esc(r.msg||'ок'))});
else if(a=='showlog')J('/log').then(function(r){addMsg('<div class="log">'+esc(r.log)+'</div>')});
else if(a=='panel')panel.style.display=panel.style.display=='none'?'block':'none';
else if(a=='logout'){localStorage.removeItem('tk');TK='';showLogin()}
else if(a=='showpro'){J('/profile',{token:TK}).then(function(u){document.getElementById('proinfo').textContent=(u.display_name||'')+' · '+(u.role||'')+' · '+u.login;document.getElementById('pname').value=u.display_name||'';document.getElementById('pro').style.display='flex';document.getElementById('adm_btn').style.display=u.can_manage?'block':'none'})}
else if(a=='closepro'){document.getElementById('pro').style.display='none'}
else if(a=='savename'){var v=document.getElementById('pname').value;J('/setname',{token:TK,name:v}).then(function(r){alert(r.msg||'ок');if(r.ok){document.getElementById('pro').style.display='none';init()}})}
else if(a=='savepw'){J('/setpw',{token:TK,old:document.getElementById('pold').value,'new':document.getElementById('pnew').value}).then(function(r){alert(r.msg||'ок');if(r.ok){document.getElementById('pold').value='';document.getElementById('pnew').value=''}})}
else if(a=='openadm'){document.getElementById('pro').style.display='none';document.getElementById('adm').style.display='flex';J('/admin/users',{token:TK,op:'list'}).then(function(r){var out='';(r.users||[]).forEach(function(u){out+='<div style="padding:6px;background:#202834;border-radius:6px;margin:3px 0;display:flex;gap:6px;align-items:center"><b>'+esc(u.display_name)+'</b> <small style="color:#8fa3b8">('+esc(u.login)+')</small> ';out+='<select class="rsel" data-login="'+att(u.login)+'" style="background:#232b36;color:#dfe6ee;border:1px solid #334052;border-radius:4px;padding:4px">';(r.roles||[]).forEach(function(role){out+='<option'+(role===u.role?' selected':'')+'>'+esc(role)+'</option>'});out+='</select> ';out+='<button data-act="do_role" data-login="'+att(u.login)+'" style="background:#2b4a6f;color:#fff;border:0;border-radius:4px;padding:4px 8px;cursor:pointer">роль</button> ';out+='<button data-act="do_resetpw" data-login="'+att(u.login)+'" style="background:#6f4a2b;color:#fff;border:0;border-radius:4px;padding:4px 8px;cursor:pointer">сброс pw</button></div>'});document.getElementById('ulist').innerHTML=out||'(пусто)';var sel=document.getElementById('nrole');if(sel)sel.innerHTML=(r.roles||[]).map(function(x){return '<option>'+esc(x)+'</option>'}).join('')})}
else if(a=='closeadm'){document.getElementById('adm').style.display='none'}
else if(a=='do_role'){var lgn=el.getAttribute('data-login');var sel=document.querySelector('.rsel[data-login="'+lgn+'"]');J('/admin/users',{token:TK,op:'role',login:lgn,role:sel.value}).then(function(r){alert(r.msg||'ок')})}
else if(a=='do_resetpw'){var lgn=el.getAttribute('data-login');var nw=prompt('Новый пароль для '+lgn+' (мин 4):');if(nw)J('/admin/users',{token:TK,op:'resetpw',login:lgn,pw:nw}).then(function(r){alert(r.msg||'ок')})}
else if(a=='adduser'){J('/admin/users',{token:TK,op:'add',login:document.getElementById('nlog').value,pw:document.getElementById('npw').value,role:document.getElementById('nrole').value}).then(function(r){alert(r.msg||'ок');if(r.ok){document.getElementById('nlog').value='';document.getElementById('npw').value='';document.getElementById('adm').style.display='none';setTimeout(function(){document.getElementById('adm').style.display='flex';document.querySelector('[data-act="openadm"]').click()},100)}})}

else if(a=='login')J('/login',{login:document.getElementById('lg').value,pw:document.getElementById('pw').value}).catch(function(e){alert('сервер недоступен: '+e);throw e}).then(function(r){if(r.ok){TK=r.token;localStorage.setItem('tk',TK);localStorage.setItem('usr',lg.value);login.style.display='none';init()}else alert('неверный логин или пароль')});
else if(a=='reg')J('/register',{login:lg.value,pw:pw.value}).then(function(r){alert(r.msg||'ок')});
else if(a=='appr'){var sp2=document.getElementById('spin');if(sp2)sp2.style.display='inline-block';J('/approve',{token:TK,pid:el.getAttribute('data-pid'),ok:el.getAttribute('data-ok')=='1'}).then(function(r){if(sp2)sp2.style.display='none';addMsg(esc((r.res||'')+((r.answer&&r.answer!==r.res)?'\n\n'+r.answer:'')))});}
else if(a=='setm')J('/setmodel',{token:TK,model:el.getAttribute('data-val')}).then(function(){init()});
else if(a=='act'){var ep=el.getAttribute('data-val');if(ep=='/log'){J('/log').then(function(r){addMsg('<div class="log">'+esc(r.log)+'</div>')})}else J(ep,{token:TK}).then(function(r){addMsg('<div class="log">'+esc(JSON.stringify(r).slice(0,800))+'</div>')})}
else if(a=='chip'){qinp.value=el.getAttribute('data-val');send()}
else if(a=='showchat'){var cb=document.getElementById('chatbox');if(cb.style.display=='flex'){cb.style.display='none';if(CTMR){clearInterval(CTMR);CTMR=null}}else{cb.style.display='flex';CLAST=0;document.getElementById('cmsg').innerHTML='';chatPoll();if(CTMR)clearInterval(CTMR);CTMR=setInterval(chatPoll,5000);NEWMSG=0;chatBadge()}}
else if(a=='closechat'){document.getElementById('chatbox').style.display='none';if(CTMR){clearInterval(CTMR);CTMR=null}}
else if(a=='chatsend'){var t=document.getElementById('cin').value;J('/chat/send',{token:TK,text:t}).then(function(r){if(r.ok)document.getElementById('cin').value='';chatPoll()})}});
var CLAST=0,CTMR=null;
function chatRender(ms){var box=document.getElementById('cmsg');ms.forEach(function(m){if(m.id<=CLAST)return;CLAST=m.id;var d=document.createElement('div');d.style.cssText='background:#202834;border-radius:6px;padding:6px 8px';d.innerHTML='<b style="color:#7cc0f4">'+esc(m.name)+'</b> <small style="color:#8fa3b8">'+esc(m.ts)+'</small><br>'+esc(m.text);box.appendChild(d)});box.scrollTop=box.scrollHeight}
function chatPoll(){J('/chat/poll',{token:TK,last:CLAST}).then(function(r){chatRender(r.msgs||[])})}
var NEWMSG=0;
function chatBadge(){var b=document.querySelector('[data-act="showchat"]');if(b)b.textContent=NEWMSG>0?'💬'+NEWMSG:'💬'}
setInterval(function(){if(document.getElementById('chatbox').style.display!='flex'&&TK){J('/chat/poll',{token:TK,last:CLAST}).then(function(r){var ms=r.msgs||[];if(ms.length){NEWMSG+=ms.length;chatBadge()}})}},15000)
qinp.addEventListener('keydown' ,function(e){if(e.key=='Enter')send()});
document.addEventListener('paste',function(e){var it=null,items=e.clipboardData.items;for(var i=0;i<items.length;i++){if(items[i].type.indexOf('image')==0){it=items[i];break}}if(!it)return;var f=it.getAsFile();var rd=new FileReader();rd.onload=function(){IMG=rd.result.split(',')[1];addMsg('📷 скриншот прикреплён',true)};rd.readAsDataURL(f)});
lg.addEventListener('keydown',function(e){if(e.key=='Enter')document.querySelector('[data-act="login"]').click()});
pw.addEventListener('keydown',function(e){if(e.key=='Enter')document.querySelector('[data-act="login"]').click()});
document.getElementById('cin').addEventListener('keydown',function(e){if(e.key=='Enter')document.querySelector('[data-act="chatsend"]').click()});
if(TK)init();else showLogin();
(function(){var sp=document.getElementById('spin');if(!sp)return;var of=window.fetch;window.fetch=function(){sp.style.display='inline-block';return of.apply(this,arguments).finally(function(){sp.style.display='none';});};})();
</script></body></html>"""

class Hd(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _j(self, d, code=200):
        b = json.dumps(d, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)
    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        try: return json.loads(self.rfile.read(n) or b"{}")
        except Exception: return {}
    def _client(self, b):
        u = users.token_info(b.get("token") or "")
        return u["login"] if u else None
    def do_GET(self):
        p = urlparse(self.path).path
        if p == "/status":
            token = self.headers.get("X-Token") or ""
            cl2 = users.token_info(token)
            prof = users.get_profile(cl2["login"]) if cl2 else None
            self._j({"host": HOSTNAME, "model": settings.get("llm_model"), "blocks": len(TR.BLOCKS), "tools": len(TR.TOOLS), "user": prof, "is_manager": users.can_manage_users(prof["login"]) if prof else False})
        elif p == "/panel":
            self._j(panel.build())
        elif p == "/log":
            try:
                txt = core.LOGF.read_text(encoding="utf-8", errors="ignore").splitlines()
                self._j({"log": "\n".join(txt[-80:])})
            except Exception:
                self._j({"log": "лога нет"})
        elif p == "/settings":
            self._j({"items": settings.list_ui()})
        elif p == "/fleet/info":
            import os as _os
            tail = ""
            try:
                jf = core.REPO / "Трейлы" / "TRAIL_JOURNAL.md"
                if jf.exists():
                    tail = "\n".join(jf.read_text(encoding="utf-8", errors="ignore").splitlines()[-8:])
            except Exception:
                tail = ""
            self._j({"host": HOSTNAME, "user": _os.environ.get("USERNAME", ""),
                     "model": settings.get("llm_model"), "blocks": len(TR.BLOCKS),
                     "tools": len(TR.TOOLS), "trails": tail})
        else:
            b = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
    def do_POST(self):
        p = urlparse(self.path).path
        b = self._body()
        if p == "/login":
            r = users.check_login(b.get("login"), b.get("pw"))
            self._j(r or {"ok": False}); return
        if p == "/register":
            okf = users.add_user(b.get("login"), b.get("pw"))
            self._j({"msg": "пользователь создан" if okf else "логин занят или пустой"}); return
        cl = self._client(b)
        if not cl:
            self._j({"error": "нужен вход"}, 401); return
        if p == "/ask":
            self._j(ask(b.get("q") or "", cl, b.get("image")))
        elif p == "/approve":
            self._j(do_approve(b.get("pid"), b.get("ok")))
        elif p == "/setmodel":
            settings.set_val("llm_model", b.get("model")); self._j({"ok": True})
        elif p == "/setauto":
            settings.set_val("auto_mode", 1 if b.get("on") else 0); self._j({"ok": True})
        elif p == "/setcfg":
            settings.set_val(b.get("key"), b.get("value")); self._j({"ok": True})
        elif p == "/snap":
            self._j({"msg": "скриншот принимается через Ctrl+V в поле ввода"})
        elif p == "/rescan":
            threading.Thread(target=scanner.index_all, daemon=True).start()
            self._j({"msg": "переиндексация запущена"})
        elif p == "/scan":
            threading.Thread(target=scanner.scan_models, daemon=True).start()
            self._j({"msg": "скан моделей запущен"})
        elif p == "/profile":
            __prof = users.get_profile(cl)
            if __prof:
                __prof = dict(__prof)
                __prof["can_manage"] = users.can_manage_users(cl)
            self._j(__prof or {"error": "нет профиля"})
        elif p == "/setname":
            okf, msg = users.update_display_name(cl, b.get("name"))
            self._j({"ok": okf, "msg": msg})
        elif p == "/setpw":
            okf, msg = users.change_password(cl, b.get("old") or "", b.get("new") or "")
            self._j({"ok": okf, "msg": msg})
        elif p == "/chat/send":
            self._j(chat_tools.chat_send(cl, b.get("text")))
        elif p == "/chat/poll":
            self._j({"msgs": chat_tools.chat_poll(b.get("last") or 0)})
        elif p == "/admin/users":
            if not users.can_manage_users(cl):
                self._j({"error": "нет прав"}, 403); return
            op = b.get("op")
            if op == "list":
                self._j({"users": users.list_users(), "roles": users.ROLES})
            elif op == "role":
                okf, msg = users.admin_set_role(b.get("login") or "", b.get("role") or "")
                self._j({"ok": okf, "msg": msg})
            elif op == "add":
                okf = users.add_user(b.get("login") or "", b.get("pw") or "", b.get("role") or "Инженер")
                self._j({"ok": okf, "msg": "создан" if okf else "логин занят или пустой"})
            elif op == "resetpw":
                okf, msg = users.admin_reset_password(b.get("login") or "", b.get("pw") or "")
                self._j({"ok": okf, "msg": msg})
            else:
                self._j({"error": "неизвестная op"}, 400)
        else:
            self._j({"error": "не знаю"}, 404)

if __name__ == "__main__":
    import os, atexit
    log("=== старт АГЕНТ v12 на %s ===" % HOSTNAME)
    pidfile = core.BASE / "agent.pid"
    pidfile.write_text(str(os.getpid()), encoding="ascii")
    atexit.register(lambda: pidfile.unlink(missing_ok=True))
    try:
        ThreadingHTTPServer((HOST, PORT), Hd).serve_forever()
    finally:
        try: pidfile.unlink(missing_ok=True)
        except Exception: pass