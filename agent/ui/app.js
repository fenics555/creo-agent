/* app.js — витрина АГЕНТ v15 (23.11.2026): экраны, инструменты, программы, люди, журнал, настройки. */
window.__AGENT_UI = 1;
(function uiVersionGuard() {
  // Защита от старой копии витрины в браузере: при смене версии — одна перезагрузка.
  try {
    var meta = document.querySelector('meta[name="ui-ver"]');
    var ver = meta ? meta.getAttribute('content') : '0';
    var seen = localStorage.getItem('ui_ver');
    localStorage.setItem('ui_ver', ver);
    if (seen && seen !== ver) location.reload();
  } catch (e) { /* приватный режим — не мешаем */ }
})();
var TK = localStorage.getItem('agent_token') || '';
var ME = null;
var BASE = '';
var TOOLS = [];
var CUR_TOOL = null;
var CUR_TOOL_ABORT = null;
var STREAM_CTRL = null;

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

/* ---------- модели (мгновенная смена в шапке) ---------- */
function loadModels() {
  api('/api/models', null, function (d) {
    var sel = $('model-select');
    if (!sel) return;
    var cur = d.current || '';
    sel.innerHTML = '';
    (d.models || []).forEach(function (m) {
      var o = document.createElement('option');
      o.value = m; o.textContent = m;
      if (m === cur) o.selected = true;
      sel.appendChild(o);
    });
    if (!(d.models || []).length) {
      var o2 = document.createElement('option');
      o2.value = cur; o2.textContent = cur || 'модели не найдены';
      sel.appendChild(o2);
    }
    var admin = !!(ME && ME.role === 'Администратор');
    sel.disabled = !admin;
    sel.title = admin ? 'Сменить модель дома (сразу)' : 'Смена модели — только администратор';
  }, function () {});
}
function modelChanged() {
  var sel = $('model-select');
  if (!sel || !sel.value) return;
  var pick = sel.closest('.model-pick');
  sel.setAttribute('data-hold', '1');
  api('/setmodel', { model: sel.value }, function () {
    if (pick) { pick.classList.add('pulse'); setTimeout(function () { pick.classList.remove('pulse'); }, 1300); }
    var st = $('st-model'); if (st) st.textContent = sel.value;
    loadStatus();
    sel.removeAttribute('data-hold');
  }, function (e) {
    alert('модель не сменена: ' + (e.error || 'нет прав'));
    sel.removeAttribute('data-hold');
    loadStatus();
  });
}

/* ---------- инфографика ---------- */
var PALETTE = ['#3d8bfd', '#4ec9b0', '#e2c08d', '#c586c0', '#f48771', '#7ee0c9', '#9cdcfe', '#d7ba7d'];
function renderDonut(groups) {
  groups = groups || [];
  var svg = $('donut');
  if (!svg) return;
  var total = groups.reduce(function (s, g) { return s + g.n; }, 0);
  var dt = $('donut-total'); if (dt) dt.textContent = total || '—';
  var R = 48, C = 2 * Math.PI * R, off = 0, parts = [];
  groups.forEach(function (g, i) {
    var len = total ? C * (g.n / total) : 0;
    parts.push('<circle cx="60" cy="60" r="' + R + '" fill="none" stroke="' +
      PALETTE[i % PALETTE.length] + '" stroke-width="14" stroke-dasharray="' +
      len.toFixed(2) + ' ' + (C - len).toFixed(2) + '" stroke-dashoffset="' + (-off).toFixed(2) + '"/>');
    off += len;
  });
  svg.innerHTML = parts.join('') || '<circle cx="60" cy="60" r="48" fill="none" stroke="#3a4149" stroke-width="14"/>';
  var legend = $('donut-legend');
  if (legend) {
    legend.innerHTML = groups.map(function (g, i) {
      return '<div class="legend-item"><i style="background:' + PALETTE[i % PALETTE.length] + '"></i>' +
        '<span>' + esc(g.id) + '</span><span class="spacer"></span><b>' + g.n + '</b></div>';
    }).join('');
  }
  renderBars(groups);
}
function renderBars(groups) {
  var box = $('bars');
  if (!box) return;
  groups = (groups || []).slice(0, 8);
  var max = groups.reduce(function (m, g) { return Math.max(m, g.n); }, 1);
  box.innerHTML = groups.map(function (g) {
    return '<div class="bar-row"><span>' + esc(g.id) + '</span>' +
      '<span class="bar-track"><i class="bar-fill" style="width:' +
      Math.round(100 * g.n / max) + '%"></i></span>' +
      '<span class="n">' + g.n + '</span></div>';
  }).join('') || '<div class="empty">нет данных</div>';
}
function sparkPush(sec) {
  var arr = [];
  try { arr = JSON.parse(localStorage.getItem('agent_rt') || '[]'); } catch (e) { arr = []; }
  arr.push(Number(sec) || 0);
  if (arr.length > 20) arr = arr.slice(-20);
  localStorage.setItem('agent_rt', JSON.stringify(arr));
  renderSpark(arr);
}
function renderSpark(arr) {
  var svg = $('spark');
  if (!svg) return;
  if (!arr || !arr.length) { svg.innerHTML = ''; return; }
  var max = Math.max.apply(null, arr) || 1, W = 300, H = 60;
  var step = arr.length > 1 ? W / (arr.length - 1) : W;
  var pts = arr.map(function (v, i) {
    return (i * step).toFixed(1) + ',' + (H - 6 - (v / max) * (H - 12)).toFixed(1);
  });
  svg.innerHTML = '<polyline points="' + pts.join(' ') + '"></polyline>' +
    arr.map(function (v, i) {
      return '<circle cx="' + (i * step).toFixed(1) + '" cy="' +
        (H - 6 - (v / max) * (H - 12)).toFixed(1) + '" r="2"></circle>';
    }).join('');
}
function refreshSpark() {
  var arr = [];
  try { arr = JSON.parse(localStorage.getItem('agent_rt') || '[]'); } catch (e) { arr = []; }
  renderSpark(arr);
}

/* ---------- правила (как .clinerules в Cline) ---------- */
var RULES = { files: [], limit: 12000 };

function loadRules() {
  api('/api/rules', null, function (d) {
    RULES.files = (d.files || []).map(function (f) { return f.path; });
    RULES.limit = d.limit || 12000;
    var box = $('rules-files');
    if (box) {
      box.innerHTML = (d.files || []).map(function (f) {
        var st = f.exists
          ? '<span class="badge ok">' + f.lines + ' строк · ' + esc(f.mtime) + '</span>'
          : '<span class="badge err">нет файла</span>';
        return '<div class="item"><div class="grow"><div class="name">' + esc(f.path) +
          '</div></div>' + st +
          '<button class="btn sm ghost" data-rule-del="' + esc(f.path) + '">Убрать</button></div>';
      }).join('') || '<div class="empty">файлов правил нет</div>';
      box.querySelectorAll('[data-rule-del]').forEach(function (b) {
        b.addEventListener('click', function () { ruleRemove(b.getAttribute('data-rule-del')); });
      });
    }
    var lim = $('rules-limit'); if (lim) lim.value = RULES.limit;
    var pv = $('rules-preview'); if (pv) pv.textContent = d.preview || '(пусто)';
    var stt = $('rules-status');
    if (stt) {
      var n = (d.files || []).filter(function (f) { return f.exists; }).length;
      stt.textContent = 'в промт идёт ' + (d.chars || 0) + ' из ' + RULES.limit +
        ' симв. · существующих файлов: ' + n;
    }
  }, function (e) {
    var stt = $('rules-status'); if (stt) stt.textContent = 'ошибка: ' + (e.error || '');
  });
}
function rulesSave(files) {
  var lim = $('rules-limit');
  api('/setrules', { files: files || RULES.files, max_chars: lim ? parseInt(lim.value, 10) : 0 },
    function () { loadRules(); },
    function (e) { alert('правила не сохранены: ' + (e.error || 'нет прав')); });
}
function ruleAdd() {
  var inp = $('rule-new-path');
  var v = ((inp && inp.value) || '').trim();
  if (!v) return;
  var files = RULES.files.slice();
  if (files.indexOf(v) < 0) files.push(v);
  if (inp) inp.value = '';
  rulesSave(files);
}
function ruleRemove(path) {
  rulesSave(RULES.files.filter(function (x) { return x !== path; }));
}

/* ---------- сессия: новая / эстафета ---------- */
function newSession() {
  if (!confirm('Очистить историю диалога? Контекст начнётся с нуля.')) return;
  api('/history/clear', {}, function () {
    chatClear();
    chatAdd('Новая сессия: история диалога очищена.', false);
    loadStatus();
  }, function (e) { alert('не очищено: ' + (e.error || '')); });
}
function handover() {
  api('/session/handover', {}, function (d) {
    alert(d.msg || ('эстафета: ' + d.path));
  }, function (e) { alert('эстафета не записана: ' + (e.error || '')); });
}

/* ---------- обслуживание ---------- */
function maintRun(tool, args, label) {
  var out = $('maint-out');
  if (!out) return;
  out.style.color = 'var(--muted)';
  out.textContent = label + ' …';
  api('/tool', { name: tool, args: args || {} }, function (d) {
    out.style.color = 'var(--text)';
    out.textContent = d.result || '(пусто)';
  }, function (e) {
    out.style.color = 'var(--err)';
    out.textContent = 'ОТКАЗ: ' + (e.error || 'нет прав');
  });
}
function setTab(tabId) {
  document.querySelectorAll('.sb-item').forEach(function (i) {
    i.classList.toggle('active', i.getAttribute('data-tab') === tabId);
  });
  document.querySelectorAll('.screen').forEach(function (s) { s.classList.remove('active'); });
  var scr = $('screen-' + tabId);
  if (scr) scr.classList.add('active');
  if (tabId === 'overview') { loadStatus(); loadPrograms(true); loadTools(); refreshSpark(); }
  if (tabId === 'tools') loadTools();
  if (tabId === 'programs') loadPrograms();
  if (tabId === 'people') loadPeople();
  if (tabId === 'logs') loadLog();
  if (tabId === 'settings') loadSettings();
  if (tabId === 'rules') loadRules();
  if (tabId === 'chat') { var ci = $('chat-input'); if (ci) ci.focus(); }
}
function togglePanel(id) {
  var el = $(id);
  if (!el) return;
  el.style.display = (el.style.display === 'none' || !el.style.display) ? 'flex' : 'none';
}
function showModal(title, text) {
  var m = $('modal');
  if (!m) return;
  $('modal-title').textContent = title || '';
  $('modal-body').textContent = text || '';
  m.style.display = 'flex';
}
function closeModal() {
  var m = $('modal');
  if (m) m.style.display = 'none';
}

/* ---------- статус и KPI ---------- */
function updateStatus(d) {
  if (!d) return;
  ME = d.user || ME;
  var model = d.model || '—';
  var ctx = d.model_ctx || d.ctx_requested || 0;
  var pill = $('pill-model'); if (pill) pill.innerHTML = 'модель: <b>' + esc(model) + '</b>';
  var cm = $('chat-model');
  if (cm) cm.textContent = model + (ctx ? ' · контекст ' + (ctx / 1024).toFixed(0) + 'k' : '');
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
  var used = d.ctx_session || 0, max = d.model_ctx || d.ctx_requested || 0;
  var pct = max ? Math.min(100, Math.round(100 * used / max)) : 0;
  var cbar = $('ctx-bar'); if (cbar) cbar.style.width = pct + '%';
  var cinfo = $('ctx-info');
  if (cinfo) cinfo.textContent = max ? (used + ' из ' + max + ' (' + pct + '%)') : '—';
  var warn = $('ctx-warn');
  if (warn) {
    if (pct >= 80) {
      warn.style.display = 'block';
      warn.className = 'ctx-warn danger';
      warn.textContent = '⚠ Контекст заполнен на ' + pct + '%. Нажмите «Эстафета» (сохранит диалог в файл), затем «Новая сессия» — иначе ответы начнут урезаться.';
    } else if (pct >= 70) {
      warn.style.display = 'block';
      warn.className = 'ctx-warn';
      warn.textContent = 'Контекст заполнен на ' + pct + '% (порог дома 70%). Скоро понадобится «Эстафета» и «Новая сессия».';
    } else {
      warn.style.display = 'none';
    }
  }
  var sel = $('model-select');
  if (sel && d.model && sel.value !== d.model && !sel.getAttribute('data-hold')) sel.value = d.model;
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
  var wait = chatAdd('', false);
  wait.classList.add('typing');
  var box = $('chat-msgs');
  box.parentNode.classList.add('streaming');
  var t0 = Date.now(), toks = '', steps = [];
  var ctrl = new AbortController();
  STREAM_CTRL = ctrl;
  var spin = '<span class="dots"><i></i><i></i><i></i></span>';
  wait.innerHTML = spin + ' думает… <b class="tmr">0 с</b>';
  var thinkTmr = setInterval(function () {
    if (!toks) {
      wait.innerHTML = spin + ' думает… <b class="tmr">' +
        ((Date.now() - t0) / 1000).toFixed(0) + ' с</b>';
    }
  }, 400);

  function finish(done, stopped) {
    clearInterval(thinkTmr);
    var secs = (Date.now() - t0) / 1000;
    wait.classList.remove('typing');
    box.parentNode.classList.remove('streaming');
    var ans = (done && done.answer) || toks || (stopped ? 'остановлено' : '(пусто)');
    wait.textContent = ans;
    var meta = [];
    if (done && done.steps) meta.push('шагов: ' + done.steps);
    if (steps.length) meta.push(String(steps[0]).replace(/\s+/g, ' ').slice(0, 100));
    meta.push(secs.toFixed(1) + ' с');
    var m = document.createElement('span');
    m.className = 'meta';
    m.textContent = meta.join(' · ');
    wait.appendChild(m);
    if (done && done.think) {
      var det = document.createElement('details');
      det.className = 'think';
      var sum = document.createElement('summary');
      sum.textContent = '🧠 рассуждение';
      var body = document.createElement('div');
      body.className = 'mono';
      body.textContent = done.think;
      det.appendChild(sum); det.appendChild(body);
      wait.appendChild(det);
    }
    var lt = $('st-last-time'); if (lt) lt.textContent = secs.toFixed(1) + ' с';
    var ls = $('st-last-steps'); if (ls) ls.textContent = (done && done.steps) || '—';
    var lg = ((done && done.log) || []).join(' ') + ' ' + steps.join(' ');
    var mm = lg.match(/(\d+)\s*ток/);
    var lk = $('st-last-tokens'); if (lk) lk.textContent = mm ? mm[1] + ' ток' : '—';
    sparkPush(secs);
    STREAM_CTRL = null;
  }

  fetch('/ask_stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Token': TK },
    body: JSON.stringify({ q: text, mode: 1 }),
    signal: ctrl.signal
  }).then(function (r) {
    if (!r.ok) throw new Error('HTTP ' + r.status);
    var reader = r.body.getReader();
    var dec = new TextDecoder('utf-8');
    var buf = '';
    function pump() {
      return reader.read().then(function (res) {
        if (res.done) { finish(null, false); return; }
        buf += dec.decode(res.value, { stream: true });
        var idx;
        while ((idx = buf.indexOf('\n\n')) >= 0) {
          var chunk = buf.slice(0, idx);
          buf = buf.slice(idx + 2);
          chunk.split('\n').forEach(function (line) {
            if (line.indexOf('data: ') !== 0) return;
            var d = null;
            try { d = JSON.parse(line.slice(6)); } catch (e) { return; }
            if (d.tok) {
              var wasEmpty = !toks;
              toks += Array.isArray(d.tok) ? d.tok.join('') : String(d.tok);
              if (toks) {
                if (wasEmpty) clearInterval(thinkTmr);
                wait.textContent = toks;
              }
            }
            if (d.step) {
              steps.push(d.step);
              if (!toks) wait.textContent = '… ' + String(d.step).slice(0, 90);
            }
            if (d.error) { wait.textContent = 'ошибка: ' + d.error; }
            if (d.done) { finish(d.done, false); }
          });
        }
        return pump();
      });
    }
    return pump();
  }).catch(function (e) {
    if (e.name === 'AbortError') { finish(null, true); return; }
    wait.classList.remove('typing');
    wait.textContent = 'ошибка: ' + e.message;
    finish(null, true);
  });
}
function chatStop() {
  if (STREAM_CTRL) { try { STREAM_CTRL.abort(); } catch (e) {} }
  api('/ask_cancel', {}, function () { }, function () { });
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
    renderDonut(d.groups || []);
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
  var descEl = $('tool-desc');
  if (descEl) descEl.textContent = t.desc || '';
  var warn = $('tool-warn');
  var notes = [];
  if (t.approval) notes.push('требует согласования (пишет в дом / Creo)');
  if (t.needs_creo) notes.push('нужен живой Creo/CREOSON');
  if (warn) {
    if (notes.length) {
      warn.style.display = 'block';
      warn.textContent = '⚠ ' + notes.join(' · ');
    } else {
      warn.style.display = 'none';
    }
  }
  var args = $('tool-args');
  var pd = t.params || {};
  var keys = Object.keys(pd);
  if (!keys.length) {
    args.innerHTML = '<span style="color:var(--muted)">параметров нет — запускается сразу</span>';
  } else {
    args.innerHTML = keys.map(function (k) {
      return '<div class="field"><label>' + esc(k) + ' — ' +
        esc(pd[k] || 'параметр') + '</label>' +
        '<input id="arg-' + esc(k) + '" placeholder="' + esc(pd[k] || k) + '"></div>';
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
      '<button class="btn sm ghost" data-readme="' + esc(p.id) + '">README</button>' +
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
  box.querySelectorAll('[data-readme]').forEach(function (b) {
    b.addEventListener('click', function () { openProgramReadme(b.getAttribute('data-readme')); });
  });
}
function openProgramReadme(id) {
  showModal('README · ' + id, 'Читаю…');
  api('/api/program_readme?id=' + encodeURIComponent(id), null, function (d) {
    showModal('README · ' + id + (d.lines ? ' · ' + d.lines + ' строк' : ''), d.text || '(пусто)');
  }, function (e) { showModal('README · ' + id, 'ошибка: ' + (e.error || '')); });
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
        '<button class="btn sm" data-setrole="' + esc(u.login) + '">Сменить роль</button>' +
        ((ME && ME.login === u.login) ? '' :
          '<button class="btn sm danger" data-del-user="' + esc(u.login) + '">Удалить</button>') +
        '</div>';
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
    box.querySelectorAll('[data-del-user]').forEach(function (b) {
      b.addEventListener('click', function () {
        var lg = b.getAttribute('data-del-user');
        if (!confirm('Удалить пользователя «' + lg + '»? Доступ будет потерян.')) return;
        api('/admin/users', { op: 'delete', login: lg }, function (r) {
          $('people-msg').textContent = r.msg || 'удалено';
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
  if (CUR_TOOL.approval && !confirm('«' + CUR_TOOL.name + '» меняет дом или Creo.\nПодтвердить запуск?')) return;
  var args = {};
  Object.keys(CUR_TOOL.params || {}).forEach(function (p) {
    var el = $('arg-' + p);
    var v = el ? el.value.trim() : '';
    if (v) args[p] = v;
  });
  var b = $('tool-run-btn');
  var out = $('tool-result');
  b.disabled = true;
  var t0 = Date.now();
  var ctrl = (typeof AbortController !== 'undefined') ? new AbortController() : null;
  var timer = setInterval(function () {
    out.textContent = 'Выполняю ' + CUR_TOOL.name + ' … ' +
      ((Date.now() - t0) / 1000).toFixed(0) + ' с (Esc — отменить)';
  }, 500);
  out.style.color = 'var(--muted)';
  function done(text, isErr) {
    clearInterval(timer);
    b.disabled = false;
    out.style.color = isErr ? 'var(--err)' : 'var(--text)';
    out.textContent = text;
  }
  var opts = { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Token': TK },
               body: JSON.stringify({ name: CUR_TOOL.name, args: args }) };
  if (ctrl) opts.signal = ctrl.signal;
  CUR_TOOL_ABORT = ctrl;
  fetch('/tool', opts).then(function (r) {
    return r.text().then(function (t) {
      var d = {};
      try { d = JSON.parse(t); } catch (e) { d = { result: t }; }
      if (!r.ok) { done('ОТКАЗ: ' + (d.error || ('HTTP ' + r.status)), true); return; }
      done(d.result || '(пусто)', false);
    });
  }).catch(function (e) {
    if (e.name === 'AbortError') { done('Отменено пользователем', true); return; }
    done('ошибка связи: ' + e.message, true);
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
  api('/api/models', null, function (mm) {
    var MODELS = mm.models || [];
    api('/settings', null, function (d) {
      var box = $('settings-list');
      var items = d.items || [];
      box.innerHTML = items.map(function (it, i) {
        var isBool = (it.type === 'bool') || it.kind === 'bool';
        var isModel = (it.key === 'llm_model') || String(it.key).indexOf('model_') === 0;
        var input;
        if (isBool) {
          input = '<select id="set-' + i + '"><option' + (it.value ? ' selected' : '') + '>да</option>' +
            '<option' + (!it.value ? ' selected' : '') + '>нет</option></select>';
        } else if (isModel) {
          var cur = String(it.value == null ? '' : it.value);
          var opts = ['<option value="">— не задано —</option>'];
          MODELS.forEach(function (m) {
            opts.push('<option value="' + esc(m) + '"' + (m === cur ? ' selected' : '') + '>' +
              esc(m) + '</option>');
          });
          if (cur && MODELS.indexOf(cur) < 0) {
            opts.push('<option value="' + esc(cur) + '" selected>' + esc(cur) + ' (нет в Ollama)</option>');
          }
          input = '<select id="set-' + i + '">' + opts.join('') + '</select>';
        } else {
          input = '<input id="set-' + i + '" value="' + esc(it.value == null ? '' : it.value) + '">';
        }
        var badge = it.used === false ? '<span class="badge warn" title="ключ не читается кодом агента — задел">не влияет</span>' : '';
        return '<div class="item"><div class="grow"><div class="t">' + esc(it.name || it.key) + '</div>' +
          '<div class="d">' + esc(it.space || '') + ' · ' + esc(it.key) + ' — ' + esc(it.desc || '') + '</div></div>' +
          badge + input + '<button class="btn sm" data-set="' + i + '">Применить</button></div>';
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
          if (it.type === 'list') val = String(raw).split(/[;,]/).map(function (x) { return x.trim(); })
            .filter(function (x) { return x; });
          api('/setcfg', { key: it.key, value: val }, function () {
            b.textContent = '✓ применено';
            setTimeout(function () { b.textContent = 'Применить'; }, 1400);
            if (it.key === 'llm_model') loadStatus();
          }, function (e) {
            b.textContent = 'Отказ';
            b.title = e.error || '';
            setTimeout(function () { b.textContent = 'Применить'; }, 1800);
          });
        });
      });
    });
  }, function () {
    var st = $('settings-list');
    if (st) st.innerHTML = '<div class="empty">не удалось получить список моделей</div>';
  });
}

/* ---------- вход ---------- */
function showApp() {
  $('login-screen').style.display = 'none';
  $('app').style.display = 'flex';
  loadStatus();
  loadPrograms(true);
  loadModels();
  refreshSpark();
  setTab('chat');
  var ci = $('chat-input'); if (ci) ci.focus();
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
  var msel = $('model-select');
  if (msel) msel.addEventListener('change', modelChanged);
  var rch = $('run-checks');
  if (rch) rch.addEventListener('click', function () { maintRun('checks_run', { scope: '' }, 'Проверки дома'); });
  var rchh = $('run-checks-house');
  if (rchh) rchh.addEventListener('click', function () { maintRun('checks_run', { scope: 'house' }, 'Проверки house'); });
  var cl = $('btn-checks-list');
  if (cl) cl.addEventListener('click', function () { maintRun('checks_list', {}, 'Список проверок'); });
  var gs = $('btn-git-status');
  if (gs) gs.addEventListener('click', function () { maintRun('git_status', {}, 'Git-статус'); });
  var gp = $('btn-git-pull');
  if (gp) gp.addEventListener('click', function () { maintRun('git_pull', {}, 'Обновление (git pull)'); });
  var mr = $('maint-refresh');
  if (mr) mr.addEventListener('click', function () { maintRun('git_status', {}, 'Git-статус'); });
  var rr = $('rules-refresh'); if (rr) rr.addEventListener('click', loadRules);
  var ra = $('rule-add'); if (ra) ra.addEventListener('click', ruleAdd);
  var rs = $('rules-save'); if (rs) rs.addEventListener('click', function () { rulesSave(); });
  var ns = $('btn-new-session'); if (ns) ns.addEventListener('click', newSession);
  var ho = $('btn-handover'); if (ho) ho.addEventListener('click', handover);
  var chr = $('chat-rules'); if (chr) chr.addEventListener('click', function () { setTab('rules'); });
  var chh = $('chat-handover'); if (chh) chh.addEventListener('click', handover);
  var chn = $('chat-new'); if (chn) chn.addEventListener('click', newSession);
  var chl = $('chat-reload'); if (chl) chl.addEventListener('click', function () { location.reload(true); });
  var mc = $('modal-close'); if (mc) mc.addEventListener('click', closeModal);
  var md = $('modal'); if (md) md.addEventListener('click', function (e) { if (e.target === md) closeModal(); });
  var oh = $('ov-handover'); if (oh) oh.addEventListener('click', handover);
  var onw = $('ov-new'); if (onw) onw.addEventListener('click', newSession);
  document.addEventListener('keydown', function (e) {
    if (e.ctrlKey && e.key.toLowerCase() === 'k') {
      e.preventDefault(); setTab('tools');
      var f = $('tool-search'); if (f) f.focus();
    }
    if (e.ctrlKey && e.key === 'Enter') { e.preventDefault(); chatSend(); }
    if (e.key === 'Escape') { if ($('modal').style.display === 'flex') closeModal(); else chatStop(); }
  });
  if (hasToken()) showApp(); else $('login-screen').style.display = 'flex';
});