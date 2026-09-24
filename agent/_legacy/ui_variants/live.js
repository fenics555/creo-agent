/* ЖИВЫЕ ДАННЫЕ ДЛЯ ВАРИАНТОВ ОКНА (ui\variants\live.js)
   Один источник логики для всех трёх раскладок: /api/programs, /api/bases, /api/jobs, /prog_run, /prog_state.
   Раскладки (v1_tabs, v2_side, v3_pult) только расставляют блоки — данные и поведение здесь. */
const V = (() => {
  const TK = localStorage.getItem('tk') || '';
  const api = u => fetch(u, {headers:{'X-Token':TK}}).then(r => r.json());
  const post = (u, b) => fetch(u, {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(Object.assign({token: TK}, b || {}))}).then(r => r.json());
  const esc = s => String(s == null ? '' : s).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
  const klass = k => k === 'Ж' ? 'k-zh' : (k === 'Г' ? 'k-g' : 'k-r');
  const noAuth = '<div class="log">нужен вход в агент: открой http://127.0.0.1:8765, войди, потом вернись сюда</div>';

  function progCard(p){
    const run = p.run ? `<button class="btn" data-run="${p.id}">Запустить</button>`
                      : `<span class="muted" style="font-size:12px">запуск — своим окном</span>`;
    return `<div class="card"><h4><span class="dot ${p.pid?'on':''}"></span> ${esc(p.title)}
      <span class="k ${klass(p.klass)}">класс ${esc(p.klass)}</span></h4>
      <div class="mono muted">движок: ${esc(p.engine)}</div>
      <div class="mono muted">${p.window ? 'окно: '+esc(p.cwd)+' / '+esc(p.window) : 'окна нет — зовёт агент'}</div>
      <div class="muted" style="font-size:12px">${esc(p.status)}</div>
      <div class="row">${run}<button class="btn sec" data-state="${p.id}">Журнал</button></div>
      <div class="log" id="st_${p.id}" style="display:none"></div></div>`;
  }

  function progRow(p){
    return `<tr><td><span class="dot ${p.pid?'on':''}"></span> <b>${esc(p.title)}</b>
      <span class="k ${klass(p.klass)}">${esc(p.klass)}</span>
      <div class="mono muted">${esc(p.engine)}</div>
      <div class="muted" style="font-size:12px">${esc(p.status)}</div></td>
      <td>${p.pid ? '🟢 работает' : '⚪ готова'}</td>
      <td>${p.window ? esc(p.window) : '<span class="muted">—</span>'}</td>
      <td>${p.run ? `<button class="btn" data-run="${p.id}">Запустить</button>` : ''}
          <button class="btn sec" data-state="${p.id}">Журнал</button>
          <div class="log" id="st_${p.id}" style="display:none"></div></td></tr>`;
  }

  async function programsHTML(cell){
    const d = await api('/api/programs');
    if(!d || !d.programs) return noAuth;
    const wrap = (cell === 'row')
      ? rows => `<table><tr><th>Программа</th><th>Состояние</th><th>Окно</th><th></th></tr>${rows}</table>`
      : rows => `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:10px">${rows}</div>`;
    let h = `<h2>🧰 Программы дома <span class="muted" style="font-size:13px">(список от ${esc(d.updated)})</span></h2>`;
    for(const g of d.groups){
      const ps = d.programs.filter(p => p.group === g.id);
      if(!ps.length) continue;
      h += `<h3 style="margin-top:14px">${esc(g.icon)} ${esc(g.title)}
        <span class="muted" style="font-size:12px">— ${esc(g.note)}</span></h3>`;
      h += wrap(ps.map(cell === 'row' ? progRow : progCard).join(''));
    }
    return h;
  }

  async function basesHTML(){
    const d = await api('/api/bases');
    if(!d || !d.bases) return noAuth;
    let h = `<h2>🗄 Базы дома <span class="muted" style="font-size:13px">(чужое — только чтение)</span></h2>
      <table><tr><th>База</th><th>Размер</th><th>Таблиц</th><th>Обновлена</th><th>Статус</th><th></th></tr>`;
    for(const b of d.bases){
      const own = /своя/.test(b.kind);
      h += `<tr><td><b>${esc(b.name)}</b><div class="mono muted">${esc(b.path)}</div>
        <div class="muted" style="font-size:12px">${esc(b.what)}</div></td>
        <td>${b.mb} МБ</td><td>${esc(b.tables)}</td><td>${esc(b.mtime)}</td>
        <td>${own ? '<span class="k k-r">своя</span>' : '<span class="k">'+esc(b.kind)+'</span>'}</td>
        <td>${own ? '<button class="btn" data-upd="harvest">Обновить индекс</button>' : ''}</td></tr>`;
    }
    return h + `</table>
      <h3 style="margin-top:14px">Журнал работ дома</h3><div class="log" id="jobs">…</div>`;
  }

  async function jobsInto(id){
    const el = document.getElementById(id); if(!el) return;
    const d = await api('/api/jobs'); el.textContent = (d && d.lines) ? d.lines : 'журнал пуст';
  }

  function status(whoId, upId){
    api('/status').then(d => {
      const w = document.getElementById(whoId), u = document.getElementById(upId);
      if(w) w.textContent = (d && d.user)
        ? ('вошёл: ' + d.user.login + ' · режим ' + (d.mode == 2 ? 'собеседник' : 'инженер')) : 'НЕ вошёл в агент';
      if(u) u.textContent = d ? ('Ollama ' + (d.up_ollama?'🟢':'⚪') + ' · CREOSON ' + (d.up_creoson?'🟢':'⚪')
                                + ' · инструментов ' + d.tools) : 'агент не отвечает';
    });
  }

  function wireTabs(chipSel, zoneId, chatId){
    document.querySelectorAll(chipSel).forEach(x => x.addEventListener('click', async () => {
      const t = x.getAttribute('data-t');
      document.querySelectorAll(chipSel).forEach(c => c.classList.remove('on'));
      x.classList.add('on');
      const z = document.getElementById(zoneId), c = document.getElementById(chatId);
      if(!t || t === 'chat'){ z.style.display = 'none'; c.style.display = 'block'; return; }
      c.style.display = 'none'; z.style.display = 'block';
      z.innerHTML = '<span class="spin"></span> читаю данные…';
      z.innerHTML = (t === 'prog') ? await programsHTML(z.getAttribute('data-cell')) : await basesHTML();
      if(t === 'base') jobsInto('jobs');
    }));
  }

  function wireButtons(){
    document.addEventListener('click', async ev => {
      const r = ev.target.closest('[data-run]'), s = ev.target.closest('[data-state]'), u = ev.target.closest('[data-upd]');
      if(r){
        r.disabled = true;
        const t = await post('/prog_run', {prog_id: r.getAttribute('data-run')});
        const host = r.closest('.card, td, .row') || r.parentElement;
        host.insertAdjacentHTML('beforeend', '<span class="muted" style="font-size:12px">' + esc((t || {}).text || '?') + '</span>');
        r.disabled = false;
      }
      if(s){
        const id = s.getAttribute('data-state');
        const t = await post('/prog_state', {prog_id: id, tail: 12});
        const el = document.getElementById('st_' + id);
        if(el){ el.style.display = 'block'; el.textContent = (t || {}).text || '?'; }
      }
      if(u){
        if(!confirm('Обновить индекс дома? Запустится harvest в фоне (обычно ~20 с).')) return;
        const t = await post('/prog_run', {prog_id: u.getAttribute('data-upd')});
        alert((t || {}).text || '?');
        jobsInto('jobs');
      }
    });
  }

  function init(o){
    o = o || {};
    if(o.chips) wireTabs(o.chips, o.zone || 'zone', o.chat || 'chat');
    wireButtons();
    status(o.who || 'who', o.up || 'up');
    if(o.jobs) jobsInto(o.jobs);
  }

  return {TK, api, post, esc, klass, progCard, progRow, programsHTML, basesHTML, jobsInto, status, wireTabs, wireButtons, init};
})();
