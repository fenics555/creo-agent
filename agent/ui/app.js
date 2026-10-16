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
  fetch(base + path, opts).then(function (r) { return r.json(); }).then(function (d) { if (cb) cb(d); }).catch(function (e) { if (errCb) errCb(e); else logOut('API error ' + path + ': ' + e, 'err'); });
}
function setTab(tabId) {
  document.querySelectorAll('.sb-item').forEach(function (i) { i.classList.remove('active'); });
  document.querySelector('[data-tab="' + tabId + '"]').classList.add('active');
  document.querySelectorAll('.tab-content').forEach(function (c) { c.classList.remove('active'); });
  $('tab-' + tabId).classList.add('active');
  // Пересоздаём вкладку в верхней панели
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
// Загрузка статуса
function loadStatus() { api('/status', null, function (d) { updateStatus(d); }); }
// Загрузка инструментов
function loadTools() { api('/api/tools', null, function (d) {
  var tb = $('tools-body');
  if (!tb) return;
  tb.innerHTML = '';
  var list = d.tools || d || [];
  if (list.length === 0) { tb.innerHTML = '<tr><td colspan="3" class="empty">Нет инструментов</td></tr>'; return; }
  list.forEach(function (t) {
    var tr = document.createElement('tr');
    tr.innerHTML = '<td>' + (t.name || '—') + '</td><td>' + (t.group || '—') + '</td><td>' + (t.desc || '—') + '</td>';
    tb.appendChild(tr);
  });
  $('stat-tools').textContent = list.length;
}); };
// Загрузка программ
function loadPrograms() { api('/api/programs', null, function (d) {
  var tb = $('programs-body');
  if (!tb) return;
  tb.innerHTML = '';
  var list = d.programs || d || [];
  list.forEach(function (p) {
    var tr = document.createElement('tr');
    tr.innerHTML = '<td>' + (p.id || '—') + '</td><td>' + (p.title || '—') + '</td><td><span class="val ok">Активна</span></td>';
    tb.appendChild(tr);
  });
  $('pill-programs').textContent = 'программ: ' + list.length;
}); };
// Чат: отправка
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
  });
}
// Чат: опрос
function chatPoll() {
  api('/chat/poll?last=0', null, function (d) {
    var msgs = d.msgs || d || [];
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
// Лог
function loadLog() { api('/log', null, function (d) {
  var lb = $('log-body');
  if (!lb) return;
  lb.textContent = d.log || 'Лог пуст';
  lb.scrollTop = lb.scrollHeight;
}); };
// Настройки
function loadSettings() { api('/settings', null, function (d) {
  var sb = $('settings-body');
  if (!sb) return;
  sb.innerHTML = '';
  var items = d.items || d || [];
  items.forEach(function (it) {
    var div = document.createElement('div');
    div.className = 'setting-row';
    div.innerHTML = '<span class="name">' + (it.key || it.name || '—') + '</span><span class="val">' + (it.value !== undefined ? it.value : it.val || '—') + '</span>';
    sb.appendChild(div);
  });
}); };
// Инициализация
document.addEventListener('DOMContentLoaded', function () {
  // Навигация
  document.querySelectorAll('.sb-item').forEach(function (i) {
    i.addEventListener('click', function () { setTab(i.getAttribute('data-tab')); });
  });
  // Переключатели панелей
  $('btn-toggle-sidebar').addEventListener('click', function () { togglePanel('sidebar'); });
  $('btn-toggle-right').addEventListener('click', function () { togglePanel('right'); });
  $('btn-close-right').addEventListener('click', function () { $('right').classList.add('hidden'); });
  $('btn-toggle-output').addEventListener('click', function () { togglePanel('output-panel'); });
  $('btn-clear-output').addEventListener('click', function () { $('output-body').innerHTML = ''; });
  // Чат
  $('btn-send').addEventListener('click', chatSend);
  $('chat-input').addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); chatSend(); } });
  // Загрузка данных
  loadStatus();
  loadTools();
  loadPrograms();
  loadLog();
  loadSettings();
  setInterval(loadStatus, 10000);
  setInterval(chatPoll, 5000);
  logOut('UI инициализирован');
});
