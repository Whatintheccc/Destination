#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.providers.deterministic import DeterministicCalendarProvider
from calendar_pilot.types import CandidateCalendarAction, RawCalendarObservation

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--observation',required=True); ap.add_argument('--frontier',required=True); ap.add_argument('--out',default='runs/p12_shadow_provider_preview.json'); args=ap.parse_args()
    op=Path(args.observation); op=op if op.is_absolute() else ROOT/op
    raw=json.loads(op.read_text()); obs=RawCalendarObservation.from_dict(raw.get('observation',raw))
    fp=Path(args.frontier); fp=fp if fp.is_absolute() else ROOT/fp
    fr=json.loads(fp.read_text()); candidates=fr.get('candidates',[])
    provider=DeterministicCalendarProvider(seed_observation=obs)
    previews=[]
    for row in candidates[:5]:
        cand=CandidateCalendarAction.from_dict(row); previews.append({'candidate_id':cand.candidate_id,'conflicts':provider.preview(cand),'operation':'preview','signal_stream':'world'})
    payload={'shadow_provider_preview_schema_version':'shadow_provider_preview.v1','mode':'shadow_no_commit','provider_id':provider.provider_id,'observation_id':obs.observation_id,'previews':previews,'commits':0,'signal_stream':'world'}
    out=Path(args.out); out=out if out.is_absolute() else ROOT/out; atomic_write_json(out,payload); print(json.dumps({'ok':True,'commits':0,'out':str(out)},indent=2))
if __name__=='__main__': main()
