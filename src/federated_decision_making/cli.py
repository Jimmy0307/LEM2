"""CLI is a transport-independent adapter to the same run_case API."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from .api import Capabilities
from .registry import load_algorithm, available_plugins, PLANNED
from .runner import Case, run_case, write_checkpoint, case_identity
from .batch import load_manifest, execute_batch, paired_comparison


def parse_plugin(values):
    entries={}
    for item in values:
        if '=' not in item: raise ValueError('--plugin must be ALGORITHM=installed.module:Class')
        a,b=item.split('=',1)
        if a in entries: raise ValueError('duplicate plugin registration')
        entries[a]=b
    return entries


def main(argv=None):
    p=argparse.ArgumentParser(description='LEM2-neutral research interface v1')
    sub=p.add_subparsers(dest='command',required=True)
    ls=sub.add_parser('list',aliases=['algorithms'],help='installed plugins and capabilities')
    run=sub.add_parser('run',help='run one dataset x seed x scenario with checkpoint')
    batch=sub.add_parser('batch',help='run multiple algorithms/datasets with resumable checkpoints')
    batch.add_argument('--manifest',type=Path,required=True)
    batch.add_argument('--output',type=Path,required=True)
    batch.add_argument('--fail-fast',action='store_true')
    compare=sub.add_parser('compare',help='matched algorithm comparison against named baseline')
    compare.add_argument('--results',type=Path,required=True)
    compare.add_argument('--baseline',required=True)
    compare.add_argument('--csv',type=Path,required=True)
    run.add_argument('--case',type=Path,required=True,help='JSON Case, explicit feature columns and target')
    run.add_argument('--output',type=Path,required=True)
    for q in [ls,run,batch]: q.add_argument('--plugin',action='append',default=[],help='register trusted external ALGO=module:Class')
    args=p.parse_args(argv)
    external=parse_plugin(getattr(args,'plugin',[]))
    if args.command in ('list','algorithms'):
        for name in sorted(set(available_plugins(external))|PLANNED):
            try:
                plugin=load_algorithm(name,external)
                cap=plugin.capabilities
                if callable(getattr(plugin,'check_engine',None)):
                    plugin.check_engine()
                print(json.dumps({'algorithm':name,'status':'AVAILABLE','capabilities':vars(cap)},ensure_ascii=False,default=list))
            except NotImplementedError as exc:
                print(json.dumps({'algorithm':name,'status':'INTERFACE_RESERVED_NOT_INSTALLED','detail':str(exc)},ensure_ascii=False))
            except (ImportError, ModuleNotFoundError) as exc:
                print(json.dumps({'algorithm':name,'status':'MISSING_ENGINE','detail':str(exc)},ensure_ascii=False))
        return 0
    if args.command=='batch':
        cases=load_manifest(args.manifest)
        result=execute_batch(cases,args.output,external,fail_fast=args.fail_fast)
        print(json.dumps(result,ensure_ascii=False))
        return 0 if not result['failed'] else 2
    if args.command=='compare':
        table=paired_comparison(args.results,args.baseline)
        args.csv.parent.mkdir(parents=True,exist_ok=True)
        table.to_csv(args.csv,index=False)
        print(json.dumps({'status':'SUCCESS','pairs':len(table),'csv':str(args.csv)},ensure_ascii=False))
        return 0
    spec=json.loads(args.case.read_text(encoding='utf-8'))
    case=Case.from_dict(spec)
    identity,source_sha,software_sha=case_identity(case,external)
    existing=args.output/(identity+'.json')
    if existing.exists():
        record=json.loads(existing.read_text(encoding='utf-8'))
        if record.get('status')!='SUCCESS' or record.get('source_sha256')!=source_sha or record.get('software_sha')!=software_sha:
            raise RuntimeError('Existing checkpoint source/code contract mismatch')
        print(json.dumps({'status':'SKIPPED_VERIFIED','checkpoint':str(existing),'run_id':identity},ensure_ascii=False))
        return 0
    record=run_case(case,external)
    path,wrote=write_checkpoint(record,args.output)
    print(json.dumps({'status':'SUCCESS','checkpoint':str(path),'created':wrote,'run_id':record['run_id'],
                      'algorithm':record['algorithm'],'metrics':record['metrics']},ensure_ascii=False))
    return 0


if __name__=='__main__':
    sys.exit(main())
