async function loadState() {
  const response = await fetch('frontend_state.sample.json', { cache: 'no-cache' });
  return response.json();
}
function fmt(value) {
  if (Array.isArray(value)) return value.length ? value.map(fmt).join(', ') : '—';
  if (value && typeof value === 'object') return `<code>${escapeHtml(JSON.stringify(value))}</code>`;
  if (value === null || value === undefined || value === '') return '—';
  return escapeHtml(String(value));
}
function escapeHtml(text) {
  return text.replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch]));
}
function renderPanel(panel) {
  const rows = (panel.rows || []).map(row => {
    const entries = Object.entries(row).slice(0, 10).map(([k, v]) => `<div class="kv"><div class="k">${escapeHtml(k)}</div><div class="v">${fmt(v)}</div></div>`).join('');
    return `<div class="row">${entries}</div>`;
  }).join('') || '<p class="purpose">No records yet.</p>';
  return `<article class="panel"><div class="badge">${escapeHtml(panel.surface_type)}</div><h2>${escapeHtml(panel.title)}</h2><p class="purpose">${escapeHtml(panel.user_question)}</p>${rows}</article>`;
}
function renderAction(action) {
  return `<div class="action"><div><strong>${escapeHtml(action.label)}</strong><p class="purpose">${escapeHtml(action.why_user_sees_it || action.control_boundary)}</p><div><code>${escapeHtml(action.receipt_id || action.action_id)}</code></div>${action.rollback_handle_id ? `<div>undo: <code>${escapeHtml(action.rollback_handle_id)}</code></div>` : ''}</div><span class="status ${escapeHtml(action.status)}">${escapeHtml(action.status)}</span></div>`;
}
function renderTrace(item) {
  return `<div class="trace-item"><div><code>${escapeHtml(item.tool)}</code></div><div>${escapeHtml(item.status)}</div><div>${escapeHtml(item.denied_reason || item.stage_state || '')}</div></div>`;
}
loadState().then(state => {
  document.getElementById('next-action').textContent = state.summary.recommended_next_action || 'no action';
  document.getElementById('panels').innerHTML = state.panels.map(renderPanel).join('');
  document.getElementById('action-queue').innerHTML = (state.action_queue || []).map(renderAction).join('') || '<p class="purpose">No machine acts queued.</p>';
  document.getElementById('trace').innerHTML = (state.trace || []).map(renderTrace).join('');
}).catch(err => {
  document.getElementById('panels').innerHTML = `<article class="panel"><h2>Missing snapshot</h2><p class="purpose">Run <code>PYTHONPATH=src python3 -m calendar_pilot.app frontend --write-snapshot</code>.</p><pre>${escapeHtml(String(err))}</pre></article>`;
});
