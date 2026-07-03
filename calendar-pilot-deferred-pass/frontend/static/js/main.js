import {api, loadView, normalizeView} from './api.js';
import {connectEvents} from './bus.js';
import {candidateCard, receiptCard} from './components/cards.js';
import {openEnvelopeOverlay} from './components/envelope.js';
import {h, clear, kv} from './h.js';
import {createStore} from './store.js';

const store = createStore();
let activeSurface = 'operate';
let pending = false;
let polling = false;
const $ = (sel) => document.querySelector(sel);

function sessionId() { return store.view?.session?.session_id || store.view?.legacy_state?.session?.session_id || ''; }
async function refresh() { store.checkpoint(await loadView(sessionId())); }
function setPending(value) { pending = value; document.querySelectorAll('button, textarea, input').forEach(el => { if (!['inspector-toggle','close-inspector'].includes(el.id)) el.disabled = value; }); }
function showToast(text) { const toast = h('div', {class: 'toast'}, text); document.body.append(toast); setTimeout(() => toast.remove(), 2400); }

function render() {
  const view = store.view || {};
  renderSidebar(view);
  renderHeader(view);
  renderSurface(view);
  renderRail(view);
}

function renderSidebar(view) {
  const list = $('#session-list');
  const sessions = view.legacy_state?.sidebar?.sessions || [{label: view.session?.label || 'Current fixture run', active: true, session_id: view.session?.session_id}];
  clear(list).append(...sessions.map(s => h('div', {class: `nav-item ${s.active ? 'active' : ''}`}, s.label || s.session_id || 'Session')));
  const runs = view.legacy_state?.sidebar?.recent_runs || [{label: 'No dogfood runs yet'}];
  clear($('#recent-runs')).append(...runs.map(r => h('div', {class: 'nav-item'}, r.label || r.plan_id || 'Run')));
}

function renderHeader(view) {
  const runtime = view.runtime || {};
  const chip = $('#runtime-chip');
  chip.textContent = runtime.mode_label || runtime.label || runtime.runtime_mode || runtime.mode || 'Fixture mode';
  chip.classList.toggle('danger', Boolean(runtime.live_blockers?.length));
  const authority = view.legacy_state?.session || view.session || {};
  const scopes = (authority.authority_scopes || []).join(', ') || 'no scopes';
  $('#authority-chip').textContent = `Tier ${authority.authority_tier ?? '—'}: ${scopes}`;
  const version = $('#state-version');
  if (version) version.textContent = `v${view.state_version ?? 0}`;
}

function renderSurface(view) {
  document.querySelectorAll('[data-surface]').forEach(btn => btn.classList.toggle('active', btn.dataset.surface === activeSurface));
  const main = $('#primary-surface') || $('#chat-transcript');
  clear(main);
  if (activeSurface === 'observe') return renderObserve(main, view);
  if (activeSurface === 'learn') return renderLearn(main, view);
  if (activeSurface === 'lab') return renderLab(main, view);
  if (activeSurface === 'authority') return renderAuthoritySurface(main, view);
  renderOperate(main, view);
}

function renderOperate(root, view) {
  const messages = view.conversation?.messages || view.legacy_state?.chat?.messages || [];
  root.append(h('section', {class: 'pipeline-strip'}, ...(view.pipeline?.turns || []).slice(-1).flatMap(turn => (turn.stages || []).map(stage => h('span', {class: `stage-pill ${stage.status || ''}`}, stage.stage || stage.tool || stage.object)))));
  messages.forEach(message => root.append(messageNode(message)));
  const hasCandidate = root.querySelector('[data-testid="candidate-card"]');
  if (!hasCandidate) (view.frontier?.candidates || []).slice(0, 4).forEach(card => root.append(candidateCard(card)));
  const hasReceipt = root.querySelector('[data-testid="receipt-card"]');
  if (!hasReceipt) (view.conversation?.receipt_cards || view.legacy_state?.chat?.receipt_cards || []).forEach(card => root.append(receiptCard(card)));
}

function messageNode(message) {
  const cards = [];
  for (const card of (message.cards || [])) {
    if (card.type === 'candidate') cards.push(candidateCard(card));
    else if (card.type === 'receipt') cards.push(receiptCard(card.receipt || card));
  }
  return h('article', {class: `message ${message.role === 'user' ? 'user' : 'assistant'}`, 'data-testid': `message-${message.role === 'user' ? 'user' : 'assistant'}`},
    h('div', {class: 'avatar'}),
    h('div', {class: 'bubble'}, message.title ? h('h3', {}, message.title) : null, message.body ? h('p', {}, message.body) : null, h('div', {class: 'cards'}, cards)));
}

function renderObserve(root, view) {
  root.append(h('h2', {}, 'Observe'));
  for (const turn of view.pipeline?.turns || []) {
    root.append(h('div', {class: 'inspector-card'}, h('h3', {}, turn.goal || turn.trace_id || 'Trace'), ...(turn.stages || []).map(stage => kv(stage.stage || stage.tool || stage.object, `${stage.status || 'succeeded'} ${stage.ms ? `${stage.ms}ms` : ''}`))));
  }
  if (store.traceLog.length) root.append(h('div', {class: 'inspector-card'}, h('h3', {}, 'Live events'), h('pre', {}, JSON.stringify(store.traceLog.slice(-30), null, 2))));
}

function renderLearn(root, view) {
  const learning = view.learning || {};
  root.append(h('h2', {}, 'Learn'));
  root.append(h('div', {class: 'inspector-card'}, h('h3', {}, 'Frontier quality'), kv('valid candidates', (view.frontier?.candidates || []).length), kv('rejections', view.frontier?.rejections?.count || 0), kv('taxonomy', learning.taxonomy_health || {})));
  root.append(h('div', {class: 'inspector-card'}, h('h3', {}, 'Tuning provenance'), h('pre', {}, JSON.stringify(learning.tuning || learning.policy_tuning || {}, null, 2))));
  root.append(h('div', {class: 'inspector-card'}, h('h3', {}, 'Frontier diff'), h('pre', {}, JSON.stringify(learning.frontier_diff || {}, null, 2))));
  (view.frontier?.candidates || []).forEach(card => root.append(candidateCard(card)));
}

function renderLab(root, view) {
  const lab = view.lab || {};
  root.append(h('h2', {}, 'Lab'));
  root.append(h('div', {class: 'inspector-card'}, h('h3', {}, 'Self-play backend'), kv('backend', lab.backend || 'stub_fast'), kv('grant policy', lab.backend_policy || {}), h('label', {}, 'Episodes ', h('input', {id: 'self-play-episodes', type: 'number', min: 1, max: 20, value: 3})), h('div', {class: 'card-actions'}, h('button', {id: 'run-self-play', 'data-testid': 'run-self-play', class: 'primary'}, 'Run self-play'))));
  root.append(h('pre', {}, JSON.stringify(lab, null, 2)));
}

function renderAuthoritySurface(root, view) {
  root.append(h('h2', {}, 'Authority'));
  root.append(h('div', {class: 'inspector-card'}, h('h3', {}, 'Authority scopes'), h('label', {}, 'Tier ', h('input', {id: 'authority-tier', type: 'number', min: 0, max: 6, value: view.legacy_state?.session?.authority_tier ?? 3})), h('label', {}, 'Scopes ', h('input', {id: 'authority-scopes', value: (view.legacy_state?.session?.authority_scopes || []).join(', ')})), h('div', {class: 'card-actions'}, h('button', {id: 'save-authority', class: 'primary'}, 'Save authority'))));
  root.append(h('pre', {}, JSON.stringify(view.authority || {}, null, 2)));
}

function renderRail(view) {
  const content = $('#inspector-content');
  if (!content) return;
  clear(content);
  content.append(h('div', {class: 'inspector-card'}, h('h3', {}, 'Glass Cockpit'), kv('surface', activeSurface), kv('state_version', view.state_version || 0), kv('invariant violations', view.invariants?.violations?.length || 0)));
  content.append(h('div', {class: 'inspector-card'}, h('h3', {}, 'Runtime report'), h('pre', {}, JSON.stringify(view.runtime || {}, null, 2))));
  content.append(h('div', {class: 'inspector-card'}, h('h3', {}, 'Replay'), h('button', {id: 'replay-export', 'data-testid': 'replay-export', class: 'primary'}, 'Export JSON')));
}

async function postAndRefresh(path, body = {}) {
  setPending(true);
  try {
    store.checkpoint(normalizeView(await api(path, {method: 'POST', body}, sessionId())));
  } catch (err) {
    showToast(err.message);
  } finally {
    setPending(false);
  }
}
async function sendGoal(goal) { return postAndRefresh('/api/plans', {goal, commit: false}); }

async function openEnvelope(traceId, envelopeId) {
  if (traceId) {
    try { return openEnvelopeOverlay(await api(`/api/trace/${encodeURIComponent(traceId)}`, {}, sessionId())); } catch (_) { /* fall through */ }
  }
  openEnvelopeOverlay({envelope_id: envelopeId, note: 'Envelope is not yet available in this trace.'});
}

document.addEventListener('submit', event => { if (event.target.id === 'composer') { event.preventDefault(); const input = $('#goal-input'); const goal = input.value.trim(); if (goal) { input.value = ''; sendGoal(goal); } } });
document.addEventListener('click', event => {
  const target = event.target.closest('button'); if (!target) return;
  if (target.dataset.surface) { activeSurface = target.dataset.surface; return render(); }
  if (target.id === 'inspector-toggle') return $('#inspector').classList.toggle('closed');
  if (target.id === 'close-inspector') return $('#inspector').classList.add('closed');
  if (target.classList.contains('tab')) { activeSurface = target.dataset.tab === 'self_play' ? 'lab' : (target.dataset.tab || 'operate'); return render(); }
  if (target.id === 'new-chat') return postAndRefresh('/api/sessions');
  const candidateId = target.dataset.candidateId;
  if (target.classList.contains('simulate-btn')) return postAndRefresh(`/api/candidates/${candidateId}/simulate`);
  if (target.classList.contains('stage-btn')) return postAndRefresh(`/api/candidates/${candidateId}/stage`);
  if (target.classList.contains('commit-btn')) return postAndRefresh(`/api/candidates/${candidateId}/commit`, {confirmed: true});
  if (target.classList.contains('undo-btn')) return postAndRefresh('/api/undo', {rollback_handle_id: target.dataset.rollback});
  if (target.classList.contains('feedback-useful')) return postAndRefresh('/api/feedback', {receipt_id: target.dataset.receiptId, feedback: 'useful'});
  if (target.classList.contains('feedback-wrong')) return postAndRefresh('/api/feedback', {receipt_id: target.dataset.receiptId, feedback: 'wrong'});
  if (target.classList.contains('runtime-mode-btn')) return postAndRefresh('/api/runtime', {runtime_mode: target.dataset.mode});
  if (target.id === 'save-authority') return postAndRefresh('/api/authority', {max_authority_tier: Number($('#authority-tier').value || 3), scopes: $('#authority-scopes').value.split(',').map(s => s.trim()).filter(Boolean), confirmed: true});
  if (target.id === 'run-self-play') return postAndRefresh('/api/self-play', {episodes: Number($('#self-play-episodes')?.value || 3)});
  if (target.id === 'replay-export' || target.id === 'replay-export-sidebar') return api('/api/replay/export', {}, sessionId()).then(openEnvelopeOverlay).catch(err => showToast(err.message));
  if (target.classList.contains('envelope-open')) return openEnvelope(target.dataset.traceId, target.dataset.envelopeId);
});

store.subscribe(render);
store.onResync(refresh);
refresh().then(() => {
  const ok = connectEvents({store, sessionId: sessionId(), onFallbackPoll: () => { if (!polling) { polling = true; setInterval(refresh, 3000); } }});
  if (!ok) setInterval(refresh, 3000);
});
