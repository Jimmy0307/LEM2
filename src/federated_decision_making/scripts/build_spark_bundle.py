"""Build a deterministic source-only Spark --py-files bundle. No datasets/secrets.

External adapters still need installation on each executor (entry-point metadata);
this ZIP alone cannot install binary dependencies or third-party plugins.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo

import federated_decision_making

def build(output: Path, *, legacy_repo: Path | None = None):
    package = Path(federated_decision_making.__file__).resolve().parent
    locations = [(package, 'federated_decision_making')]
    if legacy_repo is not None:
        for name in ('fedrs','roughset'):
            src = legacy_repo / name
            if not (src/'__init__.py').exists():
                raise FileNotFoundError(f'legacy engine package not found: {src}')
            locations.append((src,name))
    records=[]
    output.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(output,'w',ZIP_DEFLATED,compresslevel=9) as z:
        for source,prefix in locations:
            for p in sorted(source.rglob('*.py')):
                if '__pycache__' in p.parts:continue
                rel=prefix+'/'+p.relative_to(source).as_posix()
                data=p.read_bytes()
                meta=ZipInfo(rel,(2026,1,1,0,0,0)); meta.compress_type=ZIP_DEFLATED
                z.writestr(meta,data)
                records.append({'name':rel,'sha256':hashlib.sha256(data).hexdigest()})
    sha=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix+'.manifest.json').write_text(
        json.dumps({'zip_sha256':sha,'files':records,
        'contains_private_data':False,'legacy_engine_included':legacy_repo is not None},indent=2)+'\n',encoding='utf8')
    return sha,len(records)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--legacy-repo',type=Path,default=None)
    args=p.parse_args(argv)
    print(json.dumps({'sha256':build(args.output,legacy_repo=args.legacy_repo)[0],
                      'file':str(args.output)},ensure_ascii=False))

if __name__=='__main__':main()
