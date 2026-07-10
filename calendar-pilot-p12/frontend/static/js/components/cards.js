import {h, kv} from '../h.js';

export function candidateCard(card) {
  const candidateId = card.candidate_id || '';
  const story = (card.model_story || []).slice(0, 3).map(line => h('li', {}, line));
  const rewards = Object.entries(card.reward_breakdown || {}).slice(0, 5).map(([k, v]) => h('span', {class: 'badge'}, `${k} ${v}`));
  return h('div', {class: 'card candidate-card', 'data-testid': 'candidate-card', dataset: {candidateId}},
    h('div', {class: 'card-header'},
      h('div', {}, h('h4', {}, card.title || card.intent || 'Candidate action'), h('p', {}, card.subtitle || card.explanation || '')),
      h('span', {class: 'badge'}, `Tier ${card.required_authority_tier ?? '—'}`)),
    story.length ? h('ol', {class: 'story'}, story) : null,
    h('div', {}, rewards),
    h('div', {class: 'card-actions'},
      h('button', {class: 'secondary simulate-btn', 'data-testid': 'simulate-candidate', dataset: {candidateId}}, 'Simulate'),
      h('button', {class: 'secondary stage-btn', 'data-testid': 'stage-candidate', dataset: {candidateId}}, 'Stage'),
      h('button', {class: 'primary commit-btn', 'data-testid': 'commit-candidate', dataset: {candidateId}}, 'Commit with Swift'),
      h('button', {class: 'secondary candidate-accepted', 'data-testid': 'candidate-accepted', dataset: {candidateId}}, 'Useful'),
      h('button', {class: 'secondary candidate-dismissed', 'data-testid': 'candidate-dismissed', dataset: {candidateId}}, 'Dismiss'),
      h('button', {class: 'secondary candidate-corrected', 'data-testid': 'candidate-corrected', dataset: {candidateId}}, 'Needs correction')));
}

export function receiptCard(input) {
  const card = normalizeReceipt(input);
  const statusClass = ['denied', 'failed'].includes(card.status) ? 'danger' : (['committed', 'reverted'].includes(card.status) ? 'ok' : '');
  return h('div', {class: 'card receipt-card', 'data-testid': 'receipt-card', dataset: {envelopeId: card.envelope_id || ''}},
    h('div', {class: 'card-header'},
      h('div', {}, h('h4', {}, card.title || 'Receipt'), h('p', {}, card.body || '')),
      h('span', {class: `badge ${statusClass}`}, card.status || 'receipt')),
    kv('receipt', card.receipt_id || '—'),
    kv('grant', card.grant_id || '—'),
    kv('rollback', card.rollback_state || card.rollback_handle_id || '—'),
    h('div', {class: 'card-actions'},
      card.rollback_handle_id && card.status === 'committed' ? h('button', {class: 'secondary undo-btn', 'data-testid': 'undo-action', dataset: {rollback: card.rollback_handle_id}}, 'Undo') : null,
      card.receipt_id ? h('button', {class: 'secondary feedback-useful', 'data-testid': 'feedback-useful', dataset: {receiptId: card.receipt_id}}, 'Useful') : null,
      card.receipt_id ? h('button', {class: 'secondary feedback-wrong', dataset: {receiptId: card.receipt_id}}, 'Wrong') : null,
      card.envelope_id ? h('button', {class: 'secondary envelope-open', dataset: {envelopeId: card.envelope_id, traceId: card.trace_id || ''}}, 'Envelope') : null));
}

export function normalizeReceipt(receipt) {
  const output = receipt.output || {};
  const swift = output.swift_receipt || output.receipt || receipt.swift_receipt || {};
  const env = output.action_envelope || swift.action_envelope || receipt.action_envelope || {};
  const provider = env.provider || output.provider_receipt || {};
  const rollbackState = provider.rollback_state || (output.rollback_verified === true ? 'verified' : undefined);
  return {
    type: 'receipt',
    receipt_id: swift.receipt_id || receipt.swift_receipt_id || receipt.receipt_id || receipt.tool_call_id,
    title: receipt.denied_reason ? 'Swift denied the action' : (receipt.status === 'committed' ? 'Committed calendar change' : (receipt.status === 'reverted' ? 'Undo completed' : 'Swift receipt')),
    status: receipt.status || swift.stage_state || swift.sync_status,
    rollback_handle_id: swift.rollback_handle_id || provider.rollback_handle_id || receipt.rollback_handle_id,
    rollback_state: rollbackState,
    grant_id: receipt.authority_grant_id || swift.authority_grant_id || env.authority?.grant_id,
    body: receipt.denied_reason || swift.denied_reason || `Stage state: ${receipt.stage_state || swift.stage_state || 'no_op'}`,
    candidate_id: swift.candidate_id || receipt.candidate_id,
    envelope_id: env.envelope_id || receipt.envelope_id,
    trace_id: env.trace_id || receipt.correlation_id,
  };
}
