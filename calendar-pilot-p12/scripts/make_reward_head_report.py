#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
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
    for line_no,line in enumerate(path.read_text(encoding='utf-8').splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row=json.loads(line)
        except json.JSONDecodeError as exc:
            rows.append({'record_id':f'{path.name}:line:{line_no}','record_type':'malformed_json','signal_stream':'system','payload':{'parse_error':str(exc)}})
            continue
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
    }


def build_report(*, replay_path: Path | None = None, replay_paths: list[Path] | None = None) -> dict[str, Any]:
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
        for head, field in REWARD_FIELDS.items():
            try:
                values[head].append(float(reward.get(field, 0.0) or 0.0))
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
        'reward_head_report_schema_version':'reward_head_report.v1',
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
        },
        'gates':gates,
        'hold_reasons':hold_reasons,
        'decision':decision,
    }


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--replay',action='append',default=None); ap.add_argument('--out',default='runs/p12_reward_head_report.json'); args=ap.parse_args()
    replay_args=args.replay or ['tests/fixtures/replay_golden.jsonl']
    payload=build_report(replay_paths=[_resolve(p) for p in replay_args])
    out=Path(args.out); out=out if out.is_absolute() else ROOT/out; atomic_write_json(out,payload); print(json.dumps({'ok':payload['decision']=='pass','decision':payload['decision'],'out':str(out)},indent=2))
    raise SystemExit(1 if payload['decision']=='fail' else 0)
if __name__=='__main__': main()
