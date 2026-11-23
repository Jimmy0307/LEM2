"""Algorithm-neutral metrics; parity with baseline fedrs.metrics is tested."""
from __future__ import annotations
from typing import Sequence
import numpy as np


def scores(y_true: Sequence,y_pred: Sequence):
    y,p=np.asarray(y_true,dtype=object),np.asarray(y_pred,dtype=object)
    if len(y)!=len(p):raise ValueError('prediction length mismatch')
    recalls=[float((p[y==c]==c).mean()) for c in dict.fromkeys(y.tolist())]
    balanced=float(np.mean(recalls)) if recalls else 0.0
    classes=sorted(set(y.tolist())|set(p.tolist()),key=str)
    f1=[]
    for c in classes:
        tp=int(((y==c)&(p==c)).sum())
        fp=int(((y!=c)&(p==c)).sum())
        fn=int(((y==c)&(p!=c)).sum())
        precision=tp/(tp+fp) if tp+fp else 0.0
        recall=tp/(tp+fn) if tp+fn else 0.0
        f1.append(2*precision*recall/(precision+recall) if precision+recall else 0.0)
    return {'accuracy':float((y==p).mean()) if len(y) else 0.0,
            'ba':balanced,'macro_f1':float(np.mean(f1)) if f1 else 0.0}
