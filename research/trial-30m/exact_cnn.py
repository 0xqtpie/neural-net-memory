#!/usr/bin/env python3
import json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(Path(__file__).resolve().parent))
from search import exact
from verifier import load,verify
from trial_search import emit,OUT
from lifetimes import admit
g=load(ROOT/'benchmarks/graphs/resnet-b2-c32.json');results=[]
for budget in [0,37847040]:
    start=time.perf_counter()
    try:
        c=exact(g,budget,max_states=300000);verify(g,c,budget)
        p=OUT/'bounds'/f"resnet-b2-c32-b{budget}-exact.json";p.parent.mkdir(exist_ok=True);p.write_text(json.dumps(c,indent=2)+'\n')
        result={'graph':g['id'],'budget':budget,'status':'optimum','peak_bytes':c['claims']['peak_bytes'],'object':str(p.relative_to(ROOT)),'seconds':time.perf_counter()-start,**c['metadata']}
        emit('exact_bound',**result)
    except RuntimeError as e:
        result={'graph':g['id'],'budget':budget,'status':'resource_limit','message':str(e),'seconds':time.perf_counter()-start};emit('exact_bound',**result)
    results.append(result)
(OUT/'exact-cnn-results.json').write_text(json.dumps(results,indent=2)+'\n')
