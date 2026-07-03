#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from calendar_pilot.environment.fsio import atomic_write_json
CAPS=['read_observation','preview','commit','verify','rollback','idempotency','external_id_mapping','sandbox_enforcement','rate_cap_denial','local_time_echo','timezone_integrity','provider_error_replay']
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--provider',default='deterministic'); ap.add_argument('--out',default='runs/p12_provider_capability_report.json'); args=ap.parse_args(); supported=args.provider in {'deterministic','deterministic_fixture_provider','apple_eventkit'}; caps={k: bool(supported) for k in CAPS};
 if args.provider=='google_stub_or_sandbox' or args.provider=='microsoft_stub_or_sandbox': caps={k:False for k in CAPS}; caps['read_observation']=True
 payload={'provider_capability_schema_version':'provider_capability_report.v1','provider_id':args.provider,'capabilities':caps,'unsupported_operations':[k for k,v in caps.items() if not v],'sandbox_enforced':args.provider in {'apple_eventkit'},'decision':'pass' if caps.get('read_observation') else 'hold'}
 out=Path(args.out); out=out if out.is_absolute() else ROOT/out; atomic_write_json(out,payload); print(json.dumps({'ok':True,'out':str(out)},indent=2))
if __name__=='__main__': main()
