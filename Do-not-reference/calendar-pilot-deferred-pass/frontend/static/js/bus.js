export function connectEvents({store, sessionId = '', onFallbackPoll = null}) {
  if (!('EventSource' in window)) return false;
  const url = `/api/events?since=${encodeURIComponent(store.seq || 0)}${sessionId ? `&session_id=${encodeURIComponent(sessionId)}` : ''}`;
  const source = new EventSource(url);
  source.onmessage = event => {
    try { store.apply(JSON.parse(event.data)); } catch (_) { /* ignore malformed dev frames */ }
  };
  source.onerror = () => {
    source.close();
    if (onFallbackPoll) onFallbackPoll();
  };
  return true;
}
