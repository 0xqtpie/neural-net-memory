"""Final deterministic refinement; all tested parameters retained for audit."""
import json,random,time
from cache_search import Cache,Failed,ROOT,OUT,START,load,certificate,admit,emit,incumbent_rows
seed=2551017556;rng=random.Random(seed);name='transformer-b4-t128';budget=956301312
g=load(ROOT/f'benchmarks/graphs/{name}.json');ids=[n['id'] for n in g['nodes']]
base=load(ROOT/incumbent_rows()[name,budget]['object'])['metadata'];attempts=[]
emit('focused_start',graph=name,seed=seed)
for i in range(4000):
    if time.time()>=START+1560:break
    cur=incumbent_rows()[name,budget];cap=cur['peak_bytes']-131072
    if cap<1179648:break
    keep=set(base['keepers'])
    for _ in range(rng.choice([1,1,2,3,5])):
        n=rng.choice(ids)
        if n in keep:keep.remove(n)
        else:keep.add(n)
    order=list(base['order'])
    if rng.random()<.3:
        for b in range(4):
            v=f'b{b}_v'
            if rng.random()<.5:order.remove(v);order.insert(order.index(f'b{b}_scores'),v)
    p=dict(cap=cap,budget=budget,alpha=rng.choice([.5,1.,1.,1.5]),beta=rng.choice([1.,1.5,2.,2.,3.]),bonus=rng.choice([4.,8.,16.,16.,32.]),keepers=sorted(keep),order=order,seed=seed,iteration=i)
    try:
        actions=Cache(g,**{k:v for k,v in p.items() if k not in ['seed','iteration']}).run()
        c=certificate(g,actions,budget,'trial-adaptive-cache',p)
        improved=admit(g,c,c['method'],p)
        attempts.append(dict(**p,status='legal',peak=c['claims']['peak_bytes'],cost=c['claims']['recompute_cost'],improved=improved))
        if improved:base=p
    except Failed as e:attempts.append(dict(**p,status='infeasible-policy',reason=str(e)))
(OUT/'focused-attempts.json').write_text(json.dumps(attempts,indent=2)+'\n')
emit('focused_end',attempts=len(attempts),legal=sum(a['status']=='legal' for a in attempts),improvements=sum(a.get('improved',False) for a in attempts))
