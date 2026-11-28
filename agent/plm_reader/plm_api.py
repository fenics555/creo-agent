# -*- coding: utf-8 -*-
"""plm_api.py — API-КАРКАС PLM READER (управление без вспомогательных скриптов).

Идея: ИИ (или внешний вызов) кладёт JSON-команду в `api\\in\\<имя>.json` — PLM исполняет
её СВОИМ методом (как кнопку) и кладёт ответ в `api\\out\\<имя>.json`. Никаких скриптов-обёрток.

Образец-эталон: D:\\AI\\AGENT_SETTINGS\\checks\\stand_gui_v2.py (строки 2546-2760).
Дорожная карта: D:\\AI\\ЭСТАФЕТЫ\\PLAN_AGENT_API.md · эстафета: ESTAFETA_AGENT_API.md.

Переносимость: все пути — ОТНОСИТЕЛЬНО ЭТОГО ФАЙЛА (папка api\\ рядом с программой);
жёстких дисков нет (паспорт класса Р: миграция на другой ПК).
"""
import json
import os
import sys
import threading
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BASE = os.path.join(HERE, 'api')   # <папка программы>\\api\\in|out


class CommandError(Exception):
    """Ошибка исполнения команды: уходит в ответ как error, но НЕ роняет цикл."""
    def __init__(self, msg, code='bad_request'):
        super().__init__(msg)
        self.code = code


class AgentApi:
    """API-сервер подпрограммы: реестр команд + файловый транспорт + поток.

    api = AgentApi(name='plm_reader', version=APP_VERSION)
    api.add('ping', fn, doc='...')          # read по умолчанию
    api.add('settings_set', fn, doc='...', read=False)   # write (нужен apply)
    api.start(); ...; api.stop()
    """

    def __init__(self, name='program', version='0.0', base_dir=None,
                 poll=1.5, log=None):
        self.name = name
        self.version = version
        self.base = base_dir or DEFAULT_BASE
        self.din = os.path.join(self.base, 'in')
        self.dout = os.path.join(self.base, 'out')
        self.poll = float(poll)
        self._log_fn = log
        self._cmds = {}
        self._stop = False
        self._thread = None
        self._seq = 0
        self._lock = threading.Lock()
        self._journal = os.path.join(self.dout, '_api_journal.log')
        self._ensure_dirs()

    def _ensure_dirs(self):
        try:
            os.makedirs(self.din, exist_ok=True)
            os.makedirs(self.dout, exist_ok=True)
        except OSError:
            pass

    def _log(self, text, kind='info'):
        line = '%s %s' % (time.strftime('%H:%M:%S'), text)
        try:
            with open(self._journal, 'a', encoding='utf-8') as fh:
                fh.write(line + '\n')
        except OSError:
            pass
        if self._log_fn:
            try:
                self._log_fn(line)
            except Exception:  # noqa: BLE001
                pass

    def add(self, cmd, fn, doc='', read=True, meta=None):
        """Зарегистрировать команду. read=False => write (нужен флаг apply)."""
        self._cmds[str(cmd)] = {'fn': fn, 'doc': doc, 'read': bool(read),
                                'meta': meta or {}}
        return self

    def schema(self):
        """Самодокумент: список команд с параметрами и признаком write."""
        out = []
        for cmd in sorted(self._cmds):
            c = self._cmds[cmd]
            out.append({'cmd': cmd, 'doc': c['doc'],
                        'write': not c['read'], 'params': c['meta']})
        return out

    # ---------------- поток ----------------
    def start(self):
        if self._thread and self._thread.is_alive():
            return self
        self._ensure_dirs()
        self._stop = False
        self._thread = threading.Thread(target=self._loop, name='plm_api', daemon=True)
        self._thread.start()
        self._log('api start: %s %s (in=%s)' % (self.name, self.version, self.din))
        return self

    def stop(self):
        self._stop = True
        self._log('api stop: %s' % self.name)

    def _loop(self):
        while not self._stop:
            try:
                self.poll_once()
            except Exception as exc:  # noqa: BLE001  (цикл не падает)
                self._log('LOOP ERR %s: %s' % (type(exc).__name__, exc), 'err')
            time.sleep(self.poll)

    # ---------------- транспорт ----------------
    def poll_once(self):
        """Обработать все JSON-команды из in. Возвращает список ответов."""
        results = []
        try:
            files = sorted(f for f in os.listdir(self.din) if f.endswith('.json'))
        except OSError:
            return results
        for f in files:
            src = os.path.join(self.din, f)
            try:
                with open(src, encoding='utf-8') as fh:
                    cmd = json.load(fh)
            except Exception as exc:  # noqa: BLE001
                self._answer(f, {'ok': False, 'cmd': None, 'error': 'json: %s' % exc})
                self._unlink(src)
                continue
            res = self.exec(cmd)
            self._answer(f, res)
            results.append(res)
            self._unlink(src)
        return results

    def exec(self, cmd):
        """Исполнить команду. Ошибки -> ответ ok=False (не исключение наружу)."""
        act = str((cmd or {}).get('cmd') or '').lower()
        if not act:
            return {'ok': False, 'cmd': act, 'error': 'нет поля cmd'}
        if act == 'schema':
            return {'ok': True, 'cmd': act, 'name': self.name,
                    'version': self.version, 'commands': self.schema()}
        if act == 'ping':
            return {'ok': True, 'cmd': act, 'name': self.name,
                    'version': self.version, 'alive': True}
        spec = self._cmds.get(act)
        if spec is None:
            return {'ok': False, 'cmd': act, 'error': 'неизвестная команда: %s' % act}
        if not spec['read'] and not bool(cmd.get('apply')):
            return {'ok': False, 'cmd': act, 'dry_run': True,
                    'error': 'write-команда: нужен флаг "apply": true'}
        try:
            res = spec['fn'](cmd, self)
            if not isinstance(res, dict):
                res = {'result': res}
            res.setdefault('ok', True)
            res.setdefault('cmd', act)
            return res
        except CommandError as exc:
            return {'ok': False, 'cmd': act, 'error': str(exc), 'code': exc.code}
        except Exception as exc:  # noqa: BLE001
            self._log('EXEC ERR %s: %s' % (act, exc), 'err')
            return {'ok': False, 'cmd': act,
                    'error': '%s: %s' % (type(exc).__name__, exc),
                    'trace': traceback.format_exc(limit=3)}

    def _answer(self, name, res):
        """Записать ответ в out и журнал. Никогда не бросать наружу."""
        path = os.path.join(self.dout, name)
        try:
            tmp = path + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as fh:
                json.dump(res, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        except OSError:
            pass
        ok = res.get('ok')
        self._log('[API] %-14s -> %s' % (res.get('cmd'),
                  'OK' if ok else res.get('error')), 'ok' if ok else 'err')

    def _unlink(self, path):
        try:
            os.remove(path)
        except OSError:
            pass

    # ---------------- удобство (клиент) ----------------
    def send(self, cmd, **params):
        """Положить команду в in с монотонным именем. Возвращает имя файла."""
        with self._lock:
            self._seq += 1
            name = 'c%06d.json' % self._seq
        payload = {'cmd': cmd}
        payload.update(params)
        with open(os.path.join(self.din, name), 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, ensure_ascii=False)
        return name

    def receive(self, name, timeout=10.0):
        """Дождаться ответа по имени. None — таймаут."""
        path = os.path.join(self.dout, name)
        t0 = time.time()
        while time.time() - t0 < timeout:
            if os.path.exists(path):
                try:
                    with open(path, encoding='utf-8') as fh:
                        return json.load(fh)
                except (OSError, ValueError):
                    pass
            time.sleep(0.1)
        return None


if __name__ == '__main__':
    print('plm_api: каркас API PLM Reader. См. plm_api_adapter.py')

