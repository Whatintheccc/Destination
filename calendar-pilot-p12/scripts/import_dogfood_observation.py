#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from calendar_pilot.environment.fsio import atomic_write_json

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--provider',default='fixture'); ap.add_argument('--source',default='data/sample_calendar.json'); ap.add_argument('--out',default='runs/p12_dogfood_observation.json'); args=ap.parse_args()
    src=Path(args.source); src=src if src.is_absolute() else ROOT/src
    obs=json.loads(src.read_text())
    acct=hashlib.sha256(f"{args.provider}:{obs.get('user_scope_id','local') }".encode()).hexdigest()[:16]
    payload={'dogfood_observation_schema_version':'dogfood_observation.v1','observation_id':obs.get('observation_id','obs_fixture'),'source_provider':args.provider,'provider_account_hash':acct,'calendar_count':len({e.get('calendar_id','default') for e in obs.get('events',[])}),'event_count':len(obs.get('events',[])),'task_count':len(obs.get('tasks',[])),'time_zone_id':obs.get('time_zone_id','UTC'),'observed_at':obs.get('observed_at'),'redaction_policy':'fixture_or_local_only','redaction_hash_salt_id':'local','imported_at':datetime.now(timezone.utc).isoformat(),'streams_captured':['world','action','biography'],'observation':obs,'signal_stream':'world'}
    out=Path(args.out); out=out if out.is_absolute() else ROOT/out; atomic_write_json(out,payload); print(json.dumps({'ok':True,'out':str(out)},indent=2))
if __name__=='__main__': main()
