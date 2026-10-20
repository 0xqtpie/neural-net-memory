#!/usr/bin/env python3
"""Trial-only memory-capped replay with cost/size/next-use eviction heuristics."""
import argparse,hashlib,json,math,random,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from verifier import load,simulate,verify
from search import certificate
sys.path.insert(0,str(Path(__file__).resolve().parent))
from trial_search import OUT,START,emit,elapsed,incumbent_rows
from lifetimes import admit

class Failed(Exception):pass

class Cache:
    def __init__(self,g,cap,budget,alpha,beta,bonus,keepers,order=None):
        self.g=g;self.nodes={n['id']:n for n in g['nodes']};self.ids=list(self.nodes)
        self.order=order or self.ids;self.cap=cap;self.budget=budget
        self.alpha=alpha;self.beta=beta;self.bonus=bonus;self.keepers=set(keepers)
        self.sizes={n['id']:n['bytes'] for n in g['inputs']+g['nodes']}
        self.live={n['id'] for n in g['inputs']};self.seen=set();self.spent=0;self.actions=[]
        self.requests=[('forward',n) for n in self.order]+[('loss',None)]+[('backward',n) for n in reversed(self.order)]
        self.index=0
        self.closures={};self.direct=[]
        def closure(name):
            if name not in self.closures:
                value={name}
                for dep in self.nodes.get(name,{}).get('deps',[]):value|=closure(dep)
                self.closures[name]=value
            return self.closures[name]
        for name in self.ids:closure(name)
        for op,n in self.requests:
            self.direct.append(set(self.nodes[n]['deps']) if op=='forward' else set(self.nodes[n]['backward_requires']) if op=='backward' else set(g['outputs']))
        self.future=[]
        for i in range(len(self.requests)):
            needed=set()
            for targets in self.direct[i:]:
                for n in targets:needed|=closure(n)
            self.future.append(needed)
        self.future.append(set())
    def emit(self,op,name=None):
        self.actions.append({'op':op,**({'node':name} if name is not None else {})})
        if op=='forward':
            if name in self.seen:self.spent+=self.nodes[name]['cost']
            self.seen.add(name);self.live.add(name)
            if self.spent>self.budget:raise Failed('budget')
        elif op=='drop':self.live.remove(name)
    def recovery(self,name):
        visited=set()
        def walk(n,root=False):
            if n in visited or (n in self.live and not root) or n not in self.nodes:return 0
            visited.add(n)
            return self.nodes[n]['cost']+sum(walk(d) for d in self.nodes[n]['deps'])
        return walk(name,True)
    def score(self,name):
        distance=len(self.requests)+1
        for i in range(self.index,len(self.requests)):
            if name in self.direct[i]:distance=i-self.index+1;break
        value=(self.recovery(name)**self.alpha)/(self.sizes[name]*(distance**self.beta))
        if name in self.keepers:value*=self.bonus
        return value
    def reserve(self,amount,protected):
        while sum(self.sizes[x] for x in self.live)+amount>self.cap:
            choices=[n for n in self.ids if n in self.live and n not in protected and self.nodes[n]['recomputable']]
            if not choices:raise Failed('protected allocation exceeds cap')
            dead=[n for n in choices if n not in self.future[self.index]]
            victim=dead[0] if dead else min(choices,key=lambda n:(self.score(n),n))
            self.emit('drop',victim)
    def ensure(self,name,protected):
        if name in self.live:return
        if name not in self.nodes:raise Failed('missing external input')
        if name in self.seen and not self.nodes[name]['recomputable']:raise Failed('non-recomputable')
        held=set(protected)
        for dep in self.nodes[name]['deps']:
            self.ensure(dep,held);held.add(dep)
        self.reserve(self.sizes[name],held)
        self.emit('forward',name)
    def run(self):
        for self.index,(op,name) in enumerate(self.requests):
            if op=='forward':self.ensure(name,set())
            else:
                held=set()
                for target in sorted(self.direct[self.index]):
                    self.ensure(target,held);held.add(target)
                self.emit(op,name)
            for n in self.ids:
                if n in self.live and n not in self.future[self.index+1]:self.emit('drop',n)
        return self.actions

def probe(name,seed,iterations,seconds):
    g=load(ROOT/f'benchmarks/graphs/{name}.json');rng=random.Random(seed)
    rows=[r for r in load(OUT/'starting-frontier.json') if r['graph']==name and not r['optimal']]
    unit=math.gcd(*(n['bytes'] for n in g['nodes']+g['inputs']))
    pools=[]
    for p in sorted((ROOT/f'certificates/search/{name}').glob('*.json')):pools.append(load(p)['metadata']['checkpoints'])
    for p in sorted((OUT/'certificates').glob(f'{name}-*.json')):
        m=load(p)['metadata']
        if 'checkpoints' in m:pools.append(m['checkpoints'])
    deadline=min(time.time()+seconds,START+1560);attempts=[]
    emit('cache_start',graph=name,seed=seed,iterations=iterations)
    for it in range(iterations):
        if time.time()>=deadline:break
        row=rng.choice([r for r in rows if r['budget']>0]);current=incumbent_rows()[name,row['budget']]
        if current['peak_bytes']<=row['lower_bound']:continue
        upper=(current['peak_bytes']-unit)//unit;lower=(row['lower_bound']+unit-1)//unit
        cap=unit*(upper if rng.random()<.8 else rng.randint(lower,upper))
        alpha=rng.choice([0.,.5,1.,1.5]);beta=rng.choice([0.,.5,1.,2.]);bonus=rng.choice([1.,2.,4.,16.])
        keep=rng.choice(pools) if pools and rng.random()<.75 else []
        order=[n['id'] for n in g['nodes']]
        if rng.random()<.5:
            for node in g['nodes']:
                if node['id'].endswith('_v'):
                    target=node['id'][:-1]+'probs'
                    if target in order:order.remove(node['id']);order.insert(order.index(target)+1,node['id'])
        params={'cap':cap,'budget':row['budget'],'alpha':alpha,'beta':beta,'bonus':bonus,'keepers':keep,'order':order,'seed':seed,'iteration':it}
        try:
            actions=Cache(g,cap,row['budget'],alpha,beta,bonus,keep,order).run()
            c=certificate(g,actions,row['budget'],'trial-adaptive-cache',params)
            assert c['claims']['peak_bytes']<=cap
            improved=admit(g,c,c['method'],params)
            attempts.append({'iteration':it,'status':'legal','peak':c['claims']['peak_bytes'],'cost':c['claims']['recompute_cost'],'improved':improved,**params})
        except Failed as e:attempts.append({'iteration':it,'status':'infeasible-policy','reason':str(e),**params})
        if (it+1)%100==0:emit('cache_progress',graph=name,attempts=it+1,legal=sum(a['status']=='legal' for a in attempts))
    (OUT/f'cache-attempts-{name}-{seed}.json').write_text(json.dumps(attempts,indent=2)+'\n')
    emit('cache_end',graph=name,attempts=len(attempts),legal=sum(a['status']=='legal' for a in attempts),improvements=sum(a.get('improved',False) for a in attempts))

def main():
    p=argparse.ArgumentParser();p.add_argument('--graph',required=True);p.add_argument('--seed',type=int,default=20261020);p.add_argument('--iterations',type=int,default=1000);p.add_argument('--seconds',type=float,default=120);a=p.parse_args();probe(a.graph,a.seed,a.iterations,a.seconds)
if __name__=='__main__':main()
