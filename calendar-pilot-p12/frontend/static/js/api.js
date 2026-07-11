export async function api(path, options = {}, sessionId = '') {
  let requestPath = path;
  let body = options.body;
  if (sessionId && path.startsWith('/api/') && !path.startsWith('/api/sessions')) {
    if (body && typeof body !== 'string') body = {...body, session_id: body.session_id || sessionId};
    else if (!body) requestPath = `${path}${path.includes('?') ? '&' : '?'}session_id=${encodeURIComponent(sessionId)}`;
  }
  const response = await fetch(requestPath, {
    cache: 'no-store',
    headers: {'Content-Type': 'application/json', ...(options.headers || {})},
    ...options,
    body: body && typeof body !== 'string' ? JSON.stringify(body) : body,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `${response.status} ${response.statusText}`);
  return payload;
}

export async function loadView(sessionId = '') {
  try { return normalizeView(await api('/api/view', {}, sessionId)); }
  catch (err) {
    try { return normalizeView(await api('/api/state', {}, sessionId)); }
    catch (_) {
      return normalizeView({
        state_version: 0,
        session: {label: 'Local static preview', authority_tier: 3, authority_scopes: []},
        chat: {messages: []},
        sidebar: {sessions: [{label: 'Static preview', active: true}], recent_runs: []},
      });
    }
  }
}

export function normalizeView(payload) {
  if (payload?.view_version === 'view_state.v2') return payload;
  const state = payload || {};
  return {
    view_version: 'view_state.v2/legacy-adapter',
    state_version: state.state_version || 0,
    session: state.session || {},
    sidebar: state.sidebar || {
      sessions: [{label: state.session?.label || 'Current fixture run', active: true, session_id: state.session?.session_id}],
      recent_runs: [{label: 'No dogfood runs yet'}],
    },
    runtime: state.runtime || state.chat?.runtime || {},
    conversation: state.chat || {messages: []},
    frontier: {candidates: state.chat?.candidate_cards || [], rejections: state.learning?.frontier_rejections || {count: 0, reasons: {}}},
    actions: {queue: state.action_queue || []},
    authority: state.inspector?.authority || {},
    learning: state.learning || {},
    lab: state.inspector?.self_play || {},
    pipeline: state.pipeline || {turns: state.trace ? [{trace_id: state.summary?.plan_id || 'sample', stages: state.trace}] : []},
    invariants: state.invariants || {violations: []},
    correction: state.correction || null,
  };
}
