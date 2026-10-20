#!/usr/bin/env python3
"""Exact minimax search with cost/peak Pareto dominance per logical pebble state."""
import argparse,heapq,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(Path(__file__).resolve().parent))
from verifier import load,validate_graph,verify
from search import certificate
from trial_search import OUT,emit

def solve(g,budget,max_labels=500000,upper=None):
    validate_graph(g);nodes=g['nodes'];n=len(nodes)
    if n>16:raise ValueError('trial exact solver limited to 16 nodes')
    idx={v['id']:i for i,v in enumerate(nodes)}
    def mask(names):return sum(1<<idx[x] for x in names if x in idx)
    deps=[mask(v['deps']) for v in nodes];req=[mask(v['backward_requires']) for v in nodes]
    children=[mask([v['id'] for v in nodes if p['id'] in v['deps']]) for p in nodes]
    full=(1<<n)-1;outputs=mask(g['outputs']);fixed=sum(x['bytes'] for x in g['inputs'])
    memory=[fixed]*(1<<n)
    for bits in range(1,1<<n):
        low=bits&-bits;memory[bits]=memory[bits^low]+nodes[low.bit_length()-1]['bytes']
    # Immutable records retain valid parent chains even after label dominance.
    records=[((0,0,0,False),0,fixed,None,None)]
    labels={(0,0,0,False):{0:(fixed,0)}};queue=[(fixed,0,0)];expanded=0;pruned=0
    while queue:
        peak,spent,rid=heapq.heappop(queue);state,_,_,parent,action=records[rid]
        if labels.get(state,{}).get(spent)!=(peak,rid):continue
        live,seen,done,phase=state;expanded+=1
        if phase and done==full:
            actions=[];at=rid
            while records[at][3] is not None:
                actions.append(records[at][4]);at=records[at][3]
            actions.reverse();c=certificate(g,actions,budget,'trial-exact-dominance',{'optimal':True,'labels_created':len(records),'logical_states':len(labels),'expanded':expanded,'dominance_pruned':pruned,'upper_bound':upper})
            assert c['claims']['peak_bytes']==peak
            return c
        moves=[]
        if not phase and seen==full and live&outputs==outputs:moves.append(((live,seen,done,True),spent,{'op':'loss'}))
        for i,node in enumerate(nodes):
            bit=1<<i
            if live&bit:moves.append(((live^bit,seen,done,phase),spent,{'op':'drop','node':node['id']}))
            elif live&deps[i]==deps[i]:
                extra=node['cost'] if seen&bit else 0
                if (not(seen&bit) or node['recomputable']) and spent+extra<=budget:
                    moves.append(((live|bit,seen|bit,done,phase),spent+extra,{'op':'forward','node':node['id']}))
            if phase and not(done&bit) and done&children[i]==children[i] and live&req[i]==req[i]:
                moves.append(((live,seen,done|bit,phase),spent,{'op':'backward','node':node['id']}))
        for target,newcost,action in moves:
            score=max(peak,memory[target[0]])
            if upper is not None and score>upper:continue
            front=labels.setdefault(target,{})
            if any(cost<=newcost and oldpeak<=score for cost,(oldpeak,_) in front.items()):pruned+=1;continue
            for cost in [cost for cost,(oldpeak,_) in front.items() if cost>=newcost and oldpeak>=score]:del front[cost]
            if len(records)>=max_labels:raise RuntimeError(f'label limit {max_labels}; NO optimality claim')
            nr=len(records);records.append((target,newcost,score,rid,action));front[newcost]=(score,nr);heapq.heappush(queue,(score,newcost,nr))
    raise RuntimeError('no schedule within supplied upper bound')

def selftest():
    rows=[r for r in load(ROOT/'records/frontiers.json') if r['bound_method']=='exact-minimax']
    for r in rows:
        g=load(ROOT/f"benchmarks/graphs/{r['graph']}.json");c=solve(g,r['budget']);verify(g,c,r['budget']);assert c['claims']['peak_bytes']==r['peak_bytes']
    try:solve(g,0,max_labels=1)
    except RuntimeError:pass
    else:raise AssertionError('resource limit failed')
    print('PASS: dominance solver matches all 25 tiny exact optima and fails safely at a state limit',flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--selftest',action='store_true');p.add_argument('--graph');p.add_argument('--budget',type=int);p.add_argument('--max-labels',type=int,default=500000);a=p.parse_args()
    if a.selftest:selftest()
    if a.graph:
        g=load(ROOT/f'benchmarks/graphs/{a.graph}.json');r=next(r for r in load(ROOT/'records/frontiers.json') if r['graph']==a.graph and r['budget']==a.budget);t=time.perf_counter()
        try:
            c=solve(g,a.budget,a.max_labels,r['peak_bytes']);verify(g,c,a.budget)
            path=OUT/'bounds'/f'{a.graph}-b{a.budget}-dominance.json';path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(c,indent=2)+'\n')
            emit('dominance_bound',graph=a.graph,budget=a.budget,status='optimum',peak_bytes=c['claims']['peak_bytes'],object=str(path.relative_to(ROOT)),seconds=time.perf_counter()-t,**c['metadata'])
        except RuntimeError as e:emit('dominance_bound',graph=a.graph,budget=a.budget,status='resource_limit',reason=str(e),seconds=time.perf_counter()-t)
if __name__=='__main__':main()
