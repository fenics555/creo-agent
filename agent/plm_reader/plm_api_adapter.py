# -*- coding: utf-8 -*-
"""plm_api_adapter.py — АДАПТЕР API для PLM READER (боевой, переносимый).

Собирает API из каркаса `plm_api.py` и регистрирует команды PLM (группы A-E):
  A: status                        (ping/schema отдаёт сам каркас)
  B: settings_get/settings_spec + settings_set/settings_reset
  C: db_info/db_stats/db_tables/db_query/db_doctor + db_backup/db_repair
  D: log_list/log_tail/window_state
  E: op_where/op_tree/op_changes/op_check + scan_start/scan_status

ПРАВИЛА ДОМА (эстафета §3, паспорт класса Р):
  - настройки — только через plm_settings (реестр SETTINGS_SPEC), бэкап перед записью;
  - база — только через plm_database; запись в Z:/UNC запрещена;
  - файлы Creo читает ТОЛЬКО plm_scanner.py (API их не читает);
  - модули PLM — РЯДОМ (HERE), путей-дисков нет → переживает миграцию.

Запуск (внутри процесса окна):  api = build_api(); api.start()
"""
import importlib.util
import os
import shutil
import sys
import time

from plm_api import AgentApi, CommandError

HERE = os.path.dirname(os.path.abspath(__file__))   # папка PLM Reader


def _load(name):
    """Загрузить модуль PLM (plm_settings/plm_database/engine) из папки программы.

    Папка PLM в sys.path: движок внутри делает `import plm_database` (грабля №13).
    """
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    path = os.path.join(HERE, name + '.py')
    spec = importlib.util.spec_from_file_location(name + '_api', path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name + '_api'] = mod
    spec.loader.exec_module(mod)
    return mod


def _mods(api):
    if not hasattr(api, '_mods'):
        api._mods = {}
    return api._mods


def _mod(api, name):
    """Модуль PLM по имени (ленивая загрузка + кэш)."""
    m = _mods(api)
    if name not in m:
        m[name] = _load(name)
    return m[name]


def _version():
    try:
        import plm_reader
        return str(getattr(plm_reader, 'APP_VERSION', '?'))
    except Exception:  # noqa: BLE001
        return '?'


def _spec_index(ps):
    idx = {}
    for item in ps.SETTINGS_SPEC:
        g, k, lab, t, lo, hi = item
        idx[k] = (g, lab, t, lo, hi)
    return idx


def _coerce(value, t, lo, hi, key):
    if t == 'bool':
        if isinstance(value, str):
            return value.strip().lower() in ('1', 'true', 'да', 'yes', 'on')
        return bool(value)
    if t == 'int':
        try:
            v = int(value)
        except (TypeError, ValueError):
            raise CommandError('значение «%s» не целое для %s' % (value, key))
        if isinstance(lo, int) and isinstance(hi, int) and not (lo <= v <= hi):
            raise CommandError('%s: %d вне границ [%d..%d]' % (key, v, lo, hi))
        return v
    if t == 'choice':
        if isinstance(lo, list) and value not in lo:
            raise CommandError('%s: «%s» не из %s' % (key, value, lo))
        return value
    if t == 'list':
        if isinstance(value, list):
            return value
        return [x.strip() for x in str(value).split(',') if x.strip()]
    return '' if value is None else str(value)


def _db_path(api):
    eng = _mod(api, 'engine')
    return eng.active_db()


def _is_writable(path):
    """Запись в Z:/сетевые/UNC запрещена. Локальный путь — можно."""
    if not path:
        return False
    p = os.path.abspath(path)
    if p.startswith('\\\\'):
        return False
    drive = os.path.splitdrive(p)[0].upper()
    return not drive.startswith('Z')


# ---------- A: жизнь/состояние ----------
def h_status(cmd, api):
    ps = api._ps
    settings = ps.load_settings_file()
    db = settings.get('db_dir') or ''
    return {'ok': True, 'name': 'plm_reader', 'version': _version(),
            'settings_file': ps.SETTINGS_FILE,
            'settings_count': len(settings),
            'db_dir': db, 'folders': settings.get('folders', [])}


# ---------- B: настройки ----------
def h_settings_get(cmd, api):
    ps = api._ps
    settings = ps.load_settings_file()
    key = cmd.get('key')
    if key:
        if key not in settings:
            raise CommandError('нет настройки: %s' % key, code='not_found')
        return {'ok': True, 'key': key, 'value': settings[key]}
    return {'ok': True, 'count': len(settings), 'settings': settings}


def h_settings_spec(cmd, api):
    ps = api._ps
    return {'ok': True, 'count': len(ps.SETTINGS_SPEC), 'spec': ps.settings_spec_json()}


def h_settings_set(cmd, api):
    ps = api._ps
    key = cmd.get('key')
    if not key:
        raise CommandError('нет key')
    idx = _spec_index(ps)
    if key not in idx:
        raise CommandError('ключ «%s» не в реестре SETTINGS_SPEC' % key, code='not_in_spec')
    g, lab, t, lo, hi = idx[key]
    if t == 'special':
        raise CommandError('«%s» — special (правится спец-секцией окна)' % key)
    new_val = _coerce(cmd.get('value'), t, lo, hi, key)
    settings = ps.load_settings_file()
    old_val = settings.get(key)
    backup = None
    try:
        if os.path.isfile(ps.SETTINGS_FILE):
            backup = ps.SETTINGS_FILE + '.pre_' + time.strftime('%Y%m%d_%H%M%S')
            shutil.copy2(ps.SETTINGS_FILE, backup)
    except OSError as exc:
        raise CommandError('бэкап не удался: %s' % exc, code='backup_failed')
    settings[key] = new_val
    if not ps.save_settings_file(settings):
        raise CommandError('save_settings_file вернул False', code='save_failed')
    return {'ok': True, 'key': key, 'old': old_val, 'new': new_val,
            'type': t, 'backup': backup, 'applied': True}


def h_settings_reset(cmd, api):
    ps = api._ps
    key = cmd.get('key')
    if not key:
        raise CommandError('нет key')
    if key not in ps.DEFAULT_SETTINGS:
        raise CommandError('нет умолчания для «%s»' % key, code='no_default')
    settings = ps.load_settings_file()
    old_val = settings.get(key)
    settings[key] = ps.DEFAULT_SETTINGS[key]
    if not ps.save_settings_file(settings):
        raise CommandError('save_settings_file вернул False', code='save_failed')
    return {'ok': True, 'key': key, 'old': old_val,
            'new': ps.DEFAULT_SETTINGS[key], 'applied': True}


# ---------- C: база данных ----------
def _tables(cur):
    return [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()]


def h_db_info(cmd, api):
    d = _mod(api, 'plm_database')
    path = _db_path(api)
    if not path or not os.path.isfile(path):
        raise CommandError('боевая база не найдена: %s' % path, code='no_db')
    con = d.connect_safe(path)
    try:
        n = len(_tables(con.cursor()))
    finally:
        con.close()
    return {'ok': True, 'db': path, 'size_mb': round(os.path.getsize(path) / 1048576, 1),
            'tables': n, 'writable': _is_writable(path)}


def h_db_stats(cmd, api):
    d = _mod(api, 'plm_database')
    path = _db_path(api)
    con = d.connect_safe(path)
    counts = {}
    try:
        cur = con.cursor()
        for n in _tables(cur):
            try:
                counts[n] = cur.execute('SELECT COUNT(*) FROM [%s]' % n).fetchone()[0]
            except Exception:  # noqa: BLE001
                counts[n] = None
    finally:
        con.close()
    return {'ok': True, 'db': path, 'count': len(counts), 'tables': counts}


def h_db_tables(cmd, api):
    d = _mod(api, 'plm_database')
    path = _db_path(api)
    con = d.connect_safe(path)
    out = {}
    try:
        cur = con.cursor()
        names = _tables(cur)          # ВАЖНО: материализуем ДО вложенных PRAGMA
        for n in names:
            out[n] = [r[1] for r in cur.execute('PRAGMA table_info([%s])' % n).fetchall()]
    finally:
        con.close()
    return {'ok': True, 'count': len(out), 'tables': out}


def h_db_query(cmd, api):
    d = _mod(api, 'plm_database')
    q = (cmd.get('query') or '').strip()
    if not q:
        raise CommandError('нет query')
    low = q.lower().lstrip()
    if not (low.startswith('select') or low.startswith('with') or low.startswith('pragma')):
        raise CommandError('разрешён только SELECT/WITH/PRAGMA', code='not_select')
    limit = max(1, min(int(cmd.get('limit') or 100), 5000))
    con = d.connect_safe(_db_path(api))
    try:
        cur = con.cursor()
        cur.execute(q)
        cols = [c[0] for c in cur.description] if cur.description else []
        rows = cur.fetchmany(limit)
    finally:
        con.close()
    return {'ok': True, 'columns': cols, 'rows': [list(r) for r in rows],
            'returned': len(rows), 'limit': limit}


def h_db_doctor(cmd, api):
    d = _mod(api, 'plm_database')
    return {'ok': True, 'doctor': d.doctor(db_path=_db_path(api), as_json=True)}


def h_db_backup(cmd, api):
    d = _mod(api, 'plm_database')
    return {'ok': True, 'backup': str(d.backup())}


def h_db_repair(cmd, api):
    d = _mod(api, 'plm_database')
    dry = not bool(cmd.get('apply'))
    res = d.repair(db_path=_db_path(api), dry_run=dry, quiet=True)
    return {'ok': True, 'dry_run': dry, 'result': str(res)[:2000]}


# ---------- D: логи/окно ----------
def _log_dir():
    """Папка логов дома для PLM (паспорт класса Р п.3): D:\\AI\\log\\plm_reader."""
    return os.path.join('D:\\AI\\log', 'plm_reader')


def h_log_list(cmd, api):
    out = []
    for d in (_log_dir(), HERE):
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if f.lower().endswith(('.log', '.txt')):
                    p = os.path.join(d, f)
                    out.append({'name': f, 'dir': d, 'size': os.path.getsize(p),
                                'mtime': os.path.getmtime(p)})
    out.sort(key=lambda x: x['mtime'], reverse=True)
    return {'ok': True, 'count': len(out), 'logs': out[:50]}


def h_log_tail(cmd, api):
    n = max(1, min(int(cmd.get('lines') or 50), 2000))
    name = cmd.get('name')
    if not name:
        r = h_log_list({}, api)
        if not r['logs']:
            raise CommandError('логов не найдено', code='no_logs')
        name, d = r['logs'][0]['name'], r['logs'][0]['dir']
    else:
        d = cmd.get('dir') or _log_dir()
    path = os.path.join(d, name)
    if not os.path.isfile(path):
        raise CommandError('лог не найден: %s' % path, code='no_log')
    with open(path, encoding='utf-8', errors='replace') as fh:
        lines = fh.readlines()
    return {'ok': True, 'file': path, 'total_lines': len(lines),
            'returned': min(n, len(lines)), 'lines': [x.rstrip('\n') for x in lines[-n:]]}


def h_window_state(cmd, api):
    """window_state — снимок состояния: настройки + база + идёт ли скан."""
    ps = api._ps
    settings = ps.load_settings_file()
    state = _mods(api).get('_scan', {'running': False})
    return {'ok': True, 'scan_running': state.get('running', False),
            'db': _db_path(api), 'folders': settings.get('folders', []),
            'recurse': settings.get('recurse'),
            'latest_only': settings.get('latest_only'),
            'show_limit': settings.get('show_limit'),
            'settings_count': len(settings)}


# ---------- E: операции через движок ----------
def _capture(fn, *args, **kwargs):
    """Вызвать функцию движка, перехватив её stdout (исполнитель = сам движок)."""
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            fn(*args, **kwargs)
        except SystemExit:
            pass
        except Exception as exc:  # noqa: BLE001
            buf.write('\n[ошибка] %s: %s' % (type(exc).__name__, exc))
    return buf.getvalue()


def h_op_where(cmd, api):
    model = cmd.get('model')
    if not model:
        raise CommandError('нет model')
    return {'ok': True, 'model': model, 'out': _capture(_mod(api, 'engine').do_where, model)}


def h_op_tree(cmd, api):
    model = cmd.get('model')
    if not model:
        raise CommandError('нет model')
    depth = int(cmd.get('depth') or 4)
    return {'ok': True, 'model': model, 'depth': depth,
            'out': _capture(_mod(api, 'engine').do_tree, model, depth)}


def h_op_changes(cmd, api):
    n = int(cmd.get('n') or 40)
    return {'ok': True, 'n': n, 'out': _capture(_mod(api, 'engine').do_changes, n)}


def h_op_check(cmd, api):
    return {'ok': True, 'out': _capture(_mod(api, 'engine').do_check, None)}


def h_scan_start(cmd, api):
    """scan_start — запустить скан (write; фоном, не блокирует API)."""
    import threading
    eng = _mod(api, 'engine')
    settings = api._ps.load_settings_file()
    roots = cmd.get('roots') or settings.get('folders') or []
    max_mb = settings.get('max_size_mb', 8)
    state = _mods(api).setdefault('_scan', {'running': False, 'log': ''})

    def _run():
        state['running'] = True
        try:
            state['log'] = _capture(eng.scan_to_base, roots, max_mb, 0, None,
                                    full=bool(cmd.get('full')),
                                    exclude=settings.get('exclude') or [],
                                    recurse=settings.get('recurse', True),
                                    latest_only=settings.get('latest_only', True))
        finally:
            state['running'] = False

    if state['running']:
        return {'ok': False, 'cmd': 'scan_start', 'error': 'скан уже идёт'}
    threading.Thread(target=_run, name='plm_scan', daemon=True).start()
    return {'ok': True, 'started': True, 'roots': roots, 'max_mb': max_mb}


def h_scan_status(cmd, api):
    state = _mods(api).get('_scan', {'running': False, 'log': ''})
    return {'ok': True, 'running': state.get('running', False),
            'tail': (state.get('log') or '')[-2000:]}


def build_api(base_dir=None, log=None):
    """Собрать API PLM Reader (21 команда A-E)."""
    api = AgentApi(name='plm_reader', version=_version(), base_dir=base_dir, log=log)
    api._ps = _load('plm_settings')
    # A
    api.add('status', h_status, doc='состояние: версия, файл/число настроек, база')
    # B
    api.add('settings_get', h_settings_get, doc='настройки (key|все)', meta={'key': 'строка|пусто'})
    api.add('settings_spec', h_settings_spec, doc='реестр настроек (группы/типы)')
    api.add('settings_set', h_settings_set, doc='ЗАПИСАТЬ настройку (apply; бэкап)',
            read=False, meta={'key': 'строка', 'value': 'по типу', 'apply': 'true'})
    api.add('settings_reset', h_settings_reset, doc='настройка к умолчанию (apply)',
            read=False, meta={'key': 'строка', 'apply': 'true'})
    # C
    api.add('db_info', h_db_info, doc='путь/размер/таблицы/writable')
    api.add('db_stats', h_db_stats, doc='счётчики по таблицам')
    api.add('db_tables', h_db_tables, doc='таблицы с колонками')
    api.add('db_query', h_db_query, doc='ТОЛЬКО SELECT (limit)',
            meta={'query': 'SQL SELECT', 'limit': 'число'})
    api.add('db_doctor', h_db_doctor, doc='аудит базы')
    api.add('db_backup', h_db_backup, doc='бэкап базы (apply)', read=False)
    api.add('db_repair', h_db_repair, doc='починка (dry-run по умолчанию)', read=False,
            meta={'apply': 'true'})
    # D
    api.add('log_list', h_log_list, doc='какие логи есть')
    api.add('log_tail', h_log_tail, doc='последние N строк',
            meta={'name': 'файл|пусто', 'lines': 'число'})
    api.add('window_state', h_window_state, doc='снимок состояния')
    # E
    api.add('op_where', h_op_where, doc='где используется модель', meta={'model': 'имя'})
    api.add('op_tree', h_op_tree, doc='состав вниз', meta={'model': 'имя', 'depth': 'число'})
    api.add('op_changes', h_op_changes, doc='журнал изменений', meta={'n': 'число'})
    api.add('op_check', h_op_check, doc='актуально/нужен скан')
    api.add('scan_start', h_scan_start, doc='запустить скан (apply; фоном)', read=False,
            meta={'roots': 'список|из настроек', 'full': 'bool', 'apply': 'true'})
    api.add('scan_status', h_scan_status, doc='идёт ли скан')
    return api


if __name__ == '__main__':
    a = build_api()
    print('PLM API: команд →', len(a.schema()))
    for c in a.schema():
        print('  %-16s %s%s' % (c['cmd'], c['doc'], '  [WRITE]' if c['write'] else ''))



