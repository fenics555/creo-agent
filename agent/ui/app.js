// АГЕНТ v15 — VS Code Style клиент
var TK = localStorage.getItem('tk') || '';
var base = '';
function $ (id) { return document.getElementById(id); }
function logOut(txt, cls) {
  var el = $('output-body');
  if (!el) return;
  var d = document.createElement('div');
  d.className = 'output-line ' + (cls || 'info');
  d.textContent = new Date().toLocaleTimeString() + ' ' + txt;
  el.appendChild(d);
  el.scrollTop = el.scrollHeight;
}
function api(path, body, cb, errCb) {
  var opts = { method: body ? 'POST' : 'GET', headers: { 'Content-Type': 'application/json', 'X-Token': TK || '' } };
  if (body) opts.body = JSON.stringify(body);
  fetch(base + path, opts).then(function (r) {
    var ct = r.headers.get('content-type') || '';
    if (ct.indexOf('application/json') < 0) {
      return r.text().then(function (t) { throw new Error('не JSON (' + r.status + '): ' + t.substring(0, 80)); });
    }
    return r.json();
  }).then(function (d) { if (cb) cb(d); }).catch(function (e) {
    if (errCb) errCb(e); else logOut('API error ' + path + ': ' + e, 'err');
  });
}
function hasToken() { return TK && TK.length > 0; }
function setTab(tabId) {
  document.querySelectorAll('.sb-item').forEach(function (i) { i.classList.remove('active'); });
  document.querySelector('[data-tab="' + tabId + '"]').classList.add('active');
  document.querySelectorAll('.tab-content').forEach(function (c) { c.classList.remove('active'); });
  $('tab-' + tabId).classList.add('active');
  var tabs = $('tabs');
  tabs.innerHTML = '<div class="tab active" data-tab="' + tabId + '">' + tabId + '</div>';
  logOut('Вкладка: ' + tabId);
}
function togglePanel(id) {
  var el = $(id);
  if (!el) return;
  el.classList.toggle('hidden');
}
function updateStatus(d) {
  if (!d) return;
  $('pill-model').textContent = 'модель: ' + (d.model || '—');
  $('pill-tools').textContent = 'инструментов: ' + (d.tools || '—');
  $('pill-programs').textContent = 'программ: —';
  var inds = { indollama: d.up_ollama, indcreoson: d.up_creoson, indagent: d.up_agent };
  Object.keys(inds).forEach(function (id) {
    var el = $(id);
    if (el) { el.className = 'indicator ' + (inds[id] ? '' : 'off'); el.textContent = el.textContent.replace(/ ●$/, '') + ' ●'; }
  });
  $('stat-agent').textContent = d.up_agent ? 'Жив' : 'Мёртв';
  $('stat-agent').className = 'val ' + (d.up_agent ? 'ok' : 'err');
  $('stat-ollama').textContent = d.up_ollama ? 'Жив' : 'Мёртв';
  $('stat-ollama').className = 'val ' + (d.up_ollama ? 'ok' : 'err');
  $('stat-creoson').textContent = d.up_creoson ? 'Жив' : 'Мёртв';
  $('stat-creoson').className = 'val ' + (d.up_creoson ? 'ok' : 'err');
  $('stat-model').textContent = d.model || '—';
  $('stat-tools').textContent = d.tools || '—';
  $('stat-blocks').textContent = d.blocks || '—';
  $('stat-ctx-req').textContent = d.ctx_requested || '—';
  $('stat-ctx-sess').textContent = d.ctx_session || '—';
  $('stat-mode').textContent = d.mode || '—';
  $('sb-time').textContent = new Date().toLocaleTimeString();
  $('sb-user').textContent = (d.user && d.user.login) ? d.user.login : '—';
}
function loadStatus() { api('/status', null, function (d) { updateStatus(d); }); }
function loadTools() { api('/api/tools', null, function (d) {
  var tb = $('tools-body');
  if (!tb) return;
  tb.innerHTML = '';
  if (!d || d.error) {
    tb.innerHTML = '<tr><td colspan="3" class="empty">Требуется вход в систему</td></tr>';
    $('stat-tools').textContent = '—';
    return;
  }
  var list = Array.isArray(d) ? d : (d.tools || []);
  if (list.length === 0) { tb.innerHTML = '<tr><td colspan="3" class="empty">Нет инструментов</td></tr>'; return; }
  list.forEach(function (t) {
    var tr = document.createElement('tr');
    tr.innerHTML = '<td>' + (t.name || '—') + '</td><td>' + (t.group || '—') + '</td><td>' + (t.desc || '—') + '</td>';
    tb.appendChild(tr);
  });
  $('stat-tools').textContent = list.length;
}, function (e) {
  var tb = $('tools-body');
  if (tb) tb.innerHTML = '<tr><td colspan="3" class="empty">Ошибка загрузки</td></tr>';
}); };
function loadPrograms() { api('/api/programs', null, function (d) {
  var tb = $('programs-body');
  if (!tb) return;
  tb.innerHTML = '';
  if (!d || d.error) {
    tb.innerHTML = '<tr><td colspan="3" class="empty">Требуется вход в систему</td></tr>';
    $('pill-programs').textContent = '—';
    return;
  }
  var list = Array.isArray(d) ? d : (d.programs || []);
  list.forEach(function (p) {
    var tr = document.createElement('tr');
    tr.innerHTML = '<td>' + (p.id || '—') + '</td><td>' + (p.title || '—') + '</td><td><span class="val ok">Активна</span></td>';
    tb.appendChild(tr);
  });
  $('pill-programs').textContent = 'программ: ' + list.length;
}, function (e) {
  var tb = $('programs-body');
  if (tb) tb.innerHTML = '<tr><td colspan="3" class="empty">Ошибка загрузки</td></tr>';
}); };
function chatSend() {
  var inp = $('chat-input');
  if (!inp || !inp.value.trim()) return;
  var text = inp.value.trim();
  inp.value = '';
  var msgs = $('chat-msgs');
  var me = document.createElement('div');
  me.className = 'msg me';
  me.textContent = text;
  msgs.appendChild(me);
  msgs.scrollTop = msgs.scrollHeight;
  api('/chat/send', { text: text }, function (d) {
    var a = document.createElement('div');
    a.className = 'msg agent';
    a.textContent = (d && d.answer) || (d && d.msg) || JSON.stringify(d);
    msgs.appendChild(a);
    msgs.scrollTop = msgs.scrollHeight;
  }, function (e) {
    var msgs = $('chat-msgs');
    var a = document.createElement('div');
    a.className = 'msg agent';
    a.textContent = 'Ошибка отправки: ' + e;
    msgs.appendChild(a);
    msgs.scrollTop = msgs.scrollHeight;
  });
}
function chatPoll() {
  if (!hasToken()) return;
  api('/chat/poll?last=0', null, function (d) {
    var msgs = d.msgs || d || [];
    if (!Array.isArray(msgs)) return;
    var container = $('chat-msgs');
    msgs.forEach(function (m) {
      if (m.from === 'me') return;
      var a = document.createElement('div');
      a.className = 'msg agent';
      a.textContent = m.text || m.answer || JSON.stringify(m);
      container.appendChild(a);
    });
    if (msgs.length) container.scrollTop = container.scrollHeight;
  });
}
function loadLog() { api('/log', null, function (d) {
  var lb = $('log-body');
  if (!lb) return;
  lb.textContent = d.log || 'Лог пуст';
  lb.scrollTop = lb.scrollHeight;
}); };
function loadSettings() { api('/settings', null, function (d) {
  var sb = $('settings-body');
  if (!sb) return;
  sb.innerHTML = '';
  if (!d || d.error) {
    sb.innerHTML = '<div class="empty">Требуется вход в систему</div>';
    return;
  }
  var items = Array.isArray(d) ? d : (d.items || []);
  items.forEach(function (it) {
    var div = document.createElement('div');
    div.className = 'setting-row';
    div.innerHTML = '<span class="name">' + (it.key || it.name || '—') + '</span><span class="val">' + (it.value !== undefined ? it.value : it.val || '—') + '</span>';
    sb.appendChild(div);
  });
}); };

function login() {
  var loginEl = $('login-login');
  var pwEl = $('login-pw');
  var errEl = $('login-err');
  if (!loginEl || !pwEl) return;
  var login = loginEl.value.trim();
  var pw = pwEl.value.trim();
  if (!login || !pw) { errEl.style.display = 'block'; return; }
  api('/login', { login: login, pw: pw }, function (d) {
    if (d && d.ok && d.token) {
      TK = d.token;
      localStorage.setItem('tk', TK);
      errEl.style.display = 'none';
      $('login-screen').classList.add('hidden');
      $('user-block').style.display = 'flex';
      $('user-name').textContent = d.login || login;
      if (d.is_manager) { $('btn-admin').style.display = 'inline-block'; }
      loadStatus(); loadTools(); loadPrograms(); loadLog(); loadSettings();
      setInterval(chatPoll, 5000);
      logOut('Вход: ' + (d.login || login));
    } else { errEl.style.display = 'block'; }
  }, function (e) {
    errEl.style.display = 'block';
    logOut('Ошибка входа: ' + e, 'err');
  });
}

function register() {
  var loginEl = $('login-login');
  var pwEl = $('login-pw');
  var errEl = $('login-err');
  if (!loginEl || !pwEl) return;
  var login = loginEl.value.trim();
  var pw = pwEl.value.trim();
  if (!login || !pw) { errEl.style.display = 'block'; return; }
  api('/register', { login: login, pw: pw }, function (d) {
    if (d && !d.error) { logOut('Регистрация прошла. Войдите.'); }
    else { errEl.textContent = d && d.msg ? d.msg : 'Ошибка регистрации'; errEl.style.display = 'block'; }
  }, function (e) { errEl.style.display = 'block'; });
}

function logout() {
  TK = ''; localStorage.removeItem('tk');
  $('login-screen').classList.remove('hidden');
  $('user-block').style.display = 'none';
  $('btn-admin').style.display = 'none';
  $('tools-body').innerHTML = '';
  $('programs-body').innerHTML = '';
  $('settings-body').innerHTML = '';
  $('log-body').innerHTML = '';
  $('chat-msgs').innerHTML = '<div class="msg system">Войдите в систему для работы с агентом.</div>';
  logOut('Вы вышли из системы');
}

function initResizer(handleEl, panelEl, min) {
  var startX = 0, startSize = 0;
  handleEl.addEventListener('mousedown', function (e) {
    e.preventDefault();
    startX = e.clientX;
    startSize = panelEl.getBoundingClientRect().width;
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    handleEl.classList.add('dragging');
  });
  function onMove(e) {
    var dx = e.clientX - startX;
    var newSize = startSize + dx;
    if (newSize < min) newSize = min;
    panelEl.style.width = newSize + 'px';
  }
  function onUp() {
    document.removeEventListener('mousemove', onMove);
    document.removeEventListener('mouseup', onUp);
    handleEl.classList.remove('dragging');
  }
}
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.sb-item').forEach(function (i) {
    i.addEventListener('click', function () { setTab(i.getAttribute('data-tab')); });
  });
  $('btn-toggle-sidebar').addEventListener('click', function () { togglePanel('sidebar'); });
  $('btn-toggle-right').addEventListener('click', function () { togglePanel('right'); });
  $('btn-close-right').addEventListener('click', function () { $('right').classList.add('hidden'); });
  $('btn-toggle-output').addEventListener('click', function () { togglePanel('output-panel'); });
  $('btn-clear-output').addEventListener('click', function () { $('output-body').innerHTML = ''; });
  $('btn-send').addEventListener('click', chatSend);
  $('chat-input').addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); chatSend(); } });
    initResizer($('toggle-sidebar'), $('sidebar'), 180);
  initResizer($('toggle-right'), $('right'), 200);

  if ($('btn-do-login')) $('btn-do-login').addEventListener('click', login);
  if ($('btn-do-reg')) $('btn-do-reg').addEventListener('click', register);
  if ($('btn-logout')) $('btn-logout').addEventListener('click', logout);
  if ($('btn-admin')) $('btn-admin').addEventListener('click', function () {
    logOut('Админка: пока не реализована в этом окне');
  });
  if ($('login-login')) $('login-login').addEventListener('keydown', function (e) { if (e.key === 'Enter') login(); });
  if ($('login-pw')) $('login-pw').addEventListener('keydown', function (e) { if (e.key === 'Enter') login(); });

  if (hasToken()) {
    $('login-screen').classList.add('hidden');
    $('user-block').style.display = 'flex';
    $('btn-admin').style.display = 'none';
    loadStatus(); loadTools(); loadPrograms(); loadLog(); loadSettings();
    // chatPoll отключён — не критично, избегаем ошибок в консоли
    // setInterval(chatPoll, 5000);
    logOut('UI инициализирован (войден)');
  } else {
    $('login-screen').classList.remove('hidden');
    $('user-block').style.display = 'none';
    logOut('UI инициализирован (требуется вход)');
  }
});