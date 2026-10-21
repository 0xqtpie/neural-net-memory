#!/usr/bin/env python3
"""Independent time-indexed CP-SAT encoding of activation-memory/v1.

Complete horizon: at most n+B/min(cost) forwards; each can be dropped once,
plus n backwards and one loss. Extra no-op steps are allowed. Thus H=3n+2k+1
covers every useful complete schedule, without imposing a topological order.
This is a new adapter, not a run of Checkmate, DTR or Moccasin.
"""
import argparse,hashlib,json,math,platform,sys,time
from pathlib import Path
from ortools.sat.python import cp_model
import ortools
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from verifier import load,verify,validate_graph,simulate
from search import certificate,baseline_candidates,exact
OUT=Path(__file__).resolve().parent

def solve(g,budget,seconds=15):
    validate_graph(g);ns=g['nodes'];n=len(ns);idx={v['id']:i for i,v in enumerate(ns)}
    H=3*n+2*(budget//min(v['cost'] for v in ns))+1
    if H>120:raise ValueError('adapter horizon cap; no optimality claim')
    m=cp_model.CpModel()
    def bs(name,rows,cols):return [[m.new_bool_var(f'{name}_{t}_{i}') for i in range(cols)] for t in range(rows)]
    live=bs('live',H+1,n);seen=bs('seen',H+1,n);done=bs('done',H+1,n)
    f=bs('f',H,n);drop=bs('drop',H,n);back=bs('b',H,n);first=bs('first',H,n);repeat=bs('repeat',H,n)
    phase=[m.new_bool_var(f'phase_{t}') for t in range(H+1)];loss=[m.new_bool_var(f'loss_{t}') for t in range(H)]
    for i in range(n):m.add(live[0][i]==0);m.add(seen[0][i]==0);m.add(done[0][i]==0);m.add(done[H][i]==1)
    m.add(phase[0]==0);m.add(phase[H]==1)
    fixed=sum(v['bytes'] for v in g['inputs']);unit=math.gcd(fixed,*[v['bytes'] for v in ns]);peak=m.new_int_var(fixed//unit,(fixed+sum(v['bytes'] for v in ns))//unit,'peak')
    for t in range(H+1):m.add(peak>=fixed//unit+sum((v['bytes']//unit)*live[t][i] for i,v in enumerate(ns)))
    for t in range(H):
        m.add(sum(f[t]+drop[t]+back[t])+loss[t]<=1)
        m.add(phase[t+1]==phase[t]+loss[t])
        for i,v in enumerate(ns):
            m.add(live[t+1][i]==live[t][i]+f[t][i]-drop[t][i]);m.add(seen[t+1][i]==seen[t][i]+first[t][i]);m.add(done[t+1][i]==done[t][i]+back[t][i])
            m.add(first[t][i]+repeat[t][i]==f[t][i]);m.add(first[t][i]+seen[t][i]<=1);m.add(repeat[t][i]<=seen[t][i]);m.add(first[t][i]+phase[t]<=1)
            if not v['recomputable']:m.add(repeat[t][i]==0)
            m.add(f[t][i]+live[t][i]<=1);m.add(drop[t][i]<=live[t][i]);m.add(back[t][i]<=phase[t]);m.add(back[t][i]+done[t][i]<=1)
            for dep in v['deps']:
                if dep in idx:m.add(f[t][i]<=live[t][idx[dep]])
            for req in v['backward_requires']:
                if req in idx:m.add(back[t][i]<=live[t][idx[req]])
            for j,child in enumerate(ns):
                if v['id'] in child['deps']:m.add(back[t][i]<=done[t][j])
            m.add(loss[t]<=seen[t][i])
            if v['id'] in g['outputs']:m.add(loss[t]<=live[t][i])
    m.add(sum(ns[i]['cost']*repeat[t][i] for t in range(H) for i in range(n))<=budget)
    m.minimize(peak);s=cp_model.CpSolver();s.parameters.max_time_in_seconds=seconds;s.parameters.num_search_workers=1;s.parameters.random_seed=20261021
    started=time.perf_counter();status=s.solve(m);elapsed=time.perf_counter()-started
    result={'status':s.status_name(status),'horizon':H,'seconds':elapsed,'limit_seconds':seconds,'workers':1,'seed':20261021,'best_bound_bytes':round(s.best_objective_bound*unit)}
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):return result,None
    actions=[]
    for t in range(H):
        if s.value(loss[t]):actions.append({'op':'loss'})
        for i,v in enumerate(ns):
            for op,variables in [('forward',f),('drop',drop),('backward',back)]:
                if s.value(variables[t][i]):actions.append({'op':op,'node':v['id']})
    c=certificate(g,actions,budget,'CP-SAT time-indexed v1',result)
    assert c['claims']['peak_bytes']==round(s.objective_value*unit)
    verify(g,c,budget);result.update(c['claims']);return result,c

def main():
    p=argparse.ArgumentParser();p.add_argument('--seconds',type=float,default=15);a=p.parse_args()
    graphs=[load(ROOT/f'benchmarks/graphs/{name}.json') for name in ('chain6-unit','chain6-weighted','diamond5','skip6','stateful4')]+[load(OUT/'graph.json')]
    results=[]
    for g in graphs:
        for budget in (0,2,4):
            baselines=[]
            for name,actions in baseline_candidates(g):
                # Simulation gets the actual extra cost, before selecting budget-compatible candidates.
                metrics=simulate(g,actions,10**12)
                if metrics['recompute_cost']<=budget:baselines.append((metrics['peak_bytes'],name))
            baseline=min(baselines)
            ref=exact(g,budget,max_states=2000000)
            result,c=solve(g,budget,a.seconds)
            result.update(graph=g['id'],budget=budget,baseline_peak_bytes=baseline[0],baseline_method=baseline[1],reference_exact_peak_bytes=ref['claims']['peak_bytes'])
            if c:
                if result['status']=='OPTIMAL':assert result['peak_bytes']==ref['claims']['peak_bytes']
                assert result['best_bound_bytes']<=ref['claims']['peak_bytes']<=result['peak_bytes']
                dest=OUT/'certificates'/f'{g["id"]}-b{budget}.json';dest.parent.mkdir(exist_ok=True);dest.write_text(json.dumps(c,indent=2)+'\n');result['certificate']=str(dest.relative_to(ROOT))
            results.append(result)
            (OUT/'solver-results.json').write_text(json.dumps({'solver':f'OR-Tools {ortools.__version__} CP-SAT','adapter_scope':'new identical-semantics formulation; not a native Checkmate/DTR/Moccasin comparison','python':platform.python_version(),'platform':platform.platform(),'runs':results},indent=2)+'\n')
            print(g['id'],budget,result,flush=True)
if __name__=='__main__':main()
