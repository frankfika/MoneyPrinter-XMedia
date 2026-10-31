const $ = (s, r=document) => r.querySelector(s);
const $$ = (s, r=document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const escAttr = esc;

async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok && r.status !== 404) throw new Error(`${path} → ${r.status}`);
  return r.json();
}
async function post(path, body) {
  const r = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
  return r.json();
}
function toast(msg, kind) {
  let t = $('.toast');
  if (!t) { t = document.createElement('div'); t.className='toast'; document.body.appendChild(t); }
  t.textContent = msg; t.className = 'toast show' + (kind ? ' ' + kind : '');
  clearTimeout(t._h); t._h = setTimeout(()=> t.className='toast', 3600);
}
function agoText(ts) {
  if (!ts) return '—';
  const d = new Date(String(ts).replace(' ','T'));
  if (isNaN(d)) return String(ts);
  const h = (Date.now()-d.getTime())/3600000;
  if (h < 1) return Math.max(0,Math.round((Date.now()-d.getTime())/60000)) + ' 分钟前';
  if (h < 48) return h.toFixed(1) + ' 小时前';
  return (h/24).toFixed(1) + ' 天前';
}
function md(src) {
  if (!src) return '';
  let lines = String(src).split('\n');
  // 先把连续的表格行抽出来
  const blocks = [];
  let i = 0;
  while (i < lines.length) {
    if (/^\s*\|/.test(lines[i])) {
      const t = [];
      while (i < lines.length && /^\s*\|/.test(lines[i])) t.push(lines[i++]);
      blocks.push({type:'table', lines:t});
    } else blocks.push({type:'line', line:lines[i++]});
  }
  lines = blocks.flatMap(b => b.type==='table' ? [b] : [b.line]);
  let out = '', inList = false, inCode = false;
  const inline = t => esc(t)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  for (const blk of lines) {
    if (blk && typeof blk === 'object' && blk.type === 'table') {
      if (inList) { out += '</ul>'; inList=false; }
      const rows = blk.lines.map(r => r.replace(/^\s*\|/, '').replace(/\|\s*$/, '').split('|').map(c=>c.trim()));
      const head = rows[0] || [];
      const body = rows.slice(rows.length && /^[:\- ]+$/.test((rows[1]||[]).join('')) ? 2 : 1);
      out += '<table style="margin:8px 0"><thead><tr>' + head.map(h=>`<th>${inline(h)}</th>`).join('') + '</tr></thead><tbody>'
        + body.map(r=>'<tr>'+r.map(c=>`<td>${inline(c)}</td>`).join('')+'</tr>').join('') + '</tbody></table>';
      continue;
    }
    const raw = blk;
    if (raw.trim().startsWith('```')) { inCode = !inCode; out += inCode ? '<pre>' : '</pre>'; continue; }
    if (inCode) { out += esc(raw) + '\n'; continue; }
    const l = raw.replace(/\s+$/,'');
    const hm = l.match(/^(#{1,4})\s+(.*)$/);
    if (hm) { if (inList) { out += '</ul>'; inList=false; }
      const lv = Math.min(hm[1].length,3);
      out += `<h${lv}>${inline(hm[2])}</h${lv}>`; continue; }
    if (/^\s*[-*]\s+/.test(l)) {
      if (!inList) { out += '<ul>'; inList = true; }
      out += `<li>${inline(l.replace(/^\s*[-*]\s+/,''))}</li>`; continue;
    }
    if (!l.trim()) { if (inList) { out += '</ul>'; inList=false; } continue; }
    if (inList) { out += '</ul>'; inList=false; }
    out += `<p>${inline(l)}</p>`;
  }
  if (inList) out += '</ul>';
  if (inCode) out += '</pre>';
  return out;
}
function gatePill(g) {
  if (!g) return '<span class="pill mute">未知</span>';
  if (g.state === 'pass') return '<span class="pill ok">闸门通过</span>';
  if (g.state === 'fail') return '<span class="pill bad">闸门拦截</span>';
  if (g.state === 'stale') return '<span class="pill warn">回执过期</span>';
  return '<span class="pill mute">未测</span>';
}
function platformPill(p) {
  return p === 'xiaohongshu' ? '<span class="pill info">小红书</span>' : '<span class="pill mute">X</span>';
}

// ───────── 总览 ─────────
async function renderOverview() {
  const d = await api('/api/overview');
  const c = d.counts;
  const x = d.x, xhs = d.xhs, dd = d.x_delta;
  const coolH = dd.published_hours ?? 0;
  const gapH = d.x_gap_hours ?? 6;
  const coolPct = Math.min(100, (coolH/gapH)*100);

  $('#tab-overview').innerHTML = `
  <div class="grid g4" style="margin-bottom:14px">
    <div class="stat"><div class="n">${c.published_total}</div><div class="l">累计已发</div><div class="x">今天 +${c.published_today}</div></div>
    <div class="stat"><div class="n">${c.outbound_total}</div><div class="l">互动动作</div><div class="x">今天 +${c.outbound_today}</div></div>
    <div class="stat"><div class="n" style="color:${c.drafts_pending_passed?'var(--amber)':'inherit'}">${c.drafts_pending_passed}</div><div class="l">过闸未发</div><div class="x">共 ${c.drafts_pending} 条备稿</div></div>
    <div class="stat"><div class="n">${c.seen_total}</div><div class="l">已见帖子</div><div class="x">去重库条数</div></div>
  </div>

  <div class="grid g2" style="margin-bottom:14px">
    <div class="card">
      <h3>通道体检 <span class="hint">能不能真发</span></h3>
      ${d.channels.map(ch=>`
        <div style="display:flex;gap:10px;align-items:flex-start;padding:9px 0;border-bottom:1px solid #1c1f28">
          <span class="pill ${ch.ok?'ok':'bad'}">${ch.ok?'通':'断'}</span>
          <div style="flex:1;min-width:0">
            <div style="font-size:13px">${esc(ch.name)} <span class="dim2 mono">${esc(ch.state)}</span></div>
            ${ch.note?`<div class="dim2" style="font-size:11.5px;margin-top:3px;line-height:1.5">${esc(ch.note)}</div>`:''}
          </div>
        </div>`).join('')}
    </div>

    <div class="card">
      <h3>账号状态 <span class="hint">private/account-safety.yaml</span></h3>
      <dl class="kv">
        <dt>X 账号</dt><dd>${esc(x.account_label||'—')}</dd>
        <dt>登录态</dt><dd><span class="pill ${x.login_state==='logged_in'?'ok':'warn'}">${esc(x.login_state||'—')}</span>
            <span class="pill mute">publish_mode=${esc(x.publish_mode||'—')}</span></dd>
        <dt>上次发原创</dt><dd>${esc(x.last_published_at||'—')} <span class="dim2">(${agoText(x.last_published_at)})</span></dd>
        <dt>上次回复</dt><dd>${esc(x.last_outbound_reply_at||'—')} <span class="dim2">(${agoText(x.last_outbound_reply_at)})</span></dd>
        <dt>上次点赞</dt><dd>${esc(x.last_outbound_like_at||'—')} <span class="dim2">(${agoText(x.last_outbound_like_at)})</span></dd>
        <dt>上次登录检查</dt><dd>${esc(x.last_login_check||'—')}</dd>
        <dt>小红书</dt><dd>${esc(xhs.account_label||'—')}
            <span class="pill ${xhs.is_banned?'bad':'ok'}">${xhs.is_banned?'封禁':'正常'}</span>
            <span class="pill ${xhs.agent_publish_allowed?'ok':'mute'}">agent_publish=${xhs.agent_publish_allowed?'允许':'不允许'}</span></dd>
        <dt>小红书登录</dt><dd><span class="pill ${xhs.login_state==='logged_in'?'ok':'warn'}">${esc(xhs.login_state||'—')}</span></dd>
        <dt>小红书最近</dt><dd>${esc(xhs.last_published_title||'—')}
            ${xhs.last_published_status?`<span class="pill info">${esc(xhs.last_published_status)}</span>`:''}</dd>
      </dl>
      <div class="hr"></div>
      <div style="display:flex;justify-content:space-between;font-size:11.5px;color:var(--dim2)">
        <span>X 原创冷却 ${gapH}h</span><span>${coolH.toFixed(1)}h / ${gapH}h</span>
      </div>
      <div class="bar ${coolPct>=100?'green':'amber'}"><i style="width:${coolPct}%"></i></div>
    </div>
  </div>

  <div class="grid g2">
    <div class="card">
      <h3>待发备稿 <span class="hint">按扫描时间倒序</span></h3>
      ${d.pending.length? `<ul class="list">${d.pending.map(p=>`
        <li><span class="pill ${p.gate==='pass'?'ok':(p.gate==='fail'?'bad':'mute')}">${p.gate==='pass'?'过闸':(p.gate==='fail'?'拦截':'未测')}</span>
          <div class="body"><div class="t">${esc(p.name)}</div>
          <div class="m">${esc(p.one_line||'（无 status.md 说明）')}</div></div>
          <span class="dim2 mono" style="white-space:nowrap">${agoText(p.scanned_at)}</span></li>`).join('')}
        </ul>` : '<div class="empty">没有待发备稿</div>'}
    </div>

    <div class="card">
      <h3>最近发布</h3>
      ${d.recent_published.length? `<ul class="list">${d.recent_published.map(e=>`
        <li>${platformPill(e.platform)}
          <div class="body"><div class="t">${e.url?`<a href="${escAttr(e.url)}" target="_blank" rel="noopener">${esc(e.topic_signature||e.id)}</a>`:esc(e.topic_signature||e.id)}</div>
          <div class="m">${esc(e.treatment||'')} ${e.media_count?`· ${e.media_count} 图`:''}</div></div>
          <span class="dim2 mono nowrap">${agoText(e.timestamp)}</span></li>`).join('')}
        </ul>` : '<div class="empty">暂无</div>'}
    </div>
  </div>`;
}

// ───────── 备稿 ─────────
let draftSel = null;
async function renderDrafts() {
  const d = await api('/api/drafts');
  const entries = d.entries || [];
  if (!draftSel && entries.length) draftSel = entries[0].name;
  const sel = entries.find(x=>x.name===draftSel);
  $('#tab-drafts').innerHTML = `
  <div class="split">
    <div>
      <input type="search" id="draftFilter" placeholder="过滤备稿…">
      <div style="margin-top:10px" id="draftList">
        ${entries.map(x=>`
          <div class="draft-item ${x.name===draftSel?'sel':''}" data-name="${escAttr(x.name)}">
            <div class="h"><span class="n">${esc(x.name)}</span>${gatePill(x.gate)}</div>
            <div class="d">${esc(x.summary||x.one_line||'')}</div>
            <div class="pillrow" style="margin-top:6px">
              ${x.has_x?`<span class="pill mute">X ${x.x_chars}字</span>`:''}
              ${x.has_xhs?`<span class="pill mute">XHS ${x.xhs_chars}字</span>`:''}
              ${x.published_x?'<span class="pill ok">X 已发</span>':'<span class="pill warn">X 未发</span>'}
              ${x.has_xhs?(x.published_xhs?'<span class="pill ok">XHS 已发</span>':'<span class="pill warn">XHS 未发</span>'):''}
              ${x.shots.length?`<span class="pill mute">${x.shots.length}图</span>`:''}
            </div>
          </div>`).join('')}
      </div>
    </div>
    <div id="draftDetail">${sel? draftDetail(sel):'<div class="empty">选一条备稿</div>'}</div>
  </div>`;

  $$('#draftList .draft-item').forEach(el=>el.onclick=()=>{ draftSel=el.dataset.name; renderDrafts(); });
  const f = $('#draftFilter');
  if (f) { f.oninput = ()=> {
      const q=f.value.toLowerCase();
      $$('#draftList .draft-item').forEach(el=>{
        el.style.display = el.textContent.toLowerCase().includes(q) ? '' : 'none'; });
    }; }
  $$('#draftDetail img').forEach(img=>img.onclick=()=>window.open(img.src,'_blank'));
  const askBtn = $('#askDraftBtn');
  if (askBtn) askBtn.onclick = ()=> {
      promptForDraft(sel);
  };
}

function draftDetail(x) {
  const matches = x.published || [];
  return `
  <div class="card">
    <h3>${esc(x.name)} <span class="hint">${esc(x.material_id||'')} ${x.slot?'· '+esc(x.slot):''} ${x.scanned_at?'· '+esc(x.scanned_at):''}</span></h3>
    <div class="pillrow" style="margin-bottom:12px">
      ${gatePill(x.gate)}
      ${x.published_x?'<span class="pill ok">X 已发</span>':'<span class="pill warn">X 未发</span>'}
      ${x.has_xhs?(x.published_xhs?'<span class="pill ok">XHS 已发</span>':'<span class="pill warn">XHS 未发</span>'):''}
      ${x.source_name?`<span class="pill mute">源:${esc(x.source_name)}</span>`:''}
      ${x.shots.length?`<span class="pill mute">${x.shots.length} 张真截图</span>`:''}
      ${matches.map(m=>`<a class="pill info" href="${escAttr(m.url)}" target="_blank" rel="noopener">${m.platform==='xiaohongshu'?'小红书已发':'X 已发'}</a>`).join('')}
    </div>
    ${matches.length?`<div class="small" style="margin-bottom:10px">台账匹配：${matches.map(m=>esc(m.why||'')).join('；')}</div>`:''}
    ${x.gate.note?`<div class="small" style="margin-bottom:10px;color:var(--amber)">⚠ ${esc(x.gate.note)}</div>`:''}
    ${x.gate.state!=='unknown'?`
      <div class="small" style="margin-bottom:10px">
        闸门 ${esc(x.gate.checked_at||'')} · 软分 ${esc(x.gate.soft_score??'—')}
        ${x.gate.hard_hits && x.gate.hard_hits.length?`· 硬命中 <span class="mono" style="color:var(--red)">${esc(x.gate.hard_hits.join(', '))}</span>`:''}
      </div>`:''}
    ${x.original_url?`<div class="small" style="margin-bottom:12px">原文：<a href="${escAttr(x.original_url)}" target="_blank" rel="noopener">${esc(x.original_url)}</a></div>`:''}
    ${x.summary?`<div style="font-size:13.5px;line-height:1.75;margin-bottom:12px">${esc(x.summary)}</div>`:''}
    ${(x.verified_facts||[]).length?`
      <div class="hr"></div><div class="small" style="color:var(--dim2);margin-bottom:6px">已核对事实</div>
      <ul class="md" style="padding-left:18px;margin:0">${x.verified_facts.map(f=>`<li>${esc(f)}</li>`).join('')}</ul>`:''}
    ${x.shots.length?`
      <div class="hr"></div><div class="small" style="color:var(--dim2);margin-bottom:6px">截图</div>
      <div class="shots">${x.shots.map(f=>`<img src="/api/draft/shot?name=${encodeURIComponent(x.name)}&file=${encodeURIComponent(f)}" alt="${escAttr(f)}">`).join('')}</div>`:''}
    <div class="hr"></div>
    <button class="btn primary" id="askDraftBtn">交给 Codex 处理这一条 →</button>
  </div>
  ${x.x_text?`<div class="card" style="margin-top:12px"><h3>X 正文 <span class="hint">${x.x_chars} 字 · sha ${esc((x.gate.sha256||'').slice(0,8))}</span></h3><pre>${esc(x.x_text)}</pre></div>`:''}
  ${x.xhs_text?`<div class="card" style="margin-top:12px"><h3>小红书正文 <span class="hint">${x.xhs_chars} 字</span></h3><pre>${esc(x.xhs_text)}</pre></div>`:''}
  ${x.status_md?`<div class="card" style="margin-top:12px"><h3>status.md</h3><div class="md">${md(x.status_md)}</div></div>`:''}`;
}

function promptForDraft(x) {
  const t = `处理备稿 outputs/${x.name}（材料在 outputs/${x.name}/material.yaml，已核对事实见 verified_facts）。
先读 state/forbidden.yaml 和 private/account-safety.yaml 的硬约束，再判断这条稿现在能不能发；
能发就按现有 publisher 流程走内置浏览器发布，不能发就如实说明卡在哪一步并写清原因。
注意：发布前必须出确认卡（站点/账号/标题/正文/图/可见性）。`;
  switchTab('ask');
  setTimeout(()=>{ $('#codexPrompt').value = t; $('#codexPrompt').focus(); }, 60);
}

// ───────── 已发 ─────────
async function renderPublished() {
  const d = await api('/api/published?limit=200');
  const q = ($('#pubSearch')?.value || '').trim();
  const rows = (q ? d.entries.filter(e=>JSON.stringify(e).toLowerCase().includes(q.toLowerCase())) : d.entries);
  $('#tab-published').innerHTML = `
  <div class="card">
    <h3>已发布台账 <span class="hint">${d.total} 条 · state/published-posts.json</span></h3>
    <input type="search" id="pubSearch" placeholder="搜索 topic / 触发来源 / URL…" value="${escAttr(q)}">
    <div class="hr"></div>
    <div class="table-wrap"><table><thead><tr><th>时间</th><th>平台</th><th>主题</th><th>处理方式</th><th>图</th><th>来源</th></tr></thead>
    <tbody>${rows.map(e=>`<tr>
      <td class="nowrap">${esc(e.timestamp||'')}</td>
      <td>${platformPill(e.platform)}</td>
      <td>${e.url?`<a href="${escAttr(e.url)}" target="_blank" rel="noopener">${esc(e.topic_signature||e.id)}</a>`:esc(e.topic_signature||e.id)}</td>
      <td class="dim2">${esc(e.treatment||'')}</td>
      <td class="nowrap">${e.media_count||0}</td>
      <td class="dim2">${esc((e.source||'').slice(0,70))}</td>
    </tr>`).join('')}</tbody></table></div>
    ${rows.length?'':'<div class="empty">没有匹配的记录</div>'}
  </div>`;
  $('#pubSearch').oninput = ()=>renderPublished();
}

// ───────── 互动 ─────────
async function renderOutbound() {
  const d = await api('/api/outbound?limit=200');
  const kinds = Object.entries(d.kinds).map(([k,v])=>`<span class="pill mute">${esc(k)} ${v}</span>`).join(' ');
  $('#tab-outbound').innerHTML = `
  <div class="card">
    <h3>互动台账 <span class="hint">${d.total} 条 · state/outbound-actions.json</span></h3>
    <div class="pillrow">${kinds}</div>
    <div class="hr"></div>
    <input type="search" id="outSearch" placeholder="搜索 handle / topic…">
    <div class="hr"></div>
    <div class="table-wrap"><table><thead><tr><th>时间</th><th>动作</th><th>对象</th><th>主题</th><th>验证</th></tr></thead>
    <tbody>${d.entries.map(e=>`<tr>
      <td class="nowrap">${esc(e.timestamp||'')}</td>
      <td><span class="pill ${e.action==='reply'?'info':(e.action==='like'?'mute':'warn')}">${esc(e.action||'')}</span></td>
      <td>${e.target_post_url?`<a href="${escAttr(e.target_post_url)}" target="_blank" rel="noopener">@${esc(e.target_handle)}</a>`:'@'+esc(e.target_handle||'')}</td>
      <td class="dim2">${esc(e.topic_signature||'')}</td>
      <td class="dim2">${esc((e.verification||'').slice(0,80))}</td>
    </tr>`).join('')}</tbody></table></div>
  </div>`;
  const s = $('#outSearch');
  s.oninput = ()=>{ const q=s.value.toLowerCase();
    $$('#tab-outbound tbody tr').forEach(tr=>{ tr.style.display = tr.textContent.toLowerCase().includes(q)?'':'none'; }); };
}

// ───────── 闸门 ─────────
async function renderGate() {
  const d = await api('/api/gate?limit=60');
  const pass = d.entries.filter(e=>e.passed).length;
  $('#tab-gate').innerHTML = `
  <div class="grid g2" style="align-items:start">
    <div class="card">
      <h3>文本体检 <span class="hint">跑 scripts/prepublish.py</span></h3>
      <textarea id="gateText" rows="7" placeholder="粘贴要发出去的正文，回车即跑闸门…"></textarea>
      <div style="margin-top:10px"><button class="btn primary" id="gateRun">跑闸门</button></div>
      <div id="gateOut" style="margin-top:12px"></div>
    </div>
    <div class="card">
      <h3>闸门回执 <span class="hint">最近 ${d.entries.length} 条 · 通过 ${pass}</span></h3>
      <ul class="list">${d.entries.map(e=>`
        <li><span class="pill ${e.passed?'ok':'bad'}">${e.passed?'过':'拦'}</span>
          <div class="body">
            <div class="t mono" style="font-size:11.5px">${esc(e.sha256||'').slice(0,16)} · ${e.chars||'?'}字 · 软分 ${e.soft_score??'—'}</div>
            <div class="m">${esc((e.reasons||[]).slice(0,2).join(' / ').slice(0,220))}</div>
          </div>
          <span class="dim2 mono nowrap">${esc(e.ts||'')}</span></li>`).join('')}</ul>
    </div>
  </div>`;
  $('#gateRun').onclick = async ()=>{
    const t = $('#gateText').value.trim();
    if (!t) { toast('先贴一段正文','bad'); return; }
    if (t.length > 8000) { toast(`正文 ${t.length} 字，超过闸门上限 8000 字，先截一段再跑`,'bad'); return; }
    $('#gateOut').innerHTML = '<div class="small"><span class="spin"></span> 跑闸门中…</div>';
    const r = await post('/api/gate/check', {text:t});
    $('#gateOut').innerHTML = `
      <div class="pillrow" style="margin-bottom:8px">
        <span class="pill ${r.passed?'ok':'bad'}">${r.passed?'通过':'拦截'}</span>
        <span class="pill mute">exit ${r.exit_code}</span>
      </div>
      <pre>${esc(r.stdout||r.stderr||'')}</pre>`;
  };
}

// ───────── 红线 ─────────
async function renderRules() {
  const d = await api('/api/rules');
  const f = d.forbidden || {};
  const list = (arr) => (arr||[]).map(x=>{
    if (typeof x === 'string') return `<li>${esc(x)}</li>`;
    return `<li><strong>${esc(x.id||'')}</strong> ${esc(x.desc||'')}
      <span class="pill ${x.severity==='hard'?'bad':'mute'}">${esc(x.severity||'')}</span>
      <span class="dim2 mono">${esc((x.scope||[]).join('/'))}</span></li>`;
  }).join('');
  const sec = (title, obj) => Object.entries(obj||{}).map(([k,v])=>`
    <div style="margin-bottom:10px"><div class="small" style="color:var(--dim2)">${esc(k)}</div>
    <div>${Array.isArray(v)? `<ul style="padding-left:18px;margin:4px 0">${v.map(i=>`<li>${esc(typeof i==='object'?JSON.stringify(i):i)}</li>`).join('')}</ul>`
      : `<pre style="margin-top:4px">${esc(JSON.stringify(v,null,2))}</pre>`}</div></div>`).join('');
  $('#tab-rules').innerHTML = `
  <div class="grid g2">
    <div class="card">
      <h3>禁忌清单 <span class="hint">state/forbidden.yaml</span></h3>
      ${Object.entries(f).map(([k,v])=>`
        <div style="margin-bottom:12px">
          <div class="small" style="color:var(--dim2);margin-bottom:4px">${esc(k)}</div>
          ${Array.isArray(v)?`<ul style="padding-left:18px;margin:0;font-size:13px">${list(v)}</ul>`:`<pre>${esc(JSON.stringify(v,null,2))}</pre>`}
        </div>`).join('')}
    </div>
    <div>
      <div class="card"><h3>X 文风 <span class="hint">style-x.yaml</span></h3>${sec('', d.style_x)}</div>
      <div class="card" style="margin-top:12px"><h3>小红书文风 <span class="hint">style-xhs.yaml</span></h3>${sec('', d.style_xhs)}</div>
      <div class="card" style="margin-top:12px"><h3>过滤规则 <span class="hint">filter-rules.yaml</span></h3>${sec('', d.filter)}</div>
    </div>
  </div>`;
}

// ───────── 交给 Codex ─────────
let codexJob = null, codexTimer = null;
async function renderAsk() {
  if (!$('#tab-ask').dataset.built) {
    $('#tab-ask').dataset.built = '1';
    $('#tab-ask').innerHTML = `
    <div class="card" style="margin-bottom:12px">
      <h3>交给 Codex <span class="hint">后端调 codex exec · 判断层仍然在 Codex 里</span></h3>
      <div class="pillrow" style="margin-bottom:10px">
        <button class="btn sm" data-preset="按这条新闻写一条 X">按这条新闻写 X</button>
        <button class="btn sm" data-preset="帮我写一条小红书">写小红书</button>
        <button class="btn sm" data-preset="跑一轮 pulse，去互动一下">跑一轮 pulse</button>
        <button class="btn sm" data-preset="今天 X 怎么样？给我一份摘要">今天 X 摘要</button>
        <button class="btn sm" data-preset="检查现在能不能发 X，说清卡在哪一步">检查能不能发</button>
      </div>
      <textarea id="codexPrompt" rows="6" placeholder="说人话就行，比如「按 https://xxx 写一条 X」…"></textarea>
      <div style="margin-top:10px;display:flex;gap:8px;align-items:center">
        <button class="btn primary" id="codexRun">跑</button>
        <span id="codexState" class="small"></span>
      </div>
      <div class="tabs-note" style="margin:10px 0 0">注意：这个入口跑的是无头 codex，会改仓库里的文件（state/ outputs/）。真发仍需内置浏览器里的 Codex 窗口。</div>
    </div>
    <div class="card"><h3>输出</h3><pre id="codexOut">（还没跑）</pre></div>`;
    $('#codexRun').onclick = runCodex;
    $$('#tab-ask [data-preset]').forEach(b=>b.onclick=()=>{ $('#codexPrompt').value=b.dataset.preset; });
  }
}
async function runCodex() {
  const p = $('#codexPrompt').value.trim();
  if (!p) { toast('先写点东西','bad'); return; }
  const r = await post('/api/codex', {prompt:p});
  codexJob = r.job_id;
  $('#codexState').innerHTML = '<span class="spin"></span> 跑着…';
  $('#codexOut').textContent = '（运行中）';
  clearInterval(codexTimer);
  codexTimer = setInterval(async ()=>{
    const j = await api('/api/codex/job?id='+codexJob);
    if (!j) return;
    if (j.status === 'running') { $('#codexOut').textContent = '（运行中…）'; return; }
    clearInterval(codexTimer);
    $('#codexState').textContent = j.status + (j.code!=null?' · exit '+j.code:'');
    const errLines = (j.error||'').split('\n').filter(l => l.trim()
      && !/^\s*\d{4}-\d{2}-\d{2}T.*WARN/.test(l)
      && !/^warning:/i.test(l.trim()));
    $('#codexOut').textContent = (j.output||'') + (errLines.length? ('\n\n[stderr]\n'+errLines.join('\n')) : '');
    toast('codex '+j.status, j.status==='done'?'ok':'bad');
    if (j.status==='done') renderOverview();
  }, 1500);
}

// ───────── tabs ─────────
function switchTab(name) {
  $$('#tabs button').forEach(b=>b.classList.toggle('active', b.dataset.tab===name));
  $$('.tab-panel').forEach(p=>p.classList.toggle('active', p.id==='tab-'+name));
  const map = {overview:renderOverview, drafts:renderDrafts, published:renderPublished,
               outbound:renderOutbound, gate:renderGate, rules:renderRules, ask:renderAsk};
  (map[name]||(()=>{}))();
}
$('#tabs').onclick = e=>{ const b=e.target.closest('button'); if (b) switchTab(b.dataset.tab); };
$('#refresh').onclick = ()=>{ switchTab($('#tabs button.active').dataset.tab); toast('已刷新','ok'); };

setInterval(()=>{ const a=$('#tabs button.active'); if (a && a.dataset.tab==='overview') renderOverview(); }, 30000);
function tick(){ const d=new Date(); $('#clock').textContent = d.toLocaleString('zh-CN',{hour12:false}); }
tick(); setInterval(tick,1000);
switchTab('overview');
