export function createStore() {
  let view = null;
  let seq = 0;
  const traceLog = [];
  const subscribers = new Set();
  let resync = null;
  const notify = () => subscribers.forEach(fn => fn(view));
  return {
    get view() { return view; },
    get seq() { return seq; },
    get traceLog() { return traceLog; },
    subscribe(fn) { subscribers.add(fn); return () => subscribers.delete(fn); },
    onResync(fn) { resync = fn; },
    checkpoint(nextView) { view = nextView; seq = Math.max(seq, nextView?.state_version || 0); notify(); },
    apply(event) {
      if (!event) return;
      if (event.seq && seq && event.seq > seq + 1 && resync) resync();
      if (event.seq) seq = Math.max(seq, event.seq);
      if (event.kind === 'patch' && view) view[event.region] = event.value;
      else traceLog.push(event);
      if (event.state_version && view) view.state_version = Math.max(view.state_version || 0, event.state_version);
      notify();
    },
  };
}