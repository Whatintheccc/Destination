const app = {
  state: null,
  inspectorTab: 'runtime',
  pending: false,
};

const $ = (sel) => document.querySelector(sel);
const escapeHtml = (text) => String(text ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch]));
const fmt = (value) => {
  if (value === null || value === undefined || value === '') return '—';
  if (Array.isArray(value)) return value.length ? value.map(v => escapeHtml(String(v))).join(', ') : '—';
  if (typeof value === 'object') return `<code>${escapeHtml(JSON.stringify(value))}</code>`;
  return escapeHtml(String(value));
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    cache: 'no-store',
    headers: {'Content-Type': 'application/json', ...(options.headers || {})},
    ...options,
    body: options.body && typeof options.body !== 'string' ? JSON.stringify(options.body) : options.body,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (payload.state) return payload.state;
    throw new Error(payload.error || `${response.status} ${response.statusText}`);
  }
  return payload;
}

async function loadState() {
  try {
    return await api('/api/state');
  } catch (err) {
    const response = await fetch('frontend_state.sample.json', { cache: 'no-cache' });
    const state = await response.json();
    state.offline = true;
    state.runtime = {
      runtime_mode: 'fixture',
      mode_label: 'Offline fixture fallback',
      offline_fixture_fallback: true,
      backends: {
        kernel: 'static_sample',
        codex: 'static_sample',
        diffusiongemma: 'static_sample',
        provider: 'static_sample',
      },
      live_blockers: ['backend /api/state unavailable'],
    };
    state.session = {...(state.session || {}), runtime_mode: 'fixture'};
    return state;
  }
}

function setPending(pending) {
  app.pending = pending;
  document.querySelectorAll('button, textarea').forEach(el => {
    if (el.id === 'inspector-toggle' || el.id === 'close-inspector') return;
    el.disabled = pending;
  });
}

async function refresh(nextState) {
  app.state = nextState || await loadState();
  render();
}

function render() {
  const state = app.state || {};
  renderSidebar(state.sidebar || {});
  renderChat((state.chat || {}).messages || []);
  renderInspector(state.inspector || {});
  renderRuntimeChip(state.runtime || state.chat?.runtime || {});
  const tier = state.session?.authority_tier ?? '—';
  const scopes = (state.session?.authority_scopes || []).join(', ') || 'no scopes';
  $('#authority-chip').textContent = `Tier ${tier}: ${scopes}`;
}

function renderRuntimeChip(runtime) {
  const label = runtime.mode_label || runtime.label || runtime.runtime_mode || 'Fixture mode';
  const chip = $('#runtime-chip');
  if (!chip) return;
  chip.textContent = label;
  chip.title = runtime.live_blockers?.length ? `Blocked: ${runtime.live_blockers.join('; ')}` : label;
  chip.classList.toggle('danger', Boolean(runtime.live_blockers?.length));
}

function renderSidebar(sidebar) {
  const sessions = sidebar.sessions?.length ? sidebar.sessions : [{label: 'Current fixture run', active: true}];
  $('#session-list').innerHTML = sessions.map(s => `<div class="nav-item ${s.active ? 'active' : ''}">${escapeHtml(s.label || s.session_id || 'Session')}</div>`).join('');
  const runs = sidebar.recent_runs?.length ? sidebar.recent_runs : [{label: 'No dogfood runs yet'}];
  $('#recent-runs').innerHTML = runs.map(r => `<div class="nav-item">${escapeHtml(r.label || r.plan_id || 'Run')}</div>`).join('');
}

function renderChat(messages) {
  const transcript = $('#chat-transcript');
  transcript.innerHTML = messages.map(renderMessage).join('');
  transcript.scrollTop = transcript.scrollHeight;
}

function renderMessage(message) {
  const role = message.role === 'user' ? 'user' : 'assistant';
  const title = message.title ? `<h3>${escapeHtml(message.title)}</h3>` : '';
  const body = message.body ? `<p>${escapeHtml(message.body)}</p>` : '';
  const cards = (message.cards || []).map(renderCard).join('');
  return `<article class="message ${role}" data-testid="message-${role}"><div class="avatar"></div><div class="bubble">${title}${body}<div class="cards">${cards}</div></div></article>`;
}

function renderCard(card) {
  if (card.type === 'candidate') return renderCandidateCard(card);
  if (card.type === 'receipt') return renderReceiptCard(card.receipt ? normalizeReceiptCard(card.receipt) : card);
  if (card.type === 'action_queue') return (card.actions || []).map(renderActionQueueCard).join('');
  return `<div class="card"><pre>${escapeHtml(JSON.stringify(card, null, 2))}</pre></div>`;
}

function normalizeReceiptCard(receipt) {
  const output = receipt.output || {};
  const swift = output.swift_receipt || output.receipt || {};
  return {
    type: 'receipt',
    receipt_id: swift.receipt_id || receipt.swift_receipt_id || receipt.tool_call_id,
    title: receipt.denied_reason ? 'Swift denied the action' : (receipt.status === 'committed' ? 'Committed calendar change' : 'Swift receipt'),
    status: receipt.status,
    rollback_handle_id: swift.rollback_handle_id,
    requires_confirmation: receipt.requires_user_confirmation,
    grant_id: receipt.authority_grant_id,
    body: receipt.denied_reason || `Stage state: ${receipt.stage_state || swift.stage_state || 'no_op'}`,
    candidate_id: swift.candidate_id,
  };
}

function renderCandidateCard(card) {
  const story = (card.model_story || []).map(line => `<li>${escapeHtml(line)}</li>`).join('');
  const reward = Object.entries(card.reward_breakdown || {}).slice(0, 5).map(([k, v]) => `<span class="badge">${escapeHtml(k)} ${escapeHtml(v)}</span>`).join(' ');
  const candidateId = escapeHtml(card.candidate_id || '');
  return `<div class="card candidate-card" data-testid="candidate-card" data-candidate-id="${candidateId}">
    <div class="card-header">
      <div><h4>${escapeHtml(card.title || 'Candidate action')}</h4><p>${escapeHtml(card.subtitle || '')}</p></div>
      <span class="badge">Tier ${escapeHtml(card.required_authority_tier ?? '—')}</span>
    </div>
    ${story ? `<ol class="story">${story}</ol>` : ''}
    <div>${reward}</div>
    <div class="card-actions">
      <button class="secondary simulate-btn" data-testid="simulate-candidate" data-candidate-id="${candidateId}">Simulate</button>
      <button class="secondary stage-btn" data-testid="stage-candidate" data-candidate-id="${candidateId}">Stage</button>
      <button class="primary commit-btn" data-testid="commit-candidate" data-candidate-id="${candidateId}">Commit with Swift</button>
    </div>
  </div>`;
}

function renderReceiptCard(card) {
  const statusClass = card.status === 'denied' ? 'danger' : (card.status === 'committed' ? 'ok' : '');
  const rollback = card.rollback_handle_id ? `<button class="secondary undo-btn" data-testid="undo-action" data-rollback="${escapeHtml(card.rollback_handle_id)}">Undo</button>` : '';
  const feedback = card.receipt_id ? `<button class="secondary feedback-useful" data-testid="feedback-useful" data-receipt-id="${escapeHtml(card.receipt_id)}">Useful</button><button class="secondary feedback-wrong" data-receipt-id="${escapeHtml(card.receipt_id)}">Wrong</button>` : '';
  const explain = card.status === 'denied' ? `<button class="secondary explain-denial" data-denied-reason="${escapeHtml(card.body || '')}">Explain denial</button>` : '';
  return `<div class="card receipt-card" data-testid="receipt-card">
    <div class="card-header"><div><h4>${escapeHtml(card.title || 'Receipt')}</h4><p>${escapeHtml(card.body || '')}</p></div><span class="badge ${statusClass}">${escapeHtml(card.status || 'receipt')}</span></div>
    <div class="kv"><div class="k">receipt</div><div class="v"><code>${escapeHtml(card.receipt_id || '—')}</code></div></div>
    <div class="kv"><div class="k">grant</div><div class="v"><code>${escapeHtml(card.grant_id || '—')}</code></div></div>
    <div class="card-actions">${rollback}${feedback}${explain}</div>
  </div>`;
}

function renderActionQueueCard(action) {
  return renderReceiptCard({
    receipt_id: action.receipt_id,
    title: action.label,
    status: action.status,
    rollback_handle_id: action.rollback_handle_id,
    requires_confirmation: action.requires_confirmation,
    grant_id: action.grant_id,
    body: action.why_user_sees_it,
  });
}

function renderInspector(inspector) {
  document.querySelectorAll('.tab').forEach(tab => tab.classList.toggle('active', tab.dataset.tab === app.inspectorTab));
  const data = inspector[app.inspectorTab] || {};
  const content = $('#inspector-content');
  if (app.inspectorTab === 'runtime') content.innerHTML = renderRuntime(data, app.state?.runtime || {});
  else if (app.inspectorTab === 'authority') content.innerHTML = renderAuthority(data);
  else if (app.inspectorTab === 'profile') content.innerHTML = renderProfile(data);
  else if (app.inspectorTab === 'replay') content.innerHTML = renderReplay(data);
  else if (app.inspectorTab === 'self_play') content.innerHTML = renderSelfPlay(data);
  else if (app.inspectorTab === 'provider') content.innerHTML = renderRows(data.title || 'Provider', data.rows || []);
  else content.innerHTML = renderDebug(data);
}

function renderRuntime(data, runtime) {
  const report = data.report || runtime || {};
  const rows = data.rows?.length ? data.rows : [
    {key: 'mode', value: report.mode_label || report.runtime_mode || 'Fixture mode'},
    {key: 'kernel', value: report.backends?.kernel},
    {key: 'codex', value: report.backends?.codex},
    {key: 'diffusiongemma', value: report.backends?.diffusiongemma},
    {key: 'provider', value: report.backends?.provider},
    {key: 'live_blockers', value: report.live_blockers?.length ? report.live_blockers : 'none'},
  ];
  return `${renderRows(data.title || 'Runtime mode', rows)}
    <div class="inspector-card"><h3>Runtime report</h3><pre>${escapeHtml(JSON.stringify(report, null, 2))}</pre></div>`;
}

function renderRows(title, rows) {
  const body = (rows || []).map(row => `<div class="inspector-card">${Object.entries(row).map(([k,v]) => `<div class="kv"><div class="k">${escapeHtml(k)}</div><div class="v">${fmt(v)}</div></div>`).join('')}</div>`).join('') || '<p class="muted">No records yet.</p>';
  return `<div class="inspector-card"><h3>${escapeHtml(title)}</h3></div>${body}`;
}

function renderAuthority(data) {
  return `<div class="inspector-card"><h3>Authority scopes</h3><p class="muted">Codex can request; Swift grants and validates.</p>
    <label>Tier <input id="authority-tier" type="number" min="0" max="6" value="${escapeHtml(app.state?.session?.authority_tier ?? 3)}" /></label>
    <label>Scopes <input id="authority-scopes" value="${escapeHtml((app.state?.session?.authority_scopes || []).join(', '))}" /></label>
    <div class="card-actions"><button id="save-authority" class="primary">Save authority</button></div></div>
    ${renderRows('Recent grants', data.history || data.rows || [])}`;
}

function renderProfile(data) {
  return `${renderRows('Learned profile claims', data.rows || [])}
    <div class="inspector-card"><h3>Repair profile</h3><textarea id="profile-correction" rows="3" placeholder="e.g. I do not want focus blocks on Friday afternoons"></textarea>
    <div class="card-actions"><button id="propose-profile" class="secondary">Propose patch</button><button id="apply-profile" class="primary">Apply confirmed patch</button></div></div>
    ${renderRows('Patch history', data.patch_history || [])}`;
}

function renderReplay(data) {
  return `<div class="inspector-card"><h3>Replay explorer</h3><p class="muted">${escapeHtml(data.export_hint || 'Export causal records.')}</p>
    <div class="card-actions"><button id="refresh-replay" class="secondary">Refresh</button><button id="replay-export" data-testid="replay-export" class="primary">Export JSON</button></div>
    <pre id="replay-json">${escapeHtml(JSON.stringify(data.summary || {}, null, 2))}</pre></div>`;
}

function renderSelfPlay(data) {
  return `${renderRows('Latest failure modes', data.history || data.rows || [])}<div class="inspector-card"><h3>Run release gate</h3><label>Episodes <input id="self-play-episodes" type="number" min="1" max="20" value="3" /></label><div class="card-actions"><button id="run-self-play" data-testid="run-self-play" class="primary">Run self-play</button></div></div>`;
}

function renderDebug(data) {
  return `<div class="inspector-card"><h3>Dogfood trace</h3><div class="card-actions"><button id="reset-fixture" class="secondary">Reset fixture</button></div><pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre></div>`;
}

async function sendGoal(goal) {
  setPending(true);
  try {
    const state = await api('/api/plans', {method: 'POST', body: {goal, commit: false}});
    await refresh(state);
  } finally { setPending(false); }
}

async function postAndRefresh(path, body = {}) {
  setPending(true);
  try {
    const state = await api(path, {method: 'POST', body});
    await refresh(state);
  } catch (err) {
    showToast(err.message);
  } finally { setPending(false); }
}

function showToast(text) {
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = text;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 2200);
}

document.addEventListener('submit', (event) => {
  if (event.target.id === 'composer') {
    event.preventDefault();
    const input = $('#goal-input');
    const goal = input.value.trim();
    if (!goal) return;
    input.value = '';
    sendGoal(goal);
  }
});

document.addEventListener('click', async (event) => {
  const target = event.target.closest('button');
  if (!target) return;
  if (target.id === 'inspector-toggle') { $('#inspector').classList.toggle('closed'); return; }
  if (target.id === 'close-inspector') { $('#inspector').classList.add('closed'); return; }
  if (target.classList.contains('tab')) { app.inspectorTab = target.dataset.tab; renderInspector(app.state.inspector || {}); return; }
  if (target.id === 'new-chat') { await postAndRefresh('/api/reset'); return; }
  const candidateId = target.dataset.candidateId;
  if (target.classList.contains('simulate-btn')) return postAndRefresh(`/api/candidates/${candidateId}/simulate`);
  if (target.classList.contains('stage-btn')) return postAndRefresh(`/api/candidates/${candidateId}/stage`);
  if (target.classList.contains('commit-btn')) return postAndRefresh(`/api/candidates/${candidateId}/commit`, {confirmed: true});
  if (target.classList.contains('undo-btn')) return postAndRefresh('/api/undo', {rollback_handle_id: target.dataset.rollback});
  if (target.classList.contains('feedback-useful')) return postAndRefresh('/api/feedback', {receipt_id: target.dataset.receiptId, feedback: 'useful'});
  if (target.classList.contains('feedback-wrong')) return postAndRefresh('/api/feedback', {receipt_id: target.dataset.receiptId, feedback: 'wrong'});
  if (target.classList.contains('explain-denial')) return postAndRefresh('/api/denials/explain', {denied_reason: target.dataset.deniedReason});
  if (target.id === 'save-authority') {
    const tier = Number($('#authority-tier').value || 3);
    const scopes = $('#authority-scopes').value.split(',').map(s => s.trim()).filter(Boolean);
    return postAndRefresh('/api/authority', {max_authority_tier: tier, scopes, confirmed: true});
  }
  if (target.id === 'propose-profile') return postAndRefresh('/api/profile/patch/propose', {correction: $('#profile-correction').value});
  if (target.id === 'apply-profile') return postAndRefresh('/api/profile/patch/apply', {claim: 'user correction', correction: $('#profile-correction').value, confirmed: true});
  if (target.id === 'run-self-play') return postAndRefresh('/api/self-play', {episodes: Number($('#self-play-episodes').value || 3)});
  if (target.id === 'refresh-replay') { app.inspectorTab = 'replay'; await refresh(); return; }
  if (target.id === 'replay-export' || target.id === 'replay-export-sidebar') {
    const exported = await api('/api/replay/export');
    app.inspectorTab = 'replay';
    $('#inspector').classList.remove('closed');
    renderInspector({replay: {summary: exported.summary, export_hint: 'Full replay export loaded below.'}});
    const out = $('#replay-json');
    if (out) out.textContent = JSON.stringify(exported, null, 2);
    showToast('Replay export loaded');
    return;
  }
  if (target.id === 'reset-fixture') return postAndRefresh('/api/reset');
});

$('#goal-input').addEventListener('input', (event) => {
  event.target.style.height = 'auto';
  event.target.style.height = `${Math.min(event.target.scrollHeight, 160)}px`;
});

refresh();
