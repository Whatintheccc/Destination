#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from calendar_pilot.diffusiongemma.policy import DiffusionGemmaPolicy
from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.types import RawCalendarObservation, UserBiography

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--observation',required=True); ap.add_argument('--profile',default='data/sample_profile.json'); ap.add_argument('--out',default='runs/p12_shadow_frontier.json'); args=ap.parse_args()
    op=Path(args.observation); op=op if op.is_absolute() else ROOT/op
    raw=json.loads(op.read_text()); obs_raw=raw.get('observation', raw)
    obs=RawCalendarObservation.from_dict(obs_raw)
    pp=Path(args.profile); pp=pp if pp.is_absolute() else ROOT/pp
    bio=UserBiography.from_dict(json.loads(pp.read_text()))
    candidates=[c.to_dict() for c in DiffusionGemmaPolicy().generate_candidates(obs,bio)]
    payload={'shadow_frontier_schema_version':'shadow_frontier.v1','observation_id':obs.observation_id,'mode':'shadow_no_commit','candidate_count':len(candidates),'candidates':candidates,'signal_stream':'system'}
    out=Path(args.out); out=out if out.is_absolute() else ROOT/out; atomic_write_json(out,payload); print(json.dumps({'ok':True,'candidate_count':len(candidates),'out':str(out)},indent=2))
if __name__=='__main__': main()
