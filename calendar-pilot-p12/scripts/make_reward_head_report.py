#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.environment.signal_streams import infer_signal_stream
HEADS=['utility','acceptance','engagement','long_horizon','regret','interruption','social_risk','undo_regret','ignored','explicit_wrong']
REWARD_FIELDS={
    'utility':'utility_reward',
    'acceptance':'acceptance_reward',
    'engagement':'engagement_reward',
    'regret':'regret_penalty',
    'interruption':'interruption_penalty',
    'social_risk':'social_risk_penalty',
}
BOOLEAN_HEADS={
    'undo_regret':'undone',
    'ignored':'ignored',
    'explicit_wrong':'explicit_wrong',
}


def _resolve(path: str | Path) -> Path:
    p=Path(path)
    return p if p.is_absolute() else ROOT/p


def _iter_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows=[]
    source_sha256=hashlib.sha256(path.read_bytes()).hexdigest()
    for line_no,line in enumerate(path.read_text(encoding='utf-8').splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row=json.loads(line)
        except json.JSONDecodeError as exc:
            rows.append({'record_id':f'{path.name}:line:{line_no}','record_type':'malformed_json','signal_stream':'system','payload':{'parse_error':str(exc)},'_p13_source':{'path':str(path),'sha256':source_sha256,'line_no':line_no}})
            continue
        row['_p13_source']={'path':str(path),'sha256':source_sha256,'line_no':line_no}
        rows.append(row)
    return rows


def _reward_payload(row: dict[str, Any]) -> dict[str, Any] | None:
    payload=row.get('payload') if isinstance(row.get('payload'), dict) else {}
    reward=payload.get('reward')
    if isinstance(reward, dict):
        return reward
    if row.get('record_type')=='reward':
        direct={key: payload.get(key) for key in {
            'utility_reward','acceptance_reward','engagement_reward','regret_penalty',
            'interruption_penalty','social_risk_penalty','total_reward','undone',
            'ignored','explicit_wrong','provenance'
        } if key in payload}
        return direct or None
    return None


def _mean(values: list[float]) -> float:
    return round(sum(values)/len(values), 4) if values else 0.0


def _summarize_source(path: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        'path':str(path),
        'total_rows':len(rows),
        'present':path.exists(),
        'sha256':hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None,
    }


def build_report(*, replay_path: Path | None = None, replay_paths: list[Path] | None = None, require_source_shape: bool = False) -> dict[str, Any]:
    paths=replay_paths or ([replay_path] if replay_path is not None else [])
    rows=[]
    source_summaries=[]
    for path in paths:
        source_rows=_iter_rows(path)
        source_summaries.append(_summarize_source(path, source_rows))
        rows.extend(source_rows)
    deltas={h+'_delta':0.0 for h in HEADS}
    values={h:[] for h in HEADS}
    consumed_action_ids=[]
    reward_purity_violations=[]
    reward_rows_seen=0
    non_action_reward_rows=0
    action_rows_seen=0
    non_action_stream_rows=0
    malformed_rows=[]
    consumed_reward_rows=[]
    invalid_source_shape_rows=[]
    human_row_ids=[]
    simulator_row_ids=[]
    simulator_positive_credit_violations=[]
    for row in rows:
        payload=row.get('payload') if isinstance(row.get('payload'), dict) else {}
        record_type=str(row.get('record_type') or '')
        stream=str(row.get('signal_stream') or infer_signal_stream(record_type, payload))
        row_id=str(row.get('record_id') or payload.get('record_id') or f'{record_type}:{len(consumed_action_ids)+len(reward_purity_violations)}')
        if record_type=='malformed_json':
            malformed_rows.append(row_id)
        if stream=='action':
            action_rows_seen += 1
        else:
            non_action_stream_rows += 1
        reward=_reward_payload(row)
        if reward is None:
            continue
        reward_rows_seen += 1
        if stream!='action':
            non_action_reward_rows += 1
            reward_purity_violations.append({
                'record_id':row_id,
                'record_type':record_type,
                'signal_stream':stream,
                'reason':'reward payload is not ActionStream evidence',
            })
            continue
        consumed_action_ids.append(row_id)
        source=row.get('_p13_source') if isinstance(row.get('_p13_source'),dict) else {}
        occurrence_id='rewardoccurrence:'+hashlib.sha256(json.dumps({
            'source_sha256':source.get('sha256'),
            'line_no':source.get('line_no'),
            'record_id':row_id,
        },sort_keys=True,separators=(',',':')).encode()).hexdigest()
        provenance=str(reward.get('provenance') or 'unknown')
        trace_id=str(row.get('trace_id') or payload.get('trace_id') or '')
        causal_parent_id=str(row.get('causal_parent_id') or '')
        reward_event_id=str(reward.get('reward_event_id') or '')
        if provenance=='human_ui':
            source_class='human'
            source_shape_valid=bool(reward_event_id and trace_id and causal_parent_id.startswith('feedback:'))
        elif provenance in {'self_play_simulator','simulator'}:
            source_class='simulator'
            source_shape_valid=bool(reward_event_id and trace_id.startswith('self_play:') and causal_parent_id)
        else:
            source_class='unknown'
            source_shape_valid=False
        identity={
            'occurrence_id':occurrence_id,
            'record_id':row_id,
            'source_artifact_sha256':source.get('sha256'),
            'source_line_no':source.get('line_no'),
            'reward_event_id':reward_event_id or None,
            'trace_id':trace_id or None,
            'causal_parent_id':causal_parent_id or None,
            'provenance':provenance,
            'source_class':source_class,
            'source_shape_valid':source_shape_valid,
            'classification_basis':'declared_human_feedback_reference_shape' if source_shape_valid and source_class=='human' else 'declared_self_play_reference_shape' if source_shape_valid else None,
            'declared_human_shape_valid':source_class=='human' and source_shape_valid,
        }
        consumed_reward_rows.append(identity)
        if not source_shape_valid:
            invalid_source_shape_rows.append(occurrence_id)
        elif source_class=='human':
            human_row_ids.append(occurrence_id)
        elif source_class=='simulator':
            simulator_row_ids.append(occurrence_id)
        if require_source_shape and source_class=='simulator':
            try:
                total_reward=float(reward.get('total_reward', 0.0) or 0.0)
            except (TypeError, ValueError):
                total_reward=0.0
            if total_reward > 0.0:
                simulator_positive_credit_violations.append({'occurrence_id':occurrence_id,'head':'total_reward','attempted_credit':total_reward})
        for head, field in REWARD_FIELDS.items():
            try:
                value=float(reward.get(field, 0.0) or 0.0)
                if require_source_shape and source_class=='simulator' and head in {'utility','acceptance','engagement'}:
                    if value > 0.0:
                        simulator_positive_credit_violations.append({'occurrence_id':occurrence_id,'head':head,'attempted_credit':value})
                    value=0.0
                values[head].append(value)
            except (TypeError, ValueError):
                values[head].append(0.0)
        for head, field in BOOLEAN_HEADS.items():
            values[head].append(1.0 if reward.get(field) is True else 0.0)
        values['long_horizon'].append(0.0)

    for head in HEADS:
        deltas[f'{head}_delta']=_mean(values[head])

    gates={
        'utility_delta':deltas['utility_delta'] >= 0.0,
        'regret_delta':deltas['regret_delta'] <= 0.0,
        'interruption_delta':deltas['interruption_delta'] <= 0.0,
        'social_risk_delta':deltas['social_risk_delta'] <= 0.0,
        'undo_regret_delta':deltas['undo_regret_delta'] <= 0.0,
        'explicit_wrong_delta':deltas['explicit_wrong_delta'] <= 0.0,
        'engagement_not_only_positive':not (
            deltas['engagement_delta'] > 0.0 and
            all(deltas[f'{head}_delta'] <= 0.0 for head in HEADS if head!='engagement')
        ),
        'reward_purity':not reward_purity_violations,
        'occurrence_identity_unique':len({row['occurrence_id'] for row in consumed_reward_rows})==len(consumed_reward_rows),
        'declared_source_shape':not require_source_shape or not invalid_source_shape_rows,
        'direct_simulator_credit_screen':not simulator_positive_credit_violations,
    }
    hold_reasons=[]
    if not consumed_action_ids:
        hold_reasons.append({
            'reason':'no ActionStream reward rows consumed',
            'owner':'Program A evidence collection',
            'next_unblock_action':'collect or supply replay rows with ActionStream reward payloads',
        })
    if malformed_rows:
        hold_reasons.append({
            'reason':'malformed replay rows were skipped',
            'row_ids':malformed_rows,
            'owner':'instrument owner',
            'next_unblock_action':'repair replay JSONL before using reward heads for promotion',
        })
    if require_source_shape and invalid_source_shape_rows:
        hold_reasons.append({
            'reason':'one or more reward rows lack the declared human/simulator causal-reference shape',
            'occurrence_ids':invalid_source_shape_rows,
            'owner':'reward ingress owner',
            'next_unblock_action':'supply explicit causal references; a later ingress contract must authenticate and resolve them',
        })
    if reward_purity_violations:
        decision='fail'
    elif hold_reasons:
        decision='hold'
    elif all(gates.values()):
        decision='pass'
    else:
        decision='hold'
        hold_reasons.append({
            'reason':'one or more reward-head gates did not pass',
            'owner':'ML/reward owner',
            'next_unblock_action':'inspect reward_head_deltas and replay evidence rows',
        })
    return {
        'reward_head_report_schema_version':'reward_head_report.v3' if require_source_shape else 'reward_head_report.v1',
        'reward_head_deltas':deltas,
        'reward_evidence':{
            'source_replay':str(paths[0]) if paths else '',
            'source_replays':[str(p) for p in paths],
            'source_summaries':source_summaries,
            'allowed_signal_streams':['action'],
            'source':'ActionStream reward and feedback rows',
            'total_replay_rows':len(rows),
            'action_rows_seen':action_rows_seen,
            'non_action_stream_rows':non_action_stream_rows,
            'reward_rows_seen':reward_rows_seen,
            'consumed_action_rows':len(consumed_action_ids),
            'consumed_action_row_ids':consumed_action_ids,
            'non_action_stream_reward_rows':non_action_reward_rows,
            'reward_purity_violations':reward_purity_violations,
            'occurrence_identity_scheme':'sha256(source_artifact_sha256,line_no,record_id)',
            'consumed_reward_rows':consumed_reward_rows,
            'occurrence_ids_unique':len({row['occurrence_id'] for row in consumed_reward_rows})==len(consumed_reward_rows),
            'declared_source_classification':{
                'human_occurrence_ids':human_row_ids,
                'simulator_occurrence_ids':simulator_row_ids,
                'invalid_source_shape_occurrence_ids':invalid_source_shape_rows,
                'direct_simulator_positive_credit':'screened',
                'simulator_positive_credit_violations':simulator_positive_credit_violations,
            },
            'source_shape_required':require_source_shape,
        },
        'gates':gates,
        'hold_reasons':hold_reasons,
        'decision':decision,
    }


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--replay',action='append',default=None); ap.add_argument('--require-source-shape',action='store_true'); ap.add_argument('--out',default='runs/p12_reward_head_report.json'); args=ap.parse_args()
    replay_args=args.replay or ['tests/fixtures/replay_golden.jsonl']
    payload=build_report(replay_paths=[_resolve(p) for p in replay_args],require_source_shape=args.require_source_shape)
    out=Path(args.out); out=out if out.is_absolute() else ROOT/out; atomic_write_json(out,payload); print(json.dumps({'ok':payload['decision']=='pass','decision':payload['decision'],'out':str(out)},indent=2))
    raise SystemExit(1 if payload['decision']=='fail' or (args.require_source_shape and payload['decision']!='pass') else 0)
if __name__=='__main__': main()
