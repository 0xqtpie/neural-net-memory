#!/usr/bin/env python3
"""Trial-only checkpoint population search. Never changes official records."""
import argparse,hashlib,json,random,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from verifier import load,simulate,verify
from search import certificate,checkpoint_schedule
OUT=Path(__file__).resolve().parent
START=datetime.fromisoformat(load(OUT/'TRIAL.json')['started_at'].replace('Z','+00:00')).timestamp()

def elapsed():return time.time()-START

def emit(kind,**data):
    value={'event':kind,'elapsed_seconds':round(elapsed(),3),'utc':datetime.now(timezone.utc).isoformat(),**data}
    with (OUT/'events.jsonl').open('a') as f:f.write(json.dumps(value,sort_keys=True)+'\n')
    print(json.dumps(value,sort_keys=True),flush=True)

def incumbent_rows():
    rows=load(OUT/'starting-frontier.json')
    p=OUT/'candidates.json'
    current={ (r['graph'],r['budget']):r for r in rows }
    if p.exists():
        for r in load(p):
            if r['peak_bytes']<current[r['graph'],r['budget']]['peak_bytes']:current[r['graph'],r['budget']]=r
    return current

class Campaign:
    def __init__(self,graph,seed,method):
        self.g=load(ROOT/f'benchmarks/graphs/{graph}.json');self.graph=graph
        self.rows=[r for r in load(OUT/'starting-frontier.json') if r['graph']==graph]
        self.ns=self.g['nodes'];self.ids=[n['id'] for n in self.ns];self.n=len(self.ids)
        self.rng=random.Random(seed);self.seed=seed;self.method=method;self.evaluated=0
        self.limit=sum(n['cost'] for n in self.ns)*(self.n+1)**2
        self.current=incumbent_rows();self.pool={r['budget']:[] for r in self.rows};self.tried=set()
        self.top={r['budget']:float('inf') for r in self.rows}
        self.counter=0
    def evaluate(self,keepers,cuts=(),save_final=False,order=None):
        key=(tuple(sorted(keepers)),tuple(sorted(cuts)),save_final,tuple(order) if order else None)
        if key in self.tried:return
        self.tried.add(key)
        graph=self.g
        if order:
            graph=dict(graph,nodes=[self.ns[i] for i in order])
        ids=[n['id'] for n in graph['nodes']]
        groups=[]
        if cuts:
            boundaries=[0]+sorted(cuts)+[self.n]
            groups=[ids[a:b] for a,b in zip(boundaries,boundaries[1:])]
        acts=checkpoint_schedule(graph,set(keepers),groups,save_final)
        metrics=simulate(self.g,acts,self.limit);self.evaluated+=1
        cost,peak=metrics['recompute_cost'],metrics['peak_bytes']
        for row in self.rows:
            b=row['budget']
            if cost>b:continue
            if peak<self.top[b]:
                self.top[b]=peak
                self.pool[b]=[x for x in self.pool[b] if x[0]<=peak+max(n['bytes'] for n in self.ns)]
            # Preserve diverse equal-score states and a small near-best band.
            if peak<=self.top[b]+max(n['bytes'] for n in self.ns):
                self.pool[b].append((peak,cost,key))
                self.pool[b].sort(key=lambda x:(x[0],x[1]))
                if len(self.pool[b])>120:
                    # Keep elites; sample plateau/near-best alternatives, not just min-cost ties.
                    elite=self.pool[b][:12];tail=self.pool[b][12:]
                    self.pool[b]=elite+self.rng.sample(tail,108)
            current=self.current[(self.graph,b)]
            if peak<current['peak_bytes']:
                c=certificate(self.g,acts,b,self.method,{'seed':self.seed,'evaluation':self.evaluated,'checkpoints':sorted(keepers),'cuts':sorted(cuts),'save_final':save_final,'order':order,'optimal':False})
                path=OUT/'certificates'/f'{self.graph}-b{b}-p{peak}.json';path.parent.mkdir(exist_ok=True)
                path.write_text(json.dumps(c,indent=2)+'\n')
                # Fresh process, authoritative graph path and challenge budget.
                checked=subprocess.run([sys.executable,str(ROOT/'verifier.py'),str(ROOT/f'benchmarks/graphs/{self.graph}.json'),str(path),'--budget',str(b)],capture_output=True,text=True,check=True)
                verify(self.g,c,b)
                new={'graph':self.graph,'budget':b,'peak_bytes':peak,'recompute_cost':cost,'object':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'starting_peak':row['peak_bytes'],'previous_trial_peak':current['peak_bytes'],'verified_at_seconds':elapsed(),'method':self.method,'seed':self.seed,'evaluation':self.evaluated}
                self.current[(self.graph,b)]=new
                old=load(OUT/'candidates.json') if (OUT/'candidates.json').exists() else []
                old=[r for r in old if (r['graph'],r['budget'])!=(self.graph,b)]+[new]
                (OUT/'candidates.json').write_text(json.dumps(sorted(old,key=lambda r:(r['graph'],r['budget'])),indent=2)+'\n')
                emit('verified_improvement',**new,checker_stdout=checked.stdout.strip())
    def initialize(self):
        for path in sorted((ROOT/f'certificates/search/{self.graph}').glob('*.json')):
            self.evaluate(load(path)['metadata']['checkpoints'])
        for r in self.rows:
            c=load(ROOT/r['object']);kept=set()
            for a in c['actions']:
                if a['op']=='loss':break
                if a['op']=='forward':kept.add(a['node'])
                elif a['op']=='drop':kept.remove(a['node'])
            self.evaluate(kept)
        for p in sorted((OUT/'certificates').glob(f'{self.graph}-*.json')) if (OUT/'certificates').exists() else []:
            m=load(p)['metadata'];self.evaluate(m['checkpoints'],m.get('cuts',()),m.get('save_final',False),m.get('order'))
    def run(self,iterations,mode,deadline):
        emit('search_start',graph=self.graph,seed=self.seed,mode=mode,iterations=iterations)
        self.initialize();started=time.monotonic()
        for it in range(iterations):
            if time.time()>=deadline:break
            budgets=[b for b,p in self.pool.items() if p and b>0]
            if not budgets:break
            b=self.rng.choice(budgets);pool=self.pool[b]
            if self.rng.random()<.6:
                peak,cost,key=self.rng.choice(pool[:min(20,len(pool))])
            else:peak,cost,key=self.rng.choice(pool)
            keep=set(key[0]);cuts=set(key[1]);final=key[2];order=key[3]
            if mode=='regions':
                if self.rng.random()<.65:
                    for i in self.rng.sample(range(1,self.n),self.rng.randint(1,min(4,self.n-1))):cuts.symmetric_difference_update({i})
                else:
                    for x in self.rng.sample(self.ids,self.rng.randint(1,min(3,self.n))):keep.symmetric_difference_update({x})
                if self.rng.random()<.1:final=not final
            else:
                # Singles, swaps, multibit kicks and occasional fresh checkpoints.
                u=self.rng.random()
                if u<.45:keep.symmetric_difference_update({self.rng.choice(self.ids)})
                elif u<.75:
                    for x in self.rng.sample(self.ids,2):keep.symmetric_difference_update({x})
                elif u<.95:
                    for x in self.rng.sample(self.ids,self.rng.randint(3,min(8,self.n))):keep.symmetric_difference_update({x})
                else:
                    p=self.rng.random();keep={x for x in self.ids if self.rng.random()<p}
            self.evaluate(keep,cuts,final,order)
            if (it+1)%500==0:emit('progress',graph=self.graph,mode=mode,iteration=it+1,evaluated=self.evaluated,best=self.top)
        emit('search_end',graph=self.graph,seed=self.seed,mode=mode,evaluated=self.evaluated,tried=len(self.tried),runtime_seconds=time.monotonic()-started)

def main():
    p=argparse.ArgumentParser();p.add_argument('--graph',required=True);p.add_argument('--seed',type=int,required=True);p.add_argument('--iterations',type=int,default=5000);p.add_argument('--mode',choices=['plateau','regions'],default='plateau');p.add_argument('--seconds',type=float,default=240);a=p.parse_args()
    c=Campaign(a.graph,a.seed,'trial-'+a.mode)
    c.run(a.iterations,a.mode,min(time.time()+a.seconds,START+1560))
if __name__=='__main__':main()
