import loop
'АГЕНТ v15 — agent.py (полная сборка)\nThreadingHTTPServer + стриминг токенов + параллельные инструменты + планировщик.\nВитрина живёт в data/ui/index.html; константы PAGE больше нет.\n'
import json, re, os, socket, threading, time, datetime
from concurrent.futures import ThreadPoolExecutor
import subprocess, sys
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import core
from core import log, trace
import settings
import pdf_tools
import urllib.request as _ur
core.post = loop._stream_post
core.post = loop._post_think_off
import tools_registry as TR
import scanner
import users
import chat_tools
import panel
import vision_tools as VI
HOST, PORT = ('0.0.0.0', 8765)
HOSTNAME = socket.gethostname()
UI_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui', 'index.html')
_UI_CACHE = [0, b'']
STUB_PAGE = "<html><head><meta charset='utf-8'><title>АГЕНТ v15</title></head><body style='background:#1B1C1E;color:#E8E8E8;font:14px Segoe UI,sans-serif;padding:40px'><h2>ВИТРИНА НЕ НАЙДЕНА</h2><p>Положи index.html в D:\\AI\\tools\\agent\\data\\ui\\</p></body></html>"

def _scheduler():
    last_day = ''
    while True:
        try:
            now = datetime.datetime.now()
            if settings.get('night_enable'):
                hh = int(settings.get('night_hour') or 2)
                mm = int(settings.get('night_minute') or 0)
                if now.hour == hh and now.minute == mm and (now.strftime('%Y-%m-%d') != last_day):
                    last_day = now.strftime('%Y-%m-%d')
                    for t in str(settings.get('night_tasks') or 'scan,index,usage').split(','):
                        t = t.strip()
                        log('night start: %s' % t)
                        try:
                            if t == 'scan':
                                scanner.scan_models()
                            elif t == 'index':
                                scanner.index_all()
                            elif t == 'check':
                                subprocess.run([sys.executable, 'D:\\AI\\tools\\agent\\dev\\skills_check.py'], cwd='D:\\AI\\tools\\agent')
                            elif t == 'usage':
                                import usage_tools
                                usage_tools.build_usage(True)
                            elif t == 'backup':
                                import backup
                                backup._do()
                                import backup_tools
                                log(backup_tools.tool_housekeeping())
                                log(backup_tools.tool_drift_check())
                            elif t == 'drafts':
                                import draft_tools
                                log(draft_tools.tool_drafts_build())
                        except Exception as e:
                            log('night %s err: %s' % (t, e))
                        else:
                            log('night ok: %s' % t)
                    log('night run done')
        except Exception:
            pass
        time.sleep(30)

def _wd_port(port, host='127.0.0.1'):
    import socket as _s
    try:
        with _s.create_connection((host, port), timeout=2):
            return True
    except Exception:
        return False

def _wd_spawn(cmd):
    if not cmd:
        return False
    try:
        subprocess.Popen(cmd if isinstance(cmd, list) else cmd, shell=isinstance(cmd, str), cwd='D:\\AI\\tools\\agent', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return True
    except Exception:
        return False

def _watchdog():
    fails = {}
    while True:
        try:
            if int(settings.get('wd_enable') or 1):
                for name, port, key, dflt in (('ollama', 11434, 'wd_ollama_cmd', 'ollama serve'), ('creoson', 8080, 'wd_creoson_cmd', '')):
                    if not _wd_port(port):
                        n = fails.get(name, 0) + 1
                        fails[name] = n
                        if n <= 3:
                            log('wd: %s down, raising (%d)' % (name, n))
                            _wd_spawn(settings.get(key) or dflt)
                        elif n == 4:
                            log('wd: %s still down, cooldown' % name)
                    else:
                        fails[name] = 0
        except Exception:
            pass
        time.sleep(int(settings.get('wd_interval') or 60))

def _serve_ui(handler):
    try:
        mt = int(os.path.getmtime(UI_FILE))
        if _UI_CACHE[0] != mt:
            _UI_CACHE[0] = mt
            _UI_CACHE[1] = open(UI_FILE, 'rb').read()
        b = _UI_CACHE[1]
    except Exception:
        b = STUB_PAGE.encode('utf-8')
    handler.send_response(200)
    handler.send_header('Content-Type', 'text/html; charset=utf-8')
    handler.send_header('Cache-Control', 'no-cache')
    handler.send_header('Content-Length', str(len(b)))
    handler.end_headers()
    handler.wfile.write(b)

class Hd(BaseHTTPRequestHandler):

    def log_message(self, *a):
        pass

    def _j(self, d, code=200):
        b = json.dumps(d, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _body(self):
        n = int(self.headers.get('Content-Length') or 0)
        raw = self.rfile.read(n) or b'{}'
        try:
            return json.loads(raw)
        except Exception:
            s = raw.decode('utf-8-sig', 'ignore')
            if s.lstrip().startswith('{'):
                try:
                    return json.loads(s.replace('\\"', '"'))
                except Exception:
                    return {}
            return {}

    def _client(self, b):
        u = users.token_info(b.get('token') or self.headers.get('X-Token') or '')
        return u['login'] if u else None

    def do_GET(self):
        p = urlparse(self.path).path
        if p == '/status':
            token = self.headers.get('X-Token') or ''
            cl2 = users.token_info(token)
            prof = users.get_profile(cl2['login']) if cl2 else None
            tail = ''
            if cl2:
                try:
                    jf = core.REPO / 'Трейлы' / 'TRAIL_JOURNAL.md'
                    if jf.exists():
                        tail = '\n'.join(jf.read_text(encoding='utf-8', errors='ignore').splitlines()[-8:])
                except Exception:
                    tail = ''

            def _alive(p_):
                try:
                    s_ = socket.create_connection(('127.0.0.1', p_), timeout=1)
                    s_.close()
                    return True
                except Exception:
                    return False
            self._j({'host': HOSTNAME, 'model': settings.get('llm_model'), 'blocks': len(TR.BLOCKS), 'tools': len(TR.TOOLS), 'user': prof, 'is_manager': users.can_manage_users(prof['login']) if prof else False, 'trails': tail, 'mode': settings.get_for(cl2['login'], 'chat_mode', 1) if cl2 else 1, 'up_ollama': _alive(11434), 'up_creoson': _alive(8080), 'up_agent': True})
            return
        elif p == '/health':
            if not users.token_info(self.headers.get('X-Token') or ''):
                return self._j({'error': 'no token'})
            self._j({'ollama': _wd_port(11434), 'creoson': _wd_port(8080), 'agent': True})
            return
        elif p == '/pdfpages':
            if not users.token_info(self.headers.get('X-Token') or ''):
                return self._j({'error': 'no token'})
            qs = parse_qs(urlparse(self.path).query)
            name = qs.get('name', [''])[0]
            if not name:
                return self._j({'error': 'no name'})
            self._j(pdf_tools.pdf_pages(name))
            return
        elif p == '/pdfimg':
            if not users.token_info(self.headers.get('X-Token') or ''):
                return self._j({'error': 'no token'})
            qs = parse_qs(urlparse(self.path).query)
            name = qs.get('name', [''])[0]
            page = qs.get('page', ['1'])[0]
            if not name:
                return self._j({'error': 'no name'})
            self._j(pdf_tools.pdf_img(name, page))
            return
        elif p == '/pdfstatus':
            if not users.token_info(self.headers.get('X-Token') or ''):
                return self._j({'error': 'no token'})
            qs = parse_qs(urlparse(self.path).query)
            name = qs.get('name', [''])[0]
            if not name:
                return self._j({'error': 'no name'})
            self._j(pdf_tools.pdf_status(name))
            return
        elif p == '/children':
            if not users.token_info(self.headers.get('X-Token') or ''):
                return self._j({'error': 'no token'})
            qs = parse_qs(urlparse(self.path).query)
            name = qs.get('name', [''])[0]
            if not name:
                return self._j({'error': 'no name'})
            out = []
            try:
                c = core.db()
                for sql in ('SELECT child FROM usage WHERE parent LIKE ?', 'SELECT child FROM bom WHERE parent LIKE ?', 'SELECT child FROM links WHERE parent LIKE ?'):
                    try:
                        rows = c.execute(sql, ('%' + name + '%',)).fetchall()
                        out = [r[0] for r in rows]
                    except Exception:
                        continue
                    if out:
                        break
                c.close()
            except Exception as e:
                self._j({'error': str(e)})
                return
            self._j({'name': name, 'children': out[:200]})
            return
        elif p == '/graph/data':
            if not users.token_info(self.headers.get('X-Token') or ''):
                return self._j({'error': 'no token'})
            qs = parse_qs(urlparse(self.path).query)
            name = qs.get('name', [''])[0]
            if not name:
                return self._j({'error': 'no name'})
            import graph_tools
            self._j(graph_tools.build_graph(name))
            return
        elif p == '/graph':
            if not users.token_info(self.headers.get('X-Token') or ''):
                self.send_response(401)
                self.end_headers()
                return
            b = open(os.path.join(os.path.dirname(__file__), 'ui', 'graph.html'), 'rb').read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return
        elif p == '/map/data':
            if not users.token_info(self.headers.get('X-Token') or ''):
                return self._j({'error': 'no token'})
            qs = parse_qs(urlparse(self.path).query)
            top = int(qs.get('top', ['100'])[0])
            import map_tools
            self._j(map_tools.build_map(top))
            return
        elif p == '/map':
            if not users.token_info(self.headers.get('X-Token') or ''):
                self.send_response(401)
                self.end_headers()
                return
            b = open(os.path.join(os.path.dirname(__file__), 'ui', 'map.html'), 'rb').read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return
        elif p == '/pdfregistry':
            if not users.token_info(self.headers.get('X-Token') or ''):
                return self._j({'error': 'no token'})
            try:
                c = core.db()
                rows = c.execute('SELECT path, mtime FROM files').fetchall()
                c.close()
            except Exception as e:
                self._j({'error': str(e)})
                return
            bydir = {}
            for path, mt in rows:
                bydir.setdefault(os.path.dirname(path), {})[os.path.basename(path).lower()] = (path, mt)
            pairs = []
            for d, fs in bydir.items():
                du = d.upper()
                if '\\CREO12\\' in du or '\\DATA\\' in du:
                    continue
                for nm, (path, mt) in fs.items():
                    if nm in seen_names:
                        continue
                    verdict, entry = (None, {})
                    m = re.search('(.*?)\\.(drw|asm|prt)(\\.\\\\d+)?$', nm, re.I)
                    if m:
                        core, ext, suffix = m.groups()
                        suffix = suffix or ''
                        if ext.lower() == 'drw':
                            stem = core
                            pdf = fs.get(stem + '.pdf')
                            verdict = 'нет pdf' if not pdf else 'актуален' if pdf[1] >= mt else 'УСТАРЕЛ'
                            entry = {'name': nm, 'dir': d, 'drw': path, 'pdf': pdf[0] if pdf else '', 'drw_mtime': mt, 'pdf_mtime': pdf[1] if pdf else 0, 'verdict': verdict}
                        else:
                            drw = fs.get(core + '.drw' + suffix)
                            pdf = fs.get(core + '.pdf')
                            if drw:
                                drw_p, drw_mt = drw
                                if pdf:
                                    pdf_p, pdf_mt = pdf
                                    v = 'актуален' if pdf_mt >= drw_mt else 'устарел'
                                    verdict = f'pdf через чертёж {core}.drw{suffix}: {v}'
                                else:
                                    verdict = f'чертёж {core}.drw{suffix}: нет pdf'
                                    pdf_p, pdf_mt = ('', 0)
                                entry = {'name': nm, 'dir': d, 'drw': drw_p, 'pdf': pdf_p, 'drw_mtime': drw_mt, 'pdf_mtime': pdf_mt, 'verdict': verdict}
                            else:
                                verdict = 'чертежа нет'
                                entry = {'name': nm, 'dir': d, 'drw': '', 'pdf': '', 'drw_mtime': 0, 'pdf_mtime': 0, 'verdict': verdict}
                    if verdict:
                        pairs.append(entry)
                        seen_names.add(nm)
                        if len(pairs) >= 500:
                            break
                if len(pairs) >= 500:
                    break
            pairs.sort(key=lambda r: (r['verdict'] != 'УСТАРЕЛ', r['name']))
            self._j({'pairs': pairs, 'total': len(pairs)})
            return
        elif p == '/pdfthumb':
            _tk = users.token_info(self.headers.get('X-Token') or self.headers.get('query', {}).get('token', ''))
            if not _tk:
                self._j({'error': 'token required'})
                return
            qs = parse_qs(urlparse(self.path).query)
            nm = qs.get('name', [None])[0]
            pg = qs.get('page', ['1'])[0]
            res = pdf_tools.pdf_img(nm, pg)
            if 'error' in res:
                self._j({'error': 'миниатюры нет'})
                return
            img_path = res['image_path']
            try:
                with open(img_path, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'image/png')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self._j({'error': f'failed to serve image: {e}'})
            return
            d = panel.build()
            _ui = users.token_info(self.headers.get('X-Token') or '')
            if not (_ui and users.is_admin(_ui['login'])):
                d['groups'] = [g for g in d.get('groups', []) if 'НАСТРОЙКИ' not in str(g.get('title', '')).upper()]
                d.pop('settings', None)
            self._j(d)
            return
        elif p == '/log':
            _tk = users.token_info(self.headers.get('X-Token') or '')
            if _tk and (not users.is_admin(_tk['login'])):
                c = core.db()
                rows = c.execute('SELECT q,a,ts FROM history WHERE client=? ORDER BY id DESC LIMIT 40', (_tk['login'],)).fetchall()
                c.close()
                self._j({'log': '\n'.join(('%s · %s → %s' % (ts[:16], q, a[:80]) for q, a, ts in reversed(rows))) or 'история пуста'})
                return
            else:
                try:
                    txt = core.LOGF.read_text(encoding='utf-8', errors='ignore').splitlines()
                    self._j({'log': '\n'.join(txt[-80:])})
                    return
                except Exception:
                    self._j({'log': 'лога нет'})
                    return
        elif p == '/settings':
            self._j({'items': settings.list_ui()})
            return
        elif p == '/livetoks':
            _cl6 = users.token_info(self.headers.get('X-Token') or '')
            qs = parse_qs(urlparse(self.path).query)
            last = int((qs.get('last') or ['0'])[0])
            toks = loop.LIVE_TOK.get(_cl6['login'] if _cl6 else '', [])
            self._j({'toks': toks[last:], 'last': len(toks)})
            return
        elif p == '/livethink':
            _cl7 = users.token_info(self.headers.get('X-Token') or '')
            qs7 = parse_qs(urlparse(self.path).query)
            last7 = int((qs7.get('last') or ['0'])[0])
            ths = loop.LIVE_THINK.get(_cl7['login'] if _cl7 else '', [])
            self._j({'toks': ths[last7:], 'last': len(ths)})
            return
        elif p == '/livesteps':
            _cl4 = users.token_info(self.headers.get('X-Token') or '')
            qs = parse_qs(urlparse(self.path).query)
            last = int((qs.get('last') or ['0'])[0])
            lines = loop.LIVE.get(_cl4['login'] if _cl4 else '', [])
            self._j({'lines': lines[last:], 'last': len(lines)})
            return
        elif p == '/fleet/info':
            if not users.token_info(self.headers.get('X-Token') or ''):
                self._j({'error': 'нужен вход'}, code=401)
                return
            tail = ''
            try:
                jf = core.REPO / 'Трейлы' / 'TRAIL_JOURNAL.md'
                if jf.exists():
                    tail = '\n'.join(jf.read_text(encoding='utf-8', errors='ignore').splitlines()[-10:])
            except Exception:
                pass
            self._j({'tail': tail})
            return
        elif p == '/ui/app.js':
            try:
                b = open(os.path.join(os.path.dirname(__file__), 'ui', 'app.js'), 'rb').read()
            except Exception:
                self._j({'error': 'app.js not found'})
                return
            self.send_response(200)
            self.send_header('Content-Type', 'text/javascript; charset=utf-8')
            self.send_header('Content-Length', str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return
        else:
            _serve_ui(self)

    def do_POST(self):
        p = urlparse(self.path).path
        b = self._body()
        if p == '/login':
            r = users.check_login(b.get('login'), b.get('pw') or b.get('password'))
            self._j(r or {'ok': False})
            return
        if p == '/register':
            okf = users.add_user(b.get('login'), b.get('pw') or b.get('password'))
            self._j({'msg': 'пользователь создан' if okf else 'логин занят или пустой'})
            return
        cl = self._client(b)
        if not cl:
            self._j({'error': 'нужен вход'}, 401)
            return
        if p == '/ask':
            self._j(loop.ask(b.get('q') or '', cl, b.get('image'), mode=b.get('mode')))
        elif p == '/ask_stream':
            import queue as _q
            qq = _q.Queue()
            holder = {}

            def _cb(line):
                qq.put(line)

            def _run():
                try:
                    holder['r'] = loop.ask(b.get('q') or '', cl, b.get('image'), on_step=_cb, mode=b.get('mode'))
                except Exception as e:
                    holder['r'] = {'answer': 'ошибка: %s' % e, 'log': []}
                finally:
                    qq.put(None)
            threading.Thread(target=_run, daemon=True).start()
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            while True:
                item = qq.get()
                if item is None:
                    break
                self.wfile.write(('data: %s\n\n' % json.dumps({'step': item}, ensure_ascii=False)).encode())
                self.wfile.flush()
            self.wfile.write(('data: %s\n\n' % json.dumps({'done': holder.get('r', {})}, ensure_ascii=False)).encode())
            self.wfile.flush()
            return
        elif p == '/approve':
            self._j(loop.do_approve(b.get('pid'), b.get('ok')))
        elif p == '/wiz_preview':
            import copy_tools as _cp37
            self._j(_cp37.preview(old=b.get('old') or '', new=b.get('new') or '', template=b.get('template') or '', family=b.get('family', 1), drawings=b.get('drawings', 0)))
        elif p == '/wiz_rename_preview':
            import rename_tools as _rn37
            self._j(_rn37.build_plan(old=b.get('old') or '', new=b.get('new') or '', drawings=b.get('drawings', 1)))
        elif p == '/setmodel':
            import panel as _pn
            ok_names = _pn.models()
            want = b.get('model') or ''
            if want not in ok_names:
                self._j({'ok': False, 'error': 'нет такой модели', 'models': ok_names}, 400)
                return
            settings.set_val('llm_model', want)
            self._j({'ok': True})
        elif p == '/setauto':
            settings.set_val('auto_mode', 1 if b.get('on') else 0)
            self._j({'ok': True})
        elif p == '/feedback':
            try:
                c = core.db()
                c.execute('CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, client TEXT, query TEXT, think TEXT, tool TEXT, result TEXT, ok INTEGER, comment TEXT)')
                c.execute('INSERT INTO feedback(ts,client,query,think,tool,result,ok,comment) VALUES(?,?,?,?,?,?,?,?)', (datetime.datetime.now().isoformat(), cl, (b.get('query') or '')[:2000], (b.get('think') or '')[:2000], (b.get('tool') or '')[:120], (b.get('result') or '')[:2000], 1 if b.get('ok') else 0, (b.get('comment') or '')[:500]))
                c.commit()
                c.close()
            except Exception as e:
                self._j({'ok': False, 'msg': 'оценка не сохранена: %s' % e}, 500)
                return
            self._j({'ok': True, 'msg': 'оценка сохранена'})
        elif p == '/setcfg':
            if (b.get('key') or '') in settings.PERSONAL_KEYS:
                settings.set_for(cl, b.get('key'), b.get('value'))
                self._j({'ok': True})
                return
            if not users.is_admin(cl):
                self._j({'error': 'настройки — только админ'}, 403)
                return
            settings.set_val(b.get('key'), b.get('value'))
            loop._SYS_CACHE.clear()
            self._j({'ok': True})
        elif p == '/snap':
            self._j({'msg': 'скриншот принимается через Ctrl+V в поле ввода'})
        elif p == '/rescan':
            subprocess.Popen([sys.executable, '-c', 'import scanner; scanner.index_all()'], cwd='D:\\AI\\tools\\agent')
            self._j({'msg': 'переиндексация запущена'})
        elif p == '/scan':
            subprocess.Popen([sys.executable, '-c', 'import scanner; scanner.scan_models()'], cwd='D:\\AI\\tools\\agent')
            self._j({'msg': 'скан моделей запущен'})
        elif p == '/profile':
            __prof = users.get_profile(cl)
            if __prof:
                __prof = dict(__prof)
                __prof['can_manage'] = users.can_manage_users(cl)
            self._j(__prof or {'error': 'нет профиля'})
        elif p == '/setname':
            okf, msg = users.update_display_name(cl, b.get('name'))
            self._j({'ok': okf, 'msg': msg})
        elif p == '/setpw':
            okf, msg = users.change_password(cl, b.get('old') or '', b.get('new') or '')
            self._j({'ok': okf, 'msg': msg})
        elif p == '/chat/send':
            self._j(chat_tools.chat_send(cl, b.get('text')))
        elif p == '/chat/poll':
            self._j({'msgs': chat_tools.chat_poll(b.get('last') or 0)})
        elif p == '/admin/users':
            if not users.can_manage_users(cl):
                self._j({'error': 'нет прав'}, 403)
                return
            op = b.get('op')
            if op == 'list':
                self._j({'users': users.list_users(), 'roles': users.ROLES})
            elif op == 'role':
                okf, msg = users.admin_set_role(b.get('login') or '', b.get('role') or '')
                self._j({'ok': okf, 'msg': msg})
            elif op == 'add':
                okf = users.add_user(b.get('login') or '', b.get('pw') or b.get('password') or '', b.get('role') or 'Инженер')
                self._j({'ok': okf, 'msg': 'создан' if okf else 'логин занят или пустой'})
            elif op == 'delete':
                lg = (b.get('login') or '').strip()
                if not lg:
                    self._j({'ok': False, 'msg': 'логин пустой'}, 400)
                    return
                if lg == cl:
                    self._j({'ok': False, 'msg': 'нельзя удалить самого себя'}, 400)
                    return
                us = users.list_users()
                tgt = [x for x in us if x.get('login') == lg]
                if not tgt:
                    self._j({'ok': False, 'msg': 'логин %s не найден' % lg}, 404)
                    return
                adm = [x for x in us if x.get('role') == 'Администратор' and x.get('login') != lg]
                if tgt[0].get('role') == 'Администратор' and (not adm):
                    self._j({'ok': False, 'msg': 'нельзя удалить последнего администратора'}, 400)
                    return
                okf = users.admin_delete_user(lg)
                self._j({'ok': okf, 'msg': 'пользователь %s удалён' % lg if okf else 'ошибка удаления'})
            elif op == 'resetpw':
                okf, msg = users.admin_reset_password(b.get('login') or '', b.get('pw') or b.get('password') or '')
                self._j({'ok': okf, 'msg': msg})
            else:
                self._j({'error': 'неизвестная op'}, 400)
        else:
            self._j({'error': 'не знаю'}, 404)
if __name__ == '__main__':
    import atexit
    log('=== старт АГЕНТ v15 на %s ===' % HOSTNAME)
    pidfile = core.BASE / 'agent' / 'agent.pid'
    pidfile.write_text(str(os.getpid()), encoding='ascii')
    atexit.register(lambda: pidfile.unlink(missing_ok=True))
    threading.Thread(target=_scheduler, daemon=True).start()
    threading.Thread(target=_watchdog, daemon=True).start()
    try:
        ThreadingHTTPServer((HOST, PORT), Hd).serve_forever()
    finally:
        try:
            pidfile.unlink(missing_ok=True)
        except Exception:
            pass