"""Recompute bound claims; schedule verification alone cannot establish optimality."""
import json,time
from pathlib import Path
from dominance_exact import solve,ROOT,load,verify,selftest
OUT=Path(__file__).resolve().parent

def zero_bound(g):
    nodes={n['id']:n for n in g['nodes']};sizes={n['id']:n['bytes'] for n in g['inputs']+g['nodes']}
    inputs={n['id'] for n in g['inputs']};needed={x for n in g['nodes'] for x in n['backward_requires']}
    memo={}
    def ancestors(x):
        if x not in memo:
            memo[x]=set()
            for d in nodes.get(x,{}).get('deps',[]):memo[x]|={d}|ancestors(d)
        return memo[x]
    cuts=[('loss',inputs|needed|set(g['outputs']))]
    cuts += [(n['id'],inputs|(ancestors(n['id'])&needed)|set(n['deps'])|{n['id']}) for n in g['nodes']]
    name,live=max(cuts,key=lambda pair:sum(sizes[x] for x in pair[1]))
    return {'lower_bound':sum(sizes[x] for x in live),'witness_cut':name,'mandatory_live':sorted(live)}

def main():
    started=time.perf_counter();results=[];rows=load(OUT/'starting-frontier.json')
    selftest()
    for name,budget in [('resnet-b2-c32',0),('resnet-b2-c32',37847040),('resnet-b4-c32',0)]:
        row=next(r for r in rows if (r['graph'],r['budget'])==(name,budget));g=load(ROOT/f'benchmarks/graphs/{name}.json')
        c=solve(g,budget,500000,row['peak_bytes']);verify(g,c,budget)
        assert c['claims']['peak_bytes']==row['peak_bytes']
        results.append({'graph':name,'budget':budget,'lower_bound':row['peak_bytes'],'method':'exact-dominance','previous_lower_bound':row['lower_bound'],'optimal':True})
    for row in rows:
        if row['budget']!=0:continue
        g=load(ROOT/f"benchmarks/graphs/{row['graph']}.json");b=zero_bound(g)
        assert b['lower_bound']<=row['peak_bytes']
        if b['lower_bound']>row['lower_bound']:
            results.append({'graph':row['graph'],'budget':0,**b,'method':'zero-budget-mandatory-liveness','previous_lower_bound':row['lower_bound'],'optimal':b['lower_bound']==row['peak_bytes']})
    result={'status':'PASS','seconds':time.perf_counter()-started,'bounds':results,'newly_closed_cells':len({(r['graph'],r['budget']) for r in results if r['optimal']})}
    (OUT/'bound-results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
