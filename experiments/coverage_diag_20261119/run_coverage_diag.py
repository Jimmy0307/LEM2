"""Train vs Test rule coverage diagnostic (2026-11-19).

Uses the frozen full-scale pipeline code (fedrs/, roughset/ from
research/full-scale-six-policy-20261118 @ 1b940f8): nested 64/16/20 split,
EQUAL_WIDTH_3, CLASSICAL positive-region reduct, LEM2, UNION.  Reports, per
model: positive-region fraction, coverage of the development (train) rows,
coverage of the test rows, number of empty-antecedent (TRUE) rules, and
test coverage by non-empty rules only.  Test labels are not used.

Data: scikit-learn bundled wine / breast_cancer / iris (first <=6 features)
and the two repo subsets in docs/research/public_datasets/.
Run from the root of the full-scale branch:  python run_coverage_diag.py OUT.csv
"""
import sys, numpy as np, pandas as pd
from pathlib import Path
ROOT=Path.cwd(); sys.path.insert(0,str(ROOT))
from fedrs.experiment import fit_model, nested_split
from fedrs.partition import original_partition
from fedrs.predict import match_matrix
from roughset.preprocessing import detect_feature_types
from sklearn import datasets as skd
def cov(fm,frame,rules):
    m=match_matrix(frame,rules); m=np.asarray(m.todense() if hasattr(m,'todense') else m)
    return 100*(m.sum(axis=1)>0).mean()
srcs={}
for name,ld in [('wine',skd.load_wine),('breast_cancer',skd.load_breast_cancer),('iris',skd.load_iris)]:
    b=ld(as_frame=True); f=b.frame.rename(columns={'target':'y'}); srcs[name]=(f,[c for c in f.columns if c!='y'][:6])
for name,fn in [('ai4i','ai4i_maintenance_public_stratified_subset.csv'),('online_shoppers','online_shoppers_public_stratified_subset.csv')]:
    f=pd.read_csv(str(ROOT/'docs/research/public_datasets')+'/'+fn); print(name,f.columns.tolist()[:12], f.shape)
    srcs[name]=(f,None)
out=[]
for name,(f,feats) in srcs.items():
    tgt='y' if 'y' in f.columns else f.columns[-1]
    if feats is None: feats=[c for c in f.columns if c!=tgt][:6]
    f=f[feats+[tgt]].dropna(); f.columns=[str(c).replace(' ','_') for c in f.columns]; feats=[str(c).replace(' ','_') for c in feats]
    for sc in ['CENTRALIZED','FED_IID','FED_A01']:
      for seed in (1001,1002,1003,1004,1005):
        dev,val,test=nested_split(f,tgt,seed)
        clients={'central':dev} if sc=='CENTRALIZED' else original_partition(dev,tgt,3,seed,'IID' if sc=='FED_IID' else 'NONIID_01')
        cont,cat=detect_feature_types(dev,feats,unique_numeric_threshold=10)
        fm=fit_model(feats,cont,cat,tgt,clients,dev,val,test,'EQUAL_WIDTH_3','CLASSICAL',1.0)
        pos=np.mean([m.pos_fraction_reduct for m in fm.local.values()])
        out.append(dict(dataset=name,scenario=sc,seed=seed,n=len(f),n_cont=len(cont),rules=len(fm.rules),pos_region_pct=100*pos,
          train_cov=cov(fm,fm.frames['dev'],fm.rules),test_cov=cov(fm,fm.frames['test'],fm.rules),true_rules=sum(1 for r in fm.rules if not r.conditions),
          test_cov_nonempty=cov(fm,fm.frames['test'],tuple(r for r in fm.rules if r.conditions)) if any(r.conditions for r in fm.rules) else 0.0))
R=pd.DataFrame(out); print(R.groupby(['dataset','scenario']).mean(numeric_only=True).round(1).drop(columns='seed').to_string())
R.to_csv(sys.argv[1] if len(sys.argv)>1 else 'TRAIN_TEST_COVERAGE_DIAG.csv',index=False)
