#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from calendar_pilot.environment.fsio import atomic_write_json

def load(path):
    p=Path(path); p=p if p.is_absolute() else ROOT/p
    return json.loads(p.read_text()) if p.exists() else {}
def git_sha():
    try: return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,stderr=subprocess.DEVNULL,text=True).strip()
    except Exception: return 'unknown'
def num(obj,*keys,default=0):
    cur=obj
    for k in keys:
        if not isinstance(cur,dict): return default
        cur=cur.get(k)
    return default if cur is None else cur
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--scorecard',default='runs/ml_scorecard.json'); ap.add_argument('--frontier-diff',default='runs/frontier_diff.json'); ap.add_argument('--out',default='runs/p12_measurement_report.json'); args=ap.parse_args()
    score=load(args.scorecard); diff=load(args.frontier_diff)
    frontier=score.get('frontier',{}) if isinstance(score.get('frontier'),dict) else {}
    metrics=score.get('metrics',{}) if isinstance(score.get('metrics'),dict) else {}
    payload={
      'measurement_schema_version':'measurement_report.v1','run_id':score.get('run_id') or 'p12_measurement','git_sha':git_sha(),
      'runtime_mode':metrics.get('runtime_mode','fixture'),'policy_backend':metrics.get('policy_backend','heuristic'), 'provider_backend':metrics.get('provider_backend','deterministic'), 'policy_tuning_id':metrics.get('policy_tuning_id','CURRENT'),
      'frontier_latency_ms_p50':metrics.get('frontier_latency_ms_p50'),'frontier_latency_ms_p95':metrics.get('frontier_latency_ms_p95'), 'codex_latency_ms_p50':metrics.get('codex_latency_ms_p50'), 'codex_latency_ms_p95':metrics.get('codex_latency_ms_p95'), 'provider_verify_latency_ms_p50':metrics.get('provider_verify_latency_ms_p50'), 'provider_verify_latency_ms_p95':metrics.get('provider_verify_latency_ms_p95'),
      'nim_request_count':int(metrics.get('nim_request_count',0) or 0),'nim_retry_count':int(metrics.get('nim_retry_count',0) or 0),'cost_per_valid_frontier':metrics.get('cost_per_valid_frontier'),
      'valid_frontier_rate':float(frontier.get('valid_frontier_rate', diff.get('valid_frontier_rate', 1.0 if frontier.get('valid_candidates',0) else 0.0)) or 0.0),'empty_frontier_rate':float(frontier.get('empty_frontier_rate',0.0) or 0.0), 'model_generation_rejection_rate':float(frontier.get('model_generation_rejection_rate',0.0) or 0.0),'OTHER_intent_rate':float(frontier.get('OTHER_intent_rate', frontier.get('other_intent_rate',0.0)) or 0.0),'expected_intent_hit_rate':float(frontier.get('expected_intent_hit_rate',0.0) or 0.0),
      'utility_delta':float(metrics.get('utility_delta',0.0) or 0.0),'engagement_delta':float(metrics.get('engagement_delta',0.0) or 0.0),'regret_delta':float(metrics.get('regret_delta',0.0) or 0.0),'interruption_delta':float(metrics.get('interruption_delta',0.0) or 0.0),'social_risk_delta':float(metrics.get('social_risk_delta',0.0) or 0.0),'undo_regret_delta':float(metrics.get('undo_regret_delta',0.0) or 0.0),
      'rollback_pass_rate':float(metrics.get('rollback_pass_rate',0.0) or 0.0),'provider_idempotency_pass':bool(metrics.get('provider_idempotency_pass', True)), 'hard_invariant_violations':int(metrics.get('hard_invariant_violations', len(score.get('invariants',{}).get('violations',[])) if isinstance(score.get('invariants'),dict) else 0) or 0),'soft_invariant_violations':int(metrics.get('soft_invariant_violations',0) or 0),
      'label_evidence_coverage':metrics.get('label_evidence_coverage'),'label_churn_rate':metrics.get('label_churn_rate'),'estimator_calibration_gap':metrics.get('estimator_calibration_gap'),'derived_vs_declared_conflicts':metrics.get('derived_vs_declared_conflicts')}
    out=Path(args.out); out=out if out.is_absolute() else ROOT/out; atomic_write_json(out,payload); print(json.dumps({'ok':True,'out':str(out)},indent=2))
if __name__=='__main__': main()
