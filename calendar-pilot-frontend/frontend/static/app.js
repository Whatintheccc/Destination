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
    if (window.location.protocol !== 'file:') {
      throw _err;
    }
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
  const denialReason = action.denied_reason || action.why_user_sees_it || '';
  const canAskConfirmation = action.candidate_id && !/social|people-affecting/i.test(denialReason);
  const deniedControls = action.status === 'denied' ? `<div class="controls denial-controls">
    <button data-action="explain-denial" data-denial="${escapeHtml(denialReason)}">Explain denial</button>
    ${action.candidate_id ? `<button data-action="stage-denied" data-candidate="${escapeHtml(action.candidate_id)}">Stage instead</button>` : ''}
    ${canAskConfirmation ? `<button data-action="confirm-denied" data-candidate="${escapeHtml(action.candidate_id)}">Ask confirmation</button>` : ''}
    <button data-action="narrow-scope">Narrow scope</button>
    <button data-action="repair-denial" data-denial="${escapeHtml(denialReason)}">Repair profile</button>
  </div>` : '';
  const feedback = action.receipt_id ? `<div class="feedback">
    <button data-action="feedback" data-receipt="${receipt}" data-kind="accepted">Accepted</button>
    <button data-action="feedback" data-receipt="${receipt}" data-kind="explicit_useful">Useful</button>
    <button data-action="feedback" data-receipt="${receipt}" data-kind="explicit_wrong">Wrong</button>
    <button data-action="feedback" data-receipt="${receipt}" data-kind="explicit_not_needed">Not needed</button>
    <button data-action="feedback" data-receipt="${receipt}" data-kind="edited">Edited</button>
    <button data-action="feedback" data-receipt="${receipt}" data-kind="undone">Undone</button>
    <button data-action="feedback" data-receipt="${receipt}" data-kind="ignored">Ignored</button>
    <button data-action="feedback" data-receipt="${receipt}" data-kind="notification_dismissed">Dismissed</button>
    <button data-action="feedback" data-receipt="${receipt}" data-kind="downstream_conflict">Conflict</button>
  </div>` : '';
  return `<div class="action"><div><strong>${escapeHtml(action.label)}</strong><p class="purpose">${escapeHtml(action.why_user_sees_it || action.control_boundary)}</p><div><code>${receipt}</code></div>${action.candidate_id ? `<div>candidate: <code>${escapeHtml(action.candidate_id)}</code></div>` : ''}${action.rollback_handle_id ? `<div>undo: <code>${escapeHtml(action.rollback_handle_id)}</code></div>` : ''}${action.denied_reason ? `<div>denial: <code>${escapeHtml(action.denied_reason)}</code></div>` : ''}<div class="controls">${confirm}${undo}</div>${deniedControls}${feedback}</div><span class="status ${escapeHtml(action.status)}">${escapeHtml(action.status)}</span></div>`;
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

function renderUndoHistory(rows = []) {
  return rows.map(row => `<div class="history-item">
    <div><strong>${escapeHtml(row.provider_status || row.swift_status || 'undo')}</strong><span>${escapeHtml(row.rollback_handle_id || '')}</span></div>
    <div><span>before</span><code>${escapeHtml(row.checksum_before || '')}</code></div>
    <div><span>after</span><code>${escapeHtml(row.checksum_after || '')}</code></div>
    <div><span>reward</span>${escapeHtml(row.reward_event_id || '-')}</div>
  </div>`).join('') || '<p class="purpose">No undo journey yet.</p>';
}

function renderFeedbackHistory(rows = []) {
  return rows.slice(-8).reverse().map(row => `<div class="history-item">
    <div><strong>${escapeHtml(row.reward_event_id || 'reward')}</strong><span>${escapeHtml(row.receipt_id || '')}</span></div>
    <div><span>reward</span>${fmt(row.total_reward)}</div>
    <div><span>feedback</span>${fmt(row.feedback || {})}</div>
  </div>`).join('') || '<p class="purpose">No feedback yet.</p>';
}

function renderAuthorityGrants(rows = []) {
  return rows.slice(-8).reverse().map(grant => `<div class="history-item">
    <div><strong>${escapeHtml(grant.grant_id || 'grant')}</strong><span>${escapeHtml(grant.confirmation_provenance || '')}</span></div>
    <div><span>tier</span>${fmt(grant.max_authority_tier)}</div>
    <div><span>scopes</span>${fmt(grant.scopes || [])}</div>
    <div><span>expires</span>${fmt(grant.expires_at)}</div>
    <div><span>confirmed</span>${fmt(grant.confirmed_by_user)}</div>
  </div>`).join('') || '<p class="purpose">No grants issued yet.</p>';
}

function renderProfilePatch(state) {
  const pending = state.pending_profile_patch;
  const history = state.profile_patch_history || [];
  const claims = state.profile_claims || [];
  const pendingHtml = pending?.repair_plan ? `<div class="history-item">
    <div><strong>${escapeHtml(pending.repair_plan.candidate_claim || 'profile patch')}</strong><span>${escapeHtml(pending.repair_plan.prompt || '')}</span></div>
    <div><span>confidence</span>${fmt(pending.repair_plan.suggested_confidence)}</div>
    <div><span>correction</span>${escapeHtml(pending.correction || '')}</div>
    <div><button data-action="apply-profile-patch" data-claim="${escapeHtml(pending.repair_plan.candidate_claim || '')}" data-correction="${escapeHtml(pending.correction || '')}">Apply</button></div>
  </div>` : '';
  const historyHtml = history.slice(-4).reverse().map(row => `<div class="history-item">
    <div><strong>${escapeHtml(row.claim || 'claim')}</strong><span>${escapeHtml(row.correction || '')}</span></div>
    <div><span>status</span>${escapeHtml(row.receipt?.status || 'applied')}</div>
  </div>`).join('');
  const claimsHtml = claims.map(claim => `<div class="history-item">
    <div><strong>${escapeHtml(claim.claim || 'claim')}</strong><span>${escapeHtml(claim.source || 'profile')}</span></div>
    <div><span>confidence</span>${fmt(claim.confidence)}</div>
    <div><span>evidence</span>${fmt(claim.last_evidence || claim.updated_at)}</div>
    <div class="controls">
      <button data-action="repair-claim" data-claim="${escapeHtml(claim.claim || '')}">Edit</button>
      <button data-action="decay-claim" data-claim="${escapeHtml(claim.claim || '')}">Stale</button>
    </div>
  </div>`).join('');
  return pendingHtml + historyHtml + claimsHtml || '<p class="purpose">No profile patch pending.</p>';
}

function renderSelfPlay(rows = []) {
  return rows.slice(-4).reverse().map(row => `<div class="history-item">
    <div><strong>${escapeHtml(String(row.episodes || 0))} episodes</strong><span>${escapeHtml(row.created_at || '')}</span></div>
    <div><span>avg reward</span>${fmt(row.metrics?.average_reward)}</div>
    <div><span>undo rate</span>${fmt(row.metrics?.undo_rate)}</div>
    <div><span>decision</span>${fmt(row.release_decision?.decision)}</div>
    <div><span>failures</span>${fmt(row.top_failure_modes || [])}</div>
  </div>`).join('') || '<p class="purpose">No self-play probe run yet.</p>';
}

function renderReplayExplorer(query) {
  const exportInfo = appState?.last_replay_export;
  if (!query && !exportInfo) return '<p class="purpose">No replay query yet.</p>';
  const exportHtml = exportInfo ? `<div class="history-item">
    <div><strong>JSONL export</strong><span>${escapeHtml(exportInfo.created_at || '')}</span></div>
    <div><span>records</span>${fmt(exportInfo.record_count)}</div>
    <div><span>path</span><code>${escapeHtml(exportInfo.path || '')}</code></div>
  </div>` : '';
  if (!query) return exportHtml;
  const summary = query.summary || {};
  const traces = query.traces || [];
  return `${exportHtml}<div class="history-item">
    <div><strong>${fmt(summary.records)} records</strong><span>query result</span></div>
    <div><span>decisions</span>${fmt(summary.decisions)}</div>
    <div><span>rewards</span>${fmt(summary.rewards)}</div>
    <div><span>traces</span>${fmt(traces.length)}</div>
  </div>${traces.slice(-5).map(trace => `<div class="history-item"><div><strong>${escapeHtml(trace.record_type || 'record')}</strong></div><div>${fmt(trace.payload || {})}</div></div>`).join('')}`;
}

function renderDenials(rows = []) {
  return rows.slice(-6).reverse().map(row => `<div class="history-item">
    <div><strong>${escapeHtml(row.denied_reason || 'denial')}</strong><span>${escapeHtml(row.created_at || '')}</span></div>
    <div>${escapeHtml(row.explanation || '')}</div>
    <div><span>next controls</span>${fmt((row.suggested_controls || []).map(item => item.label))}</div>
  </div>`).join('') || '<p class="purpose">No denials explained yet.</p>';
}

function syncInputs(state) {
  const session = state.session || {};
  const tier = session.authority_tier ?? 3;
  document.getElementById('authority-tier').value = tier;
  document.getElementById('authority-editor-tier').value = tier;
  document.getElementById('authority-scopes').value = (session.authority_scopes || ['recommend', 'stage', 'commit_private', 'undo']).join(',');
}

function render(state) {
  appState = state;
  const snapshot = state.snapshot || state;
  hideError();
  syncInputs(state);
  document.getElementById('next-action').textContent = snapshot.summary?.recommended_next_action || 'enter goal';
  document.getElementById('panels').innerHTML = (snapshot.panels || []).map(renderPanel).join('') || '<article class="panel"><h2>No plan yet</h2><p class="purpose">Create a plan to populate machine-learning and machine-acting surfaces.</p></article>';
  document.getElementById('action-queue').innerHTML = (snapshot.action_queue || []).map(renderAction).join('') || '<p class="purpose">No machine acts queued.</p>';
  document.getElementById('undo-history').innerHTML = renderUndoHistory(state.undo_history || []);
  document.getElementById('feedback-history').innerHTML = renderFeedbackHistory(state.feedback_history || []);
  document.getElementById('trace').innerHTML = (snapshot.trace || []).map(renderTrace).join('');
  document.getElementById('replay-summary').innerHTML = renderSummary(state);
  document.getElementById('authority-grants').innerHTML = renderAuthorityGrants(state.authority_grants || []);
  document.getElementById('profile-patch').innerHTML = renderProfilePatch(state);
  document.getElementById('self-play-history').innerHTML = renderSelfPlay(state.self_play_history || []);
  document.getElementById('replay-explorer').innerHTML = renderReplayExplorer(state.last_replay_query);
  document.getElementById('denial-history').innerHTML = renderDenials(state.denial_history || []);
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
  if (action === 'apply-profile-patch') post('/api/profile/patch/apply', { claim: button.dataset.claim, correction: button.dataset.correction, confirmed: true });
  if (action === 'stage-denied') post(`/api/candidates/${encodeURIComponent(button.dataset.candidate)}/stage`);
  if (action === 'confirm-denied') post(`/api/candidates/${encodeURIComponent(button.dataset.candidate)}/confirm`);
  if (action === 'narrow-scope') post('/api/authority', { authority_tier: 2, scopes: ['recommend', 'stage', 'undo'] });
  if (action === 'repair-denial') {
    const correction = window.prompt('Profile correction for this denial:', button.dataset.denial || '');
    if (correction) post('/api/profile/patch/propose', { correction });
  }
  if (action === 'decay-claim') {
    if (window.confirm('Mark this learned claim stale and lower confidence?')) {
      post('/api/profile/patch/apply', { claim: button.dataset.claim, correction: 'Marked stale during dogfood profile review', confirmed: true });
    }
  }
  if (action === 'repair-claim') {
    const correction = window.prompt('Correction for this learned claim:', button.dataset.claim || '');
    if (correction) post('/api/profile/patch/propose', { correction });
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

document.getElementById('authority-form').addEventListener('submit', event => {
  event.preventDefault();
  post('/api/authority', {
    authority_tier: Number(document.getElementById('authority-editor-tier').value || 3),
    scopes: document.getElementById('authority-scopes').value,
  });
});

document.getElementById('replay-form').addEventListener('submit', event => {
  event.preventDefault();
  const query = document.getElementById('replay-query').value.trim();
  const suffix = replayQuerySuffix(query);
  if (!apiMode) return showError('Replay query requires the served app.');
  setBusy(true);
  request(`/api/replay${suffix}`).then(state => {
    appState = state;
    render(state);
  }).catch(err => showError(String(err.message || err))).finally(() => setBusy(false));
});

document.getElementById('self-play-form').addEventListener('submit', event => {
  event.preventDefault();
  post('/api/self-play', { episodes: Number(document.getElementById('self-play-episodes').value || 3) });
});

document.getElementById('export-replay').addEventListener('click', event => {
  event.preventDefault();
  const suffix = replayQuerySuffix(document.getElementById('replay-query').value.trim());
  if (!apiMode) return showError('Replay export requires the served app.');
  setBusy(true);
  request(`/api/replay/export${suffix}`).then(state => {
    appState = state;
    render(state);
  }).catch(err => showError(String(err.message || err))).finally(() => setBusy(false));
});

function replayQuerySuffix(raw) {
  if (!raw) return '';
  const [prefix, ...rest] = raw.split(':');
  const value = rest.join(':').trim();
  const keyMap = {
    candidate: 'candidate_id',
    trace: 'trace_id',
    receipt: 'receipt_id',
    grant: 'authority_grant_id',
    rollback: 'rollback_handle_id',
    reward: 'reward_event_id',
  };
  if (value && keyMap[prefix]) return `?${keyMap[prefix]}=${encodeURIComponent(value)}`;
  return `?q=${encodeURIComponent(raw)}`;
}

document.getElementById('refresh').addEventListener('click', async () => {
  appState = await loadState();
  render(appState);
});

document.getElementById('reset').addEventListener('click', () => post('/api/reset'));

loadState().then(render).catch(err => {
  showError(String(err));
});
