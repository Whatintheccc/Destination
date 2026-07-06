#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.environment.signal_estimators import InterruptionToleranceEstimator
from calendar_pilot.replay import ReplayBuffer
from calendar_pilot.types import Belief, RawCalendarObservation

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--observation', default='data/sample_calendar.json')
    ap.add_argument('--out', default='runs/p12_signal_estimator_report.json')
    ap.add_argument('--replay-out', default='')
    args=ap.parse_args()
    obs=RawCalendarObservation.from_dict(json.loads((ROOT/args.observation).read_text()))
    out=InterruptionToleranceEstimator().estimate(obs)
    signal=out.signal.to_dict(); signal['signal_schema_version']='semantic_signal.v1'
    report=out.report.to_dict(); report['report_schema_version']='signal_estimator_report.v1'
    signal_row_id=f"semantic_signal:{signal['signal_id']}"
    belief=Belief.from_semantic_signal(out.signal, activation_row_ids=[signal_row_id])
    payload={'ok':True,'signals':[signal],'beliefs':[belief.to_dict()],'report':report}
    dest=Path(args.out); dest=dest if dest.is_absolute() else ROOT/dest
    atomic_write_json(dest,payload)
    if args.replay_out:
        replay=ReplayBuffer()
        replay_signal_row_id=replay.append_semantic_signal(signal, trace_id=signal['signal_id'])
        belief_row_id=replay.append_belief(belief, trace_id=belief.belief_id, causal_parent_id=replay_signal_row_id)
        replay.append_signal_estimator_report(report, trace_id=report['report_id'], causal_parent_id=belief_row_id)
        r=Path(args.replay_out); r=r if r.is_absolute() else ROOT/r
        replay.save_jsonl(r)
    print(json.dumps({'ok':True,'out':str(dest),'estimator_version':report['estimator_version']},indent=2))
if __name__=='__main__': main()
