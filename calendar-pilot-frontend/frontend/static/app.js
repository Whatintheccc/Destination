let appState = null;
let apiMode = true;

async function request(path, options = {}) {
  const response = await fetch(path, {
    cache: 'no-cache',
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || `${response.status} ${response.statusText}`);
  }
  return payload;
}

async function loadState() {
  try {
    const live = await request('/api/state');
    apiMode = true;
    return live;
  } catch (_err) {
    apiMode = false;
    const response = await fetch('frontend_state.sample.json', { cache: 'no-cache' });
    return { snapshot: await response.json(), replay_summary: null, training_rows: [] };
  }
}

async function post(path, body = {}) {
  if (!apiMode) {
    showError('Open the served app to use controls: PYTHONPATH=src python3 -m calendar_pilot.app frontend --serve');
    return;
  }
  setBusy(true);
  try {
    appState = await request(path, { method: 'POST', body: JSON.stringify(body) });
    render(appState);
  } catch (err) {
    showError(String(err.message || err));
  } finally {
    setBusy(false);
  }
}

function fmt(value) {
  if (Array.isArray(value)) return value.length ? value.map(fmt).join(', ') : '-';
  if (value && typeof value === 'object') return `<code>${escapeHtml(JSON.stringify(value))}</code>`;
  if (value === null || value === undefined || value === '') return '-';
  return escapeHtml(String(value));
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch]));
}

function renderPanel(panel) {
  const rows = (panel.rows || []).map(row => {
    const entries = Object.entries(row).slice(0, 10).map(([k, v]) => `<div class="kv"><div class="k">${escapeHtml(k)}</div><div class="v">${fmt(v)}</div></div>`).join('');
    return `<div class="row">${entries}${renderRowControls(panel.panel_id, row)}</div>`;
  }).join('') || '<p class="purpose">No records yet.</p>';
  return `<article class="panel"><div class="badge">${escapeHtml(panel.surface_type)}</div><h2>${escapeHtml(panel.title)}</h2><p class="purpose">${escapeHtml(panel.user_question)}</p>${rows}</article>`;
}

function renderRowControls(panelId, row) {
  if (panelId === 'candidate_frontier' && row.candidate_id) {
    const id = escapeHtml(row.candidate_id);
    return `<div class="controls">
      <button data-action="simulate" data-candidate="${id}">Simulate</button>
      <button data-action="stage" data-candidate="${id}">Stage</button>
      <button data-action="commit" data-candidate="${id}">Commit</button>
    </div>`;
  }
  if (panelId === 'biography_repair' && row.claim) {
    return `<div class="controls">
      <button data-action="repair-claim" data-claim="${escapeHtml(row.claim)}">Repair</button>
    </div>`;
  }
  return '';
}

function renderAction(action) {
  const receipt = escapeHtml(action.receipt_id || action.action_id || '');
  const undo = action.rollback_handle_id ? `<button data-action="undo" data-rollback="${escapeHtml(action.rollback_handle_id)}">Undo</button>` : '';
  const confirm = action.receipt_id && ['stageable', 'staged', 'requires_confirmation'].includes(action.status)
    ? `<button data-action="confirm" data-receipt="${receipt}">Confirm</button>` : '';
  const feedback = action.receipt_id ? `<div class="feedback">
    <button data-action="feedback" data-receipt="${receipt}" data-kind="explicit_useful">Useful</button>
    <button data-action="feedback" data-receipt="${receipt}" data-kind="explicit_wrong">Wrong</button>
    <button data-action="feedback" data-receipt="${receipt}" data-kind="explicit_not_needed">Not needed</button>
    <button data-action="feedback" data-receipt="${receipt}" data-kind="ignored">Ignored</button>
  </div>` : '';
  return `<div class="action"><div><strong>${escapeHtml(action.label)}</strong><p class="purpose">${escapeHtml(action.why_user_sees_it || action.control_boundary)}</p><div><code>${receipt}</code></div>${action.rollback_handle_id ? `<div>undo: <code>${escapeHtml(action.rollback_handle_id)}</code></div>` : ''}<div class="controls">${confirm}${undo}</div>${feedback}</div><span class="status ${escapeHtml(action.status)}">${escapeHtml(action.status)}</span></div>`;
}

function renderTrace(item) {
  const denial = item.denied_reason || '';
  const explain = denial ? `<button data-action="explain-denial" data-denial="${escapeHtml(denial)}">Explain</button>` : '';
  return `<div class="trace-item"><div><code>${escapeHtml(item.tool)}</code></div><div>${escapeHtml(item.status)}</div><div>${escapeHtml(denial || item.stage_state || '')}</div><div>${explain}</div></div>`;
}

function renderSummary(state) {
  const replay = state.replay_summary || {};
  const session = state.session || {};
  const rows = [
    ['records', replay.records],
    ['tool calls', replay.tool_calls],
    ['receipts', replay.receipts],
    ['rewards', replay.rewards],
    ['training rows', (state.training_rows || []).length],
    ['provider checksum', session.provider_checksum],
  ];
  return rows.map(([k, v]) => `<div><span>${escapeHtml(k)}</span><strong>${fmt(v)}</strong></div>`).join('');
}

function render(state) {
  appState = state;
  const snapshot = state.snapshot || state;
  hideError();
  document.getElementById('next-action').textContent = snapshot.summary?.recommended_next_action || 'enter goal';
  document.getElementById('panels').innerHTML = (snapshot.panels || []).map(renderPanel).join('') || '<article class="panel"><h2>No plan yet</h2><p class="purpose">Create a plan to populate machine-learning and machine-acting surfaces.</p></article>';
  document.getElementById('action-queue').innerHTML = (snapshot.action_queue || []).map(renderAction).join('') || '<p class="purpose">No machine acts queued.</p>';
  document.getElementById('trace').innerHTML = (snapshot.trace || []).map(renderTrace).join('');
  document.getElementById('replay-summary').innerHTML = renderSummary(state);
}

function showError(message) {
  const node = document.getElementById('error');
  node.hidden = false;
  node.textContent = message;
}

function hideError() {
  const node = document.getElementById('error');
  node.hidden = true;
  node.textContent = '';
}

function setBusy(busy) {
  document.querySelectorAll('button, input').forEach(el => {
    if (el.id !== 'goal-input') el.disabled = busy;
  });
}

document.addEventListener('click', event => {
  const button = event.target.closest('button[data-action]');
  if (!button) return;
  const action = button.dataset.action;
  if (action === 'simulate') post(`/api/candidates/${encodeURIComponent(button.dataset.candidate)}/simulate`);
  if (action === 'stage') post(`/api/candidates/${encodeURIComponent(button.dataset.candidate)}/stage`);
  if (action === 'commit') post(`/api/candidates/${encodeURIComponent(button.dataset.candidate)}/commit`);
  if (action === 'confirm') post(`/api/receipts/${encodeURIComponent(button.dataset.receipt)}/confirm`);
  if (action === 'undo') post('/api/undo', { rollback_handle_id: button.dataset.rollback });
  if (action === 'feedback') post('/api/feedback', { receipt_id: button.dataset.receipt, feedback: { [button.dataset.kind]: true } });
  if (action === 'explain-denial') post('/api/denials/explain', { denied_reason: button.dataset.denial });
  if (action === 'repair-claim') {
    const correction = window.prompt('Correction for this learned claim:', button.dataset.claim || '');
    if (correction) post('/api/profile/patch/apply', { claim: button.dataset.claim, correction, confirmed: true });
  }
});

document.getElementById('goal-form').addEventListener('submit', event => {
  event.preventDefault();
  post('/api/plans', {
    goal: document.getElementById('goal-input').value,
    authority_tier: Number(document.getElementById('authority-tier').value || 3),
    commit: document.getElementById('commit-now').checked,
  });
});

document.getElementById('profile-form').addEventListener('submit', event => {
  event.preventDefault();
  post('/api/profile/patch/propose', { correction: document.getElementById('profile-correction').value });
});

document.getElementById('refresh').addEventListener('click', async () => {
  appState = await loadState();
  render(appState);
});

document.getElementById('reset').addEventListener('click', () => post('/api/reset'));

loadState().then(render).catch(err => {
  showError(String(err));
});
