#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'src'))
from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.replay import sha256_file
from scripts.make_scorecard import build_scorecard
from scripts.run_frontier_diff import build_diff as build_frontier_diff
ABLATIONS=['no_intent_reward_bias','no_failure_penalties','no_denied_intents','no_right_moment_tuning','no_taxonomy_normalization','no_provider_penalties','no_semantic_labels','no_derived_signals']


def _resolve(path: str | Path) -> Path:
 p=Path(path)
 return p if p.is_absolute() else ROOT/p


def _load_json(path: Path) -> tuple[dict[str, Any], str | None]:
 if not path.exists():
  return {}, f'missing artifact: {path}'
 try:
  payload=json.loads(path.read_text(encoding='utf-8'))
 except json.JSONDecodeError as exc:
  return {}, f'malformed JSON in {path}: {exc}'
 if not isinstance(payload, dict) or not payload:
  return {}, f'empty or non-object artifact: {path}'
 return payload, None


def _load_optional_json(path: Path | None) -> dict[str, Any]:
 if path is None or not path.exists():
  return {}
 try:
  payload=json.loads(path.read_text(encoding='utf-8'))
 except json.JSONDecodeError:
  return {}
 return payload if isinstance(payload, dict) else {}


def _violation_count(scorecard: dict[str, Any]) -> int:
 invariants=scorecard.get('invariants') if isinstance(scorecard.get('invariants'), dict) else {}
 raw=invariants.get('violations', 0)
 if isinstance(raw, list):
  return len(raw)
 try:
  return int(raw or 0)
 except (TypeError, ValueError):
  return 0


def _artifact_ref(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
 return {
  'path':str(path),
  'sha256':sha256_file(path) if path.exists() else None,
  'present':bool(payload),
 }


def _summarize_frontier(diff: dict[str, Any]) -> dict[str, Any]:
 return {
  'avg_marginal_reward_delta':diff.get('avg_marginal_reward_delta'),
  'avg_reward_delta':diff.get('avg_reward_delta'),
  'baseline_leader':diff.get('baseline_leader'),
  'tuned_leader':diff.get('tuned_leader'),
  'marginal_leader_changed':diff.get('marginal_leader_changed'),
  'tuned_frontier_count':len(diff.get('tuned_frontier', []) if isinstance(diff.get('tuned_frontier'), list) else []),
  'per_candidate_marginal_delta_count':len(diff.get('per_candidate_marginal_delta', {}) if isinstance(diff.get('per_candidate_marginal_delta'), dict) else {}),
 }


def _summarize_scorecard(scorecard: dict[str, Any]) -> dict[str, Any]:
 return {
  'decision':scorecard.get('decision'),
  'invariant_violations':_violation_count(scorecard),
  'frontier_valid_candidates':((scorecard.get('frontier') or {}).get('valid_candidates') if isinstance(scorecard.get('frontier'), dict) else None),
  'training_rows':((scorecard.get('learning') or {}).get('training_rows') if isinstance(scorecard.get('learning'), dict) else None),
 }


def _decision_for_inputs(diff: dict[str, Any], scorecard: dict[str, Any], reward_heads: dict[str, Any], errors: list[str]) -> str:
 if errors:
  return 'hold'
 if not diff.get('tuned_frontier') or not isinstance(diff.get('per_candidate_marginal_delta'), dict):
  return 'hold'
 if _violation_count(scorecard) != 0:
  return 'hold'
 reward_decision=reward_heads.get('decision', 'hold') if reward_heads else 'hold'
 if reward_decision != 'pass':
  return 'hold'
 try:
  marginal=float(diff.get('avg_marginal_reward_delta', diff.get('avg_reward_delta', 0.0)) or 0.0)
 except (TypeError, ValueError):
  return 'hold'
 return 'pass' if marginal >= 0.0 else 'hold'


def _evidence_ready(diff: dict[str, Any], scorecard: dict[str, Any], reward_heads: dict[str, Any], errors: list[str]) -> bool:
 if errors:
  return False
 if not diff.get('tuned_frontier') or not isinstance(diff.get('per_candidate_marginal_delta'), dict):
  return False
 if _violation_count(scorecard) != 0:
  return False
 return reward_heads.get('decision') == 'pass'


def _marginal(diff: dict[str, Any]) -> float:
 try:
  return float(diff.get('avg_marginal_reward_delta', diff.get('avg_reward_delta', 0.0)) or 0.0)
 except (TypeError, ValueError):
  return 0.0


def _build_ablation_artifacts(
 *,
 evidence_dir: Path,
 observation_path: Path,
 profile_path: Path,
 tuning_path: Path | None,
 baseline_tuning_path: Path | None,
 goal: str,
 scorecard_replay_path: Path,
 offline_report_path: Path | None,
) -> dict[str, tuple[Path, dict[str, Any], Path, dict[str, Any], list[str]]]:
 evidence_dir.mkdir(parents=True, exist_ok=True)
 offline_report=_load_optional_json(offline_report_path)
 artifacts={}
 for name in ABLATIONS:
  errors=[]
  frontier_path=evidence_dir/f'{name}_frontier_diff.json'
  scorecard_path=evidence_dir/f'{name}_scorecard.json'
  try:
   diff=build_frontier_diff(
    observation_path=observation_path,
    profile_path=profile_path,
    tuning_path=tuning_path,
    baseline_tuning_path=baseline_tuning_path,
    goal=goal,
    ablation=name,
   )
   atomic_write_json(frontier_path, diff)
  except Exception as exc:
   diff={}
   errors.append(f'{name} frontier rerun failed: {exc}')
  try:
   scorecard=build_scorecard(replay_path=scorecard_replay_path, frontier_diff=diff, offline_report=offline_report)
   atomic_write_json(scorecard_path, scorecard)
  except Exception as exc:
   scorecard={}
   errors.append(f'{name} scorecard rerun failed: {exc}')
  artifacts[name]=(frontier_path, diff, scorecard_path, scorecard, errors)
 return artifacts


def build_report(
 *,
 candidate: str,
 current: str,
 frontier_diff_path: Path,
 scorecard_path: Path,
 reward_heads_path: Path,
 evidence_dir: Path | None = None,
 observation_path: Path | None = None,
 profile_path: Path | None = None,
 tuning_path: Path | None = None,
 baseline_tuning_path: Path | None = None,
 goal: str = 'Make next week less chaotic',
 scorecard_replay_path: Path | None = None,
 offline_report_path: Path | None = None,
) -> dict[str, Any]:
 diff,diff_error=_load_json(frontier_diff_path)
 scorecard,score_error=_load_json(scorecard_path)
 reward_heads,reward_error=_load_json(reward_heads_path)
 global_errors=[e for e in [diff_error, score_error, reward_error] if e]
 if diff and not diff.get('tuned_frontier'):
  global_errors.append('frontier_diff has no tuned_frontier rows')
 if diff and not isinstance(diff.get('per_candidate_marginal_delta'), dict):
  global_errors.append('frontier_diff has no per_candidate_marginal_delta object')
 if scorecard and 'invariants' not in scorecard:
  global_errors.append('scorecard has no invariants block')
 if reward_heads and not isinstance(reward_heads.get('reward_head_deltas'), dict):
  global_errors.append('reward_heads has no reward_head_deltas object')
 reward_deltas=dict(reward_heads.get('reward_head_deltas', {})) if isinstance(reward_heads.get('reward_head_deltas'), dict) else {}
 if evidence_dir is not None:
  replay_path=scorecard_replay_path
  if replay_path is None and isinstance(scorecard.get('replay_path'), str):
   replay_path=_resolve(scorecard['replay_path'])
  replay_path=replay_path or _resolve('tests/fixtures/replay_golden.jsonl')
  per_ablation=_build_ablation_artifacts(
   evidence_dir=evidence_dir,
   observation_path=observation_path or _resolve('data/sample_calendar.json'),
   profile_path=profile_path or _resolve('data/sample_profile.json'),
   tuning_path=tuning_path,
   baseline_tuning_path=baseline_tuning_path,
   goal=goal,
   scorecard_replay_path=replay_path,
   offline_report_path=offline_report_path,
  )
 else:
  per_ablation={name:(frontier_diff_path, diff, scorecard_path, scorecard, []) for name in ABLATIONS}
 ablations={}
 critical_components=[]
 non_effective_components=[]
 evidence_errors=list(global_errors)
 for name in ABLATIONS:
  ablation_frontier_path, ablation_diff, ablation_scorecard_path, ablation_scorecard, ablation_errors=per_ablation[name]
  errors=global_errors+ablation_errors
  if ablation_diff and not ablation_diff.get('tuned_frontier'):
   errors.append(f'{name} frontier_diff has no tuned_frontier rows')
  if ablation_diff and not isinstance(ablation_diff.get('per_candidate_marginal_delta'), dict):
   errors.append(f'{name} frontier_diff has no per_candidate_marginal_delta object')
  if ablation_scorecard and 'invariants' not in ablation_scorecard:
   errors.append(f'{name} scorecard has no invariants block')
  evidence_errors.extend(ablation_errors)
  frontier_summary=_summarize_frontier(ablation_diff)
  scorecard_summary=_summarize_scorecard(ablation_scorecard)
  evidence_ready=_evidence_ready(ablation_diff, ablation_scorecard, reward_heads, errors)
  promotion_decision=_decision_for_inputs(ablation_diff, ablation_scorecard, reward_heads, errors)
  marginal=_marginal(ablation_diff)
  if evidence_ready and promotion_decision=='hold':
   critical_components.append(name)
  elif evidence_ready:
   non_effective_components.append(name)
  signal_assessment=None
  if name in {'no_semantic_labels','no_derived_signals'}:
   signal_assessment={
    'load_bearing':None if not evidence_ready else promotion_decision=='hold',
    'basis':'signal-layer ablation has its own frontier_diff and scorecard rerun evidence' if evidence_ready else 'input evidence did not pass, so signal load-bearing status is held',
   }
  ablations[name]={
   'ablation_evidence':{
    'frontier_diff':_artifact_ref(ablation_frontier_path, ablation_diff),
    'scorecard':_artifact_ref(ablation_scorecard_path, ablation_scorecard),
    'rerun':evidence_dir is not None,
    'ablation_applied':bool(ablation_diff.get('ablation_applied')),
   },
   'frontier_diff':frontier_summary,
   'scorecard':scorecard_summary,
   'reward_head_deltas':reward_deltas,
   'promotion_decision':promotion_decision,
   'decision_basis':{
    'avg_marginal_reward_delta':frontier_summary.get('avg_marginal_reward_delta'),
    'invariant_violations':scorecard_summary.get('invariant_violations'),
    'reward_head_decision':reward_heads.get('decision') if reward_heads else None,
    'input_errors':errors,
    'component_effect':'critical' if evidence_ready and promotion_decision=='hold' else ('non_effective' if evidence_ready else 'held'),
   },
  }
  if signal_assessment is not None:
   ablations[name]['signal_layer_assessment']=signal_assessment
 decision='pass' if not evidence_errors and reward_heads.get('decision')=='pass' else 'hold'
 return {
  'ablation_schema_version':'policy_ablation_report.v1',
  'candidate_policy_tuning_id':candidate,
  'current_policy_tuning_id':current,
  'input_artifacts':{
   'frontier_diff':_artifact_ref(frontier_diff_path, diff),
   'scorecard':_artifact_ref(scorecard_path, scorecard),
   'reward_heads':_artifact_ref(reward_heads_path, reward_heads),
  },
  'ablations':ablations,
  'critical_components':sorted(set(critical_components)) if decision=='pass' else [],
  'non_effective_components':sorted(set(non_effective_components)) if decision=='pass' else [],
  'hold_reasons':[{'reason':e,'owner':'ML instrument owner','next_unblock_action':'provide non-empty frontier_diff, scorecard, and reward head artifacts'} for e in evidence_errors],
  'decision':'pass' if decision=='pass' else 'hold',
 }


def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--candidate',default='candidate'); ap.add_argument('--current',default='CURRENT'); ap.add_argument('--frontier-diff',default='runs/frontier_diff.json'); ap.add_argument('--scorecard',default='runs/ml_scorecard.json'); ap.add_argument('--reward-heads',default='runs/p12_reward_head_report.json'); ap.add_argument('--evidence-dir',default=''); ap.add_argument('--observation',default='data/sample_calendar.json'); ap.add_argument('--profile',default='data/sample_profile.json'); ap.add_argument('--tuning',default=''); ap.add_argument('--baseline-tuning',default=''); ap.add_argument('--goal',default='Make next week less chaotic'); ap.add_argument('--scorecard-replay',default=''); ap.add_argument('--offline-report',default=''); ap.add_argument('--out',default='runs/p12_policy_ablation_report.json'); args=ap.parse_args()
 out=Path(args.out); out=out if out.is_absolute() else ROOT/out
 evidence_dir=_resolve(args.evidence_dir) if args.evidence_dir else out.parent/'policy_ablation_evidence'
 payload=build_report(candidate=args.candidate,current=args.current,frontier_diff_path=_resolve(args.frontier_diff),scorecard_path=_resolve(args.scorecard),reward_heads_path=_resolve(args.reward_heads),evidence_dir=evidence_dir,observation_path=_resolve(args.observation),profile_path=_resolve(args.profile),tuning_path=_resolve(args.tuning) if args.tuning else None,baseline_tuning_path=_resolve(args.baseline_tuning) if args.baseline_tuning else None,goal=args.goal,scorecard_replay_path=_resolve(args.scorecard_replay) if args.scorecard_replay else None,offline_report_path=_resolve(args.offline_report) if args.offline_report else None)
 atomic_write_json(out,payload); print(json.dumps({'ok':payload['decision']=='pass','decision':payload['decision'],'out':str(out)},indent=2))
if __name__=='__main__': main()
