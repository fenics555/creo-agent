/* app.js — витрина АГЕНТ v15 (23.11.2026): экраны, инструменты, программы, люди, журнал, настройки. */
var TK = localStorage.getItem('agent_token') || '';
var ME = null;
var BASE = '';
var TOOLS = [];
var CUR_TOOL = null;

function $(id) { return document.getElementById(id); }
function esc(s) {
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
function logOut(txt, cls) {
  var el = $('tool-result');
  if (!el) return;
  el.textContent = txt;
  el.style.color = cls === 'err' ? 'var(--err)' : 'var(--text)';
}
function api(path, body, cb, errCb) {
  var opts = { method: body ? 'POST' : 'GET', headers: { 'X-Token': TK } };
  if (body) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
  fetch(BASE + path, opts).then(function (r) {
    return r.text().then(function (t) {
      var d;
      try { d = JSON.parse(t); } catch (e) { d = { raw: t, status: r.status }; }
      if (!r.ok) { d.error = d.error || ('HTTP ' + r.status); if (errCb) errCb(d); return null; }
      return d;
    });
  }).then(function (d) { if (d && cb) cb(d); }).catch(function (e) { if (errCb) errCb({ error: e.message }); });
}
function hasToken() { return !!(TK && TK.length); }
function setTab(tabId) {
  document.querySelectorAll('.sb-item').forEach(function (i) {
    i.classList.toggle('active', i.getAttribute('data-tab') === tabId);
  });
  document.querySelectorAll('.screen').forEach(function (s) { s.classList.remove('active'); });
  var scr = $('screen-' + tabId);
  if (scr) scr.classList.add('active');
  if (tabId === 'overview') { loadStatus(); loadPrograms(true); }
  if (tabId === 'tools') loadTools();
  if (tabId === 'programs') loadPrograms();
  if (tabId === 'people') loadPeople();
  if (tabId === 'logs') loadLog();
  if (tabId === 'settings') loadSettings();
  if (tabId === 'chat') { var ci = $('chat-input'); if (ci) ci.focus(); }
}
function togglePanel(id) {
  var el = $(id);
  if (!el) return;
  el.style.display = (el.style.display === 'none' || !el.style.display) ? 'flex' : 'none';
}

/* ---------- статус и KPI ---------- */
function updateStatus(d) {
  if (!d) return;
  ME = d.user || ME;
  var model = d.model || '—';
  var ctx = d.model_ctx || d.ctx_requested || 0;
  var pill = $('pill-model'); if (pill) pill.innerHTML = 'модель: <b>' + esc(model) + '</b>';
  var pt = $('pill-tools'); if (pt) pt.innerHTML = 'инструментов: <b>' + (d.tools || 0) + '</b>';
  var kpiModel = $('kpi-model'); if (kpiModel) kpiModel.textContent = model;
  var kpiModelSub = $('kpi-model-sub');
  if (kpiModelSub) kpiModelSub.textContent = 'контекст ' + (ctx ? (ctx / 1024).toFixed(0) + 'k' : '—');
  var kpiTools = $('kpi-tools'); if (kpiTools) kpiTools.textContent = d.tools || 0;
  var kpiToolsSub = $('kpi-tools-sub'); if (kpiToolsSub) kpiToolsSub.textContent = 'блоков ' + (d.blocks || 0);
  var stModel = $('st-model'); if (stModel) stModel.textContent = model;
  var stCtx = $('st-ctx'); if (stCtx) stCtx.textContent = ctx ? (ctx / 1024).toFixed(0) + 'k' : '—';
  var stTools = $('st-tools'); if (stTools) stTools.textContent = d.tools || 0;
  var stBlocks = $('st-blocks'); if (stBlocks) stBlocks.textContent = d.blocks || 0;
  ['ollama', 'creoson', 'agent'].forEach(function (k) {
    var el = $('ind-' + k);
    if (!el) return;
    var on = k === 'agent' ? !!d.up_agent : (k === 'ollama' ? d.up_ollama : d.up_creoson);
    el.classList.toggle('up', on);
    el.classList.toggle('down', !on);
  });
  var svc = (d.up_ollama ? 1 : 0) + (d.up_creoson ? 1 : 0) + (d.up_agent ? 1 : 0);
  var svcEl = $('kpi-services'); if (svcEl) svcEl.textContent = svc + ' / 3';
  var svcSub = $('kpi-services-sub');
  if (svcSub) svcSub.textContent = 'Ollama ' + (d.up_ollama ? '✓' : '✗') +
    ' · CREOSON ' + (d.up_creoson ? '✓' : '✗ (по требованию)') + ' · агент ' + (d.up_agent ? '✓' : '✗');
  var ov = $('ov-updated');
  if (ov) ov.textContent = 'обновлено ' + new Date().toLocaleTimeString('ru-RU');
  if (d.user) {
    $('user-block').style.display = 'flex';
    $('user-name').textContent = d.user.display_name || d.user.login;
    var av = $('user-avatar');
    if (av) av.textContent = (d.user.display_name || d.user.login || '?').slice(0, 1).toUpperCase();
    var stU = $('st-user'); if (stU) stU.textContent = d.user.login;
    var stR = $('st-role'); if (stR) stR.textContent = d.user.role || '—';
  }
}
function loadStatus() { api('/status', null, function (d) { updateStatus(d); }); }

/* ---------- чат с агентом (/ask) ---------- */
function chatAdd(text, mine, meta) {
  var box = $('chat-msgs');
  var div = document.createElement('div');
  div.className = 'msg' + (mine ? ' me' : '');
  div.textContent = text;
  if (meta) {
    var m = document.createElement('span');
    m.className = 'meta';
    m.textContent = meta;
    div.appendChild(m);
  }
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  return div;
}
function chatSend() {
  var inp = $('chat-input');
  var text = (inp.value || '').trim();
  if (!text || !hasToken()) return;
  inp.value = '';
  chatAdd(text, true);
  var wait = chatAdd('…думаю', false);
  var t0 = Date.now();
  api('/ask', { q: text, mode: 1 }, function (d) {
    var secs = ((Date.now() - t0) / 1000).toFixed(1);
    wait.textContent = d.answer || '(пусто)';
    wait.className = 'msg';
    var meta = [];
    if (d.steps) meta.push('шагов: ' + d.steps);
    if (d.log && d.log.length) meta.push(String(d.log[0]).replace(/\s+/g, ' ').slice(0, 110));
    meta.push(secs + ' с');
    var m = document.createElement('span');
    m.className = 'meta';
    m.textContent = meta.join(' · ');
    wait.appendChild(m);
    $('st-last-time').textContent = secs + ' с';
    $('st-last-steps').textContent = d.steps || '—';
    var mm = (d.log || []).join(' ').match(/(\d+)\s*ток/);
    $('st-last-tokens').textContent = mm ? mm[1] + ' ток' : '—';
  }, function (e) {
    wait.textContent = 'ошибка: ' + (e.error || 'нет ответа');
    wait.className = 'msg';
    wait.style.borderColor = 'var(--err)';
  });
}
function chatStop() {
  api('/ask_cancel', {}, function () { chatAdd('— остановлено —', false); }, function () {});
}
function chatClear() {
  var box = $('chat-msgs');
  box.innerHTML = '';
  box.removeAttribute('data-board');
  chatAdd('Лента очищена. Спросите агента.', false);
}

/* ---------- инструменты ---------- */
function loadTools() {
  api('/api/tools', null, function (d) {
    TOOLS = d.tools || [];
    var cnt = $('tools-count');
    if (cnt) cnt.textContent = 'всего ' + TOOLS.length + ' · групп ' + ((d.groups || []).length);
    var sel = $('tool-group');
    if (sel && sel.options.length <= 1) {
      (d.groups || []).forEach(function (g) {
        var o = document.createElement('option');
        o.value = g.id; o.textContent = (g.title || g.id) + ' (' + g.n + ')';
        sel.appendChild(o);
      });
    }
    renderTools();
  }, function (e) { var l = $('tools-list'); if (l) l.innerHTML = '<div class="empty">' + esc(e.error) + '</div>'; });
}
function renderTools() {
  var q = ((($('tool-search') || {}).value) || '').toLowerCase().trim();
  var g = (($('tool-group') || {}).value) || '';
  var list = $('tools-list');
  if (!list) return;
  var rows = TOOLS.filter(function (t) {
    if (g && t.group !== g) return false;
    if (!q) return true;
    return (t.name + ' ' + (t.desc || '') + ' ' + (t.group || '') + ' ' + (t.kind || ''))
      .toLowerCase().indexOf(q) >= 0;
  });
  if (!rows.length) { list.innerHTML = '<div class="empty">Ничего не найдено</div>'; return; }
  list.innerHTML = rows.map(function (t) {
    var badges = '';
    if (t.approval) badges += '<span class="badge warn">согласование</span>';
    if (t.needs_creo) badges += '<span class="badge">Creo</span>';
    if (t.kind) badges += '<span class="badge">' + esc(t.kind) + '</span>';
    return '<div class="item" data-tool="' + esc(t.name) + '" style="cursor:pointer">' +
      '<div class="grow"><div class="name">' + esc(t.name) + '</div>' +
      '<div class="d">' + esc((t.desc || '').slice(0, 120)) + '</div></div>' +
      '<div class="row" style="gap:5px">' + badges + '</div></div>';
  }).join('');
  list.querySelectorAll('[data-tool]').forEach(function (el) {
    el.addEventListener('click', function () { selectTool(el.getAttribute('data-tool')); });
  });
}
function selectTool(name) {
  var t = TOOLS.filter(function (x) { return x.name === name; })[0];
  if (!t) return;
  CUR_TOOL = t;
  $('tool-run-title').textContent = t.name;
  var args = $('tool-args');
  var params = t.params || [];
  if (!params.length) {
    args.innerHTML = '<span style="color:var(--muted)">параметров нет — запускается сразу</span>';
  } else {
    args.innerHTML = params.map(function (p) {
      return '<div class="field"><label>' + esc(p) + '</label>' +
        '<input id="arg-' + esc(p) + '" placeholder="' + esc(p) + '"></div>';
    }).join('');
  }
  var b = $('tool-run-btn');
  b.disabled = false;
  b.textContent = 'Запустить ' + t.name;
  var badge = $('tool-run-badge');
  badge.textContent = (t.group || '') + (t.approval ? ' · согласование' : '');
  badge.className = 'badge' + (t.approval ? ' warn' : '');
  $('tool-result').textContent = 'Готов к запуску.';
}
/* ---------- программы ---------- */
var WINDOWS = [];

function loadWindows(cb) {
  if (WINDOWS.length) { if (cb) cb(); return; }
  api('/wiz_run_gui', { list: 'true' }, function (d) {
    WINDOWS = d.programs || [];
    if (cb) cb();
  }, function () { if (cb) cb(); });
}
function loadPrograms(brief) {
  api('/api/programs', null, function (d) {
    var list = d.programs || [];
    var cnt = $('programs-count');
    if (cnt) cnt.textContent = 'всего ' + list.length + ' · контрактов — tool.json';
    var pill = $('pill-programs');
    if (pill) pill.innerHTML = 'программ: <b>' + list.length + '</b>';
    var kpi = $('kpi-programs'); if (kpi) kpi.textContent = list.length;
    if (brief) {
      var box = $('ov-programs');
      if (box) {
        var top = list.slice(0, 8);
        box.innerHTML = top.map(function (p) {
          var st = p.pid ? '<span class="badge ok">работает</span>' : '<span class="badge">готова</span>';
          return '<div class="item"><div class="grow"><div class="t">' + esc(p.title) + '</div>' +
            '<div class="d">' + esc(p.engine || '') + '</div></div>' + st + '</div>';
        }).join('') || '<div class="empty">список пуст</div>';
      }
      return;
    }
    loadWindows(function () { renderPrograms(list); });
  });
}
function renderPrograms(list) {
  var q = ((($('programs-search') || {}).value) || '').toLowerCase().trim();
  var box = $('programs-list');
  if (!box) return;
  var rows = list.filter(function (p) {
    if (!q) return true;
    return (p.title + ' ' + p.id + ' ' + (p.group || '')).toLowerCase().indexOf(q) >= 0;
  });
  if (!rows.length) { box.innerHTML = '<div class="empty">Ничего не найдено</div>'; return; }
  box.innerHTML = rows.map(function (p) {
    var canWin = WINDOWS.indexOf(p.id) >= 0;
    var st = p.pid ? '<span class="badge ok">PID ' + p.pid + '</span>' : '<span class="badge">готова</span>';
    return '<div class="item"><div class="grow">' +
      '<div class="t">' + esc(p.title) + '</div>' +
      '<div class="d">движок: <span class="mono">' + esc(p.engine || '—') + '</span>' +
      (p.window ? ' · окно: ' + esc(p.window) : '') + '</div></div>' + st +
      '<div class="row" style="gap:6px">' +
      (canWin ? '<button class="btn sm" data-win="' + esc(p.id) + '">Открыть окно</button>' : '') +
      '<button class="btn sm" data-run="' + esc(p.id) + '">Запустить</button>' +
      '<button class="btn sm ghost" data-state="' + esc(p.id) + '">Журнал</button>' +
      '</div></div>';
  }).join('');
  box.querySelectorAll('[data-win]').forEach(function (b) {
    b.addEventListener('click', function () { openProgramWindow(b.getAttribute('data-win')); });
  });
  box.querySelectorAll('[data-run]').forEach(function (b) {
    b.addEventListener('click', function () { runProgram(b.getAttribute('data-run')); });
  });
  box.querySelectorAll('[data-state]').forEach(function (b) {
    b.addEventListener('click', function () { programState(b.getAttribute('data-state')); });
  });
}
function openProgramWindow(id) {
  api('/wiz_run_gui', { program: id }, function (d) {
    alert(d.msg || ('окно ' + id + ' запущено'));
  }, function (e) { alert('не открылось: ' + (e.error || 'нет окна')); });
}
function runProgram(id) {
  api('/prog_run', { prog_id: id, args: '' }, function (d) {
    alert((d.text || 'запущено').slice(0, 600));
  }, function (e) { alert('отказ: ' + (e.error || 'нет прав')); });
}
function programState(id) {
  api('/prog_state', { prog_id: id, tail: 30 }, function (d) {
    alert((d.text || '—').slice(0, 1500));
  }, function (e) { alert('нет данных: ' + (e.error || '')); });
}

/* ---------- люди ---------- */
function loadPeople() {
  api('/admin/users', { op: 'list' }, function (d) {
    var box = $('people-list');
    var roles = d.roles || [];
    var sel = $('new-role');
    if (sel && !sel.options.length) {
      roles.forEach(function (r) {
        var o = document.createElement('option'); o.value = r; o.textContent = r; sel.appendChild(o);
      });
    }
    box.innerHTML = (d.users || []).map(function (u) {
      return '<div class="item"><div class="grow"><div class="t">' + esc(u.login) + '</div>' +
        '<div class="d">роль: ' + esc(u.role) + ' · был: ' + esc(u.last_seen || '—') + '</div></div>' +
        '<select data-role-for="' + esc(u.login) + '">' +
        roles.map(function (r) {
          return '<option' + (r === u.role ? ' selected' : '') + '>' + esc(r) + '</option>';
        }).join('') + '</select>' +
        '<button class="btn sm" data-setrole="' + esc(u.login) + '">Сменить роль</button></div>';
    }).join('') || '<div class="empty">нет пользователей</div>';
    box.querySelectorAll('[data-setrole]').forEach(function (b) {
      b.addEventListener('click', function () {
        var lg = b.getAttribute('data-setrole');
        var selEl = box.querySelector('[data-role-for="' + lg + '"]');
        api('/admin/users', { op: 'role', login: lg, role: selEl.value }, function (r) {
          $('people-msg').textContent = r.msg || 'готово';
          loadPeople();
        }, function (e) { $('people-msg').textContent = 'отказ: ' + (e.error || ''); });
      });
    });
  }, function (e) {
    $('people-list').innerHTML = '<div class="empty">' + esc(e.error || 'нет прав') + '</div>';
  });
}
function addUser() {
  api('/admin/users', {
    op: 'add', login: ($('new-login').value || '').trim(),
    pw: $('new-pw').value, role: $('new-role').value
  }, function (d) {
    $('people-msg').textContent = d.msg || 'готово';
    $('new-login').value = ''; $('new-pw').value = '';
    loadPeople();
  }, function (e) { $('people-msg').textContent = 'отказ: ' + (e.error || ''); });
}

/* ---------- запуск инструмента (кнопка) ---------- */
function runTool() {
  if (!CUR_TOOL) return;
  var args = {};
  (CUR_TOOL.params || []).forEach(function (p) {
    var el = $('arg-' + p);
    var v = el ? el.value.trim() : '';
    if (v) args[p] = v;
  });
  var b = $('tool-run-btn');
  b.disabled = true;
  $('tool-result').textContent = 'Выполняю ' + CUR_TOOL.name + ' …';
  $('tool-result').style.color = 'var(--muted)';
  api('/tool', { name: CUR_TOOL.name, args: args }, function (d) {
    b.disabled = false;
    $('tool-result').style.color = 'var(--text)';
    $('tool-result').textContent = d.result || '(пусто)';
  }, function (e) {
    b.disabled = false;
    $('tool-result').style.color = 'var(--err)';
    $('tool-result').textContent = 'ОТКАЗ: ' + (e.error || 'нет прав');
  });
}

/* ---------- журнал ---------- */
function loadLog() {
  api('/log', null, function (d) {
    var el = $('log-body');
    if (el) el.textContent = d.log || '(пусто)';
    var up = $('log-updated');
    if (up) up.textContent = 'обновлено ' + new Date().toLocaleTimeString('ru-RU');
  });
}

/* ---------- настройки ---------- */
function loadSettings() {
  api('/settings', null, function (d) {
    var box = $('settings-list');
    var items = d.items || [];
    box.innerHTML = items.map(function (it, i) {
      var isBool = (it.type === 'bool') || it.kind === 'bool';
      var input = isBool
        ? '<select id="set-' + i + '"><option' + (it.value ? ' selected' : '') + '>да</option>' +
          '<option' + (!it.value ? ' selected' : '') + '>нет</option></select>'
        : '<input id="set-' + i + '" value="' + esc(it.value) + '">';
      return '<div class="item"><div class="grow"><div class="t">' + esc(it.name || it.key) + '</div>' +
        '<div class="d">' + esc(it.space || '') + ' · ' + esc(it.key) + ' — ' + esc(it.desc || '') + '</div></div>' +
        input + '<button class="btn sm" data-set="' + i + '">Применить</button></div>';
    }).join('') || '<div class="empty">настроек нет</div>';
    box.querySelectorAll('[data-set]').forEach(function (b) {
      b.addEventListener('click', function () {
        var i = parseInt(b.getAttribute('data-set'), 10);
        var it = items[i];
        var raw = $('set-' + i).value;
        var val = raw;
        if (it.type === 'int') val = parseInt(raw, 10) || 0;
        if (it.type === 'float') val = parseFloat(String(raw).replace(',', '.')) || 0;
        if (it.type === 'bool') val = (raw === 'да');
        api('/setcfg', { key: it.key, value: val }, function () {
          b.textContent = 'Готово'; setTimeout(function () { b.textContent = 'Применить'; }, 1200);
        }, function (e) {
          b.textContent = 'Отказ';
          b.title = e.error || '';
          setTimeout(function () { b.textContent = 'Применить'; }, 1600);
        });
      });
    });
  });
}

/* ---------- вход ---------- */
function showApp() {
  $('login-screen').style.display = 'none';
  $('app').style.display = 'flex';
  loadStatus();
  loadPrograms(true);
  if (!$('chat-msgs').children.length) {
    chatAdd('Здравствуйте. Я агент дома: спросите что угодно или откройте «Инструменты».', false);
  }
}
function login() {
  var lg = ($('login-login').value || '').trim();
  var pw = $('login-pw').value || '';
  $('login-err').style.display = 'none';
  api('/login', { login: lg, pw: pw }, function (d) {
    if (!d.ok) { $('login-err').style.display = 'block'; return; }
    TK = d.token;
    localStorage.setItem('agent_token', TK);
    ME = d;
    showApp();
  }, function () { $('login-err').style.display = 'block'; });
}
function register() {
  var lg = ($('login-login').value || '').trim();
  var pw = $('login-pw').value || '';
  api('/register', { login: lg, pw: pw }, function (d) {
    alert(d.msg || 'готово');
  }, function (e) { alert('регистрация: ' + (e.error || 'только админ')); });
}
function logout() {
  TK = ''; ME = null;
  localStorage.removeItem('agent_token');
  $('app').style.display = 'none';
  $('login-screen').style.display = 'flex';
  $('chat-msgs').innerHTML = '';
}

/* ---------- инициализация ---------- */
window.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.sb-item').forEach(function (i) {
    i.addEventListener('click', function () { setTab(i.getAttribute('data-tab')); });
  });
  $('btn-do-login').addEventListener('click', login);
  $('btn-do-reg').addEventListener('click', register);
  $('btn-logout').addEventListener('click', logout);
  $('login-pw').addEventListener('keydown', function (e) { if (e.key === 'Enter') login(); });
  $('btn-send').addEventListener('click', chatSend);
  $('btn-stop').addEventListener('click', chatStop);
  $('btn-clear-output').addEventListener('click', chatClear);
  $('btn-refresh').addEventListener('click', function () { loadStatus(); loadPrograms(true); });
  $('tool-search').addEventListener('input', renderTools);
  $('tool-group').addEventListener('change', renderTools);
  $('tool-run-btn').addEventListener('click', runTool);
  $('programs-search').addEventListener('input', function () { loadPrograms(); });
  $('people-refresh').addEventListener('click', loadPeople);
  $('btn-add-user').addEventListener('click', addUser);
  $('logs-refresh').addEventListener('click', loadLog);
  $('settings-refresh').addEventListener('click', loadSettings);
  document.addEventListener('keydown', function (e) {
    if (e.ctrlKey && e.key.toLowerCase() === 'k') {
      e.preventDefault(); setTab('tools');
      var f = $('tool-search'); if (f) f.focus();
    }
    if (e.ctrlKey && e.key === 'Enter') { e.preventDefault(); chatSend(); }
    if (e.key === 'Escape') chatStop();
  });
  if (hasToken()) showApp(); else $('login-screen').style.display = 'flex';
});