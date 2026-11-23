"""Actual Spark RDD dispatch of independent dataset/seed/algorithm jobs.

This is *job-level Spark parallelism*, NOT distributed LEM2 training. Each
executor fits a local model for its own run. Inputs must be readable by ALL
Spark workers at the same path (shared mounted path/HDFS-staged local files).
Only the driver creates checkpoints, avoiding duplicate writes on task retries.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from federated_decision_making.runner import Case, run_case, write_checkpoint


def process(job):
    try:
        return run_case(Case.from_dict(job),external_plugins=None)
    except Exception as exc:
        return {'status':'FAILED','dataset_id':str(job.get('dataset_id')),
                'algorithm':str(job.get('algorithm')),'seed':job.get('seed'),
                'scenario':job.get('scenario'),'error_type':type(exc).__name__,
                'error':str(exc)[:1600]}


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--partitions',type=int,default=4)
    args=p.parse_args(argv)
    document=json.loads(args.manifest.read_text(encoding='utf-8'))
    if set(document)!={'api_version','jobs'} or document['api_version']!='1.0':
        raise ValueError('manifest api_version and jobs required')
    jobs=document['jobs']
    if not jobs or not isinstance(jobs,list): raise ValueError('manifest jobs must be nonempty list')
    if args.partitions<1: raise ValueError('partitions must be positive')
    # Fail fast on invalid schema BEFORE Spark is initialized.
    _=[Case.from_dict(x) for x in jobs]
    from pyspark.sql import SparkSession
    spark=SparkSession.builder.appName('ResearchPluginPlatformV1').getOrCreate()
    try:
        outputs=spark.sparkContext.parallelize(jobs,min(args.partitions,len(jobs))).map(process).collect()
        successes,failures=0,[]
        for result in outputs:
            if result['status']=='SUCCESS':
                path,created=write_checkpoint(result,args.output)
                successes+=1
                print('CHECKPOINT',path,'CREATED' if created else 'ALREADY_EXISTS',flush=True)
            else:failures.append(result)
        if failures:
            import time
            path=args.output/('spark_failures_'+str(int(time.time()))+'.json')
            path.parent.mkdir(parents=True,exist_ok=True)
            # error report only, do not replace successful checkpoints
            path.write_text(json.dumps(failures,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'jobs':len(jobs),'successes':successes,'failures':len(failures),
                          'note':'RDD dispatch of whole-run tasks; no distributed LEM2 algorithm'},ensure_ascii=False))
        return 0 if not failures else 2
    finally:
        spark.stop()


if __name__=='__main__':
    raise SystemExit(main())
