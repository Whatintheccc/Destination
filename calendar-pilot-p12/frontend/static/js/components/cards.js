import {h, kv} from '../h.js';

function actionField(label, testid, value) {
  return h('div', {class: 'kv'}, h('div', {class: 'k'}, label), h('div', {class: 'v', 'data-testid': testid}, value ?? '—'));
}

export function observationCard(card) {
  const facts = (card.facts || []).map(fact => h('div', {
    class: 'inspector-card observation-fact',
    'data-fact-id': fact.fact_id || '',
  },
    h('div', {class: 'card-header'},
      h('div', {}, h('h4', {}, fact.title || fact.fact_id || 'Calendar fact'), h('p', {}, `${fact.start || '—'} → ${fact.end || '—'}`)),
      h('span', {class: 'badge', 'data-citation-id': fact.citation_id || fact.fact_id || ''}, `Cited ${fact.citation_id || fact.fact_id || '—'}`)),
    kv('calendar', fact.calendar_id),
    kv('category', fact.category)));
  return h('div', {class: 'card observation-card', 'data-testid': 'observation-card'},
    h('div', {class: 'card-header'},
      h('div', {}, h('h4', {}, 'Calendar observation'), h('p', {}, `Bound timezone: ${card.timezone || '—'}`)),
      h('span', {class: 'badge'}, `${facts.length} cited facts`)),
    ...facts);
}

export function candidateCard(card) {
  const candidateId = card.candidate_id || '';
  const action = card.action || {};
  const timezoneCheck = card.timezone_check || {};
  const story = (card.model_story || []).slice(0, 3).map(line => h('li', {}, line));
  const rewards = Object.entries(card.reward_breakdown || {}).slice(0, 5).map(([k, v]) => h('span', {class: 'badge'}, `${k} ${v}`));
  return h('div', {class: 'card candidate-card', 'data-testid': 'candidate-card', dataset: {candidateId}},
    h('div', {class: 'card-header'},
      h('div', {}, h('h4', {}, card.title || card.intent || 'Candidate action'), h('p', {}, card.subtitle || card.explanation || '')),
      h('span', {class: 'badge'}, `Tier ${card.required_authority_tier ?? '—'}`)),
    h('div', {class: 'kv'},
      h('div', {class: 'k'}, 'Goal fit'),
      h('div', {'data-testid': 'candidate-addresses-goal', class: 'v'}, String(card.addresses_goal === true))),
    h('div', {class: 'kv'},
      h('div', {class: 'k'}, 'Compared with no change'),
      h('div', {'data-testid': 'candidate-compares-noop', class: 'v'}, card.rationale_compares_noop === true ? 'true' : 'false')),
    card.counterfactual ? h('p', {class: 'muted'}, card.counterfactual) : null,
    card.binding_constraint ? h('p', {class: 'muted', 'data-testid': 'noop-binding-constraint'}, card.binding_constraint) : null,
    h('div', {class: 'inspector-card candidate-action'},
      actionField('local date', 'candidate-local-date', action.local_date),
      actionField('timezone', 'candidate-timezone', action.timezone),
      actionField('start', 'candidate-start', action.start),
      actionField('end', 'candidate-end', action.end),
      actionField('duration minutes', 'candidate-duration-minutes', action.duration_minutes),
      actionField('calendar', 'candidate-calendar-id', action.calendar_id),
      actionField('title', 'candidate-title', action.title),
      actionField('attendees', 'candidate-attendees', JSON.stringify(action.attendees || [])),
      actionField('affected ids', 'candidate-affected-ids', JSON.stringify(action.affected_ids || [])),
      actionField('conflicts', 'candidate-conflicts', JSON.stringify(action.conflicts || [])),
      actionField('reversibility', 'candidate-reversibility', action.reversibility),
      actionField('authority need', 'candidate-authority-need', action.authority_need),
      h('span', {'data-testid': 'timezone-local-day-matches'}, String(timezoneCheck.local_day_matches === true)),
      h('span', {'data-testid': 'timezone-offset-roundtrip'}, String(timezoneCheck.offset_roundtrip === true)),
      h('span', {'data-testid': 'timezone-duration-preserved'}, String(timezoneCheck.duration_preserved === true)),
      h('span', {'data-testid': 'timezone-tomorrow-uses-bound-timezone'}, String(timezoneCheck.tomorrow_uses_bound_timezone === true)),
      h('span', {'data-testid': 'timezone-dst-case-resolved'}, String(timezoneCheck.dst_case_resolved === true))),
    story.length ? h('ol', {class: 'story'}, story) : null,
    h('div', {}, rewards),
    h('div', {class: 'card-actions'},
      card.intent !== 'do_nothing' ? h('button', {class: 'secondary simulate-btn', 'data-testid': 'simulate-candidate', dataset: {candidateId}}, 'Simulate') : null,
      card.intent !== 'do_nothing' ? h('button', {class: 'secondary stage-btn', 'data-testid': 'stage-candidate', dataset: {candidateId}}, 'Stage') : null,
      card.intent !== 'do_nothing' ? h('button', {class: 'primary commit-btn', 'data-testid': 'commit-candidate', dataset: {candidateId}}, 'Commit with Swift') : null,
      h('button', {class: 'secondary candidate-accepted', 'data-testid': 'candidate-accepted', dataset: {candidateId}}, 'Useful'),
      h('button', {class: 'secondary candidate-dismissed', 'data-testid': 'candidate-dismissed', dataset: {candidateId}}, 'Dismiss'),
      h('button', {class: 'secondary candidate-corrected', 'data-testid': 'candidate-corrected', dataset: {candidateId}}, 'Shorten by 10 min')));
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
    ['denied', 'failed'].includes(card.status) ? h('div', {class: 'inspector-card', 'data-testid': 'denial-evidence'},
      actionField('owner', 'denial-owner', 'Swift effect kernel'),
      actionField('reason', 'denial-reason', card.body || 'Swift denied the requested action.'),
      actionField('repair', 'denial-repair', 'Narrow the action or explicitly grant the required scope and tier.'),
      h('span', {'data-testid': 'denial-specific'}, String(Boolean(card.body && card.body !== 'denied'))))
      : null,
    card.simulation_preview ? h('div', {class: 'inspector-card', 'data-testid': 'simulation-preview'},
      actionField('simulated action', 'simulation-action', JSON.stringify(card.simulation_preview.action)),
      actionField('provider result', 'simulation-provider-result', JSON.stringify(card.simulation_preview.provider_result)),
      actionField('conflict result', 'simulation-conflict-result', JSON.stringify(card.simulation_preview.conflict_result)),
      actionField('uncertainty', 'simulation-uncertainty', JSON.stringify(card.simulation_preview.uncertainty)),
      card.simulation_preview.denial_or_hold_reason
        ? actionField('denial or hold', 'simulation-denial-or-hold-reason', card.simulation_preview.denial_or_hold_reason)
        : null)
      : null,
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
  const candidate = output.candidate || {};
  const candidateAction = (candidate.actions || [])[0];
  const isSimulation = output.simulation_only === true || receipt.tool_name === 'simulate_action_program' || swift.stage_state === 'simulated';
  const simulationPreview = isSimulation ? {
    action: candidateAction || {},
    provider_result: {
      provider_id: swift.provider_id || provider.provider_id || null,
      sync_status: output.would_sync_status || swift.sync_status || null,
      actuation_mode: output.would_actuation_mode || swift.actuation_mode || null,
      simulation_only: output.simulation_only === true,
    },
    conflict_result: {
      passed: swift.conflict_check_passed === true,
      rejected_action_types: swift.rejected_action_types || [],
    },
    uncertainty: {
      predicted_regret: candidate.predicted_regret,
      predicted_social_risk: candidate.predicted_social_risk,
      predicted_interruption_cost: candidate.predicted_interruption_cost,
      simulated_outcomes: candidate.simulated_outcomes || {},
    },
    denial_or_hold_reason: output.would_denied_reason || swift.denied_reason || null,
  } : null;
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
    simulation_preview: simulationPreview,
  };
}
