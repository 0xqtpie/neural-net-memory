#!/usr/bin/env python3
"""Move each explicit value lifetime's free immediately after its last read."""
import hashlib,json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from verifier import load,verify
from search import certificate
sys.path.insert(0,str(Path(__file__).resolve().parent))
from trial_search import OUT,elapsed,emit,incumbent_rows

def shorten(g,actions):
    nodes={n['id']:n for n in g['nodes']};last={};ends=[]
    for i,a in enumerate(actions):
        op=a['op'];name=a.get('node')
        reads=nodes[name]['deps'] if op=='forward' else nodes[name]['backward_requires'] if op=='backward' else g['outputs'] if op=='loss' else []
        for v in reads:
            if v in nodes:last[v]=i
        if op=='forward':last[name]=i
        elif op=='drop':ends.append((last.pop(name),name))
    ends.extend((i,n) for n,i in last.items())
    drops={}
    for i,n in ends:drops.setdefault(i,[]).append(n)
    result=[]
    for i,a in enumerate(actions):
        if a['op']=='drop':continue
        result.append(a)
        result.extend({'op':'drop','node':n} for n in sorted(drops.get(i,[])))
    return result

def admit(g,c,method,metadata):
    acts=c['actions'];b=c['budget'];current=incumbent_rows();old=current[g['id'],b]
    candidate=certificate(g,acts,b,method,metadata)
    if candidate['claims']['peak_bytes']>=old['peak_bytes']:return False
    peak=candidate['claims']['peak_bytes'];p=OUT/'certificates'/f"{g['id']}-b{b}-p{peak}.json";p.parent.mkdir(exist_ok=True);p.write_text(json.dumps(candidate,indent=2)+'\n')
    check=subprocess.run([sys.executable,str(ROOT/'verifier.py'),str(ROOT/f"benchmarks/graphs/{g['id']}.json"),str(p),'--budget',str(b)],check=True,capture_output=True,text=True)
    verify(g,candidate,b)
    start=next(r for r in load(OUT/'starting-frontier.json') if (r['graph'],r['budget'])==(g['id'],b))
    row={'graph':g['id'],'budget':b,'peak_bytes':peak,'recompute_cost':candidate['claims']['recompute_cost'],'object':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'starting_peak':start['peak_bytes'],'previous_trial_peak':old['peak_bytes'],'verified_at_seconds':elapsed(),'method':method,'metadata':metadata}
    allrows=load(OUT/'candidates.json') if (OUT/'candidates.json').exists() else []
    allrows=[r for r in allrows if (r['graph'],r['budget'])!=(g['id'],b)]+[row]
    (OUT/'candidates.json').write_text(json.dumps(sorted(allrows,key=lambda r:(r['graph'],r['budget'])),indent=2)+'\n')
    emit('verified_improvement',**row,checker_stdout=check.stdout.strip());return True

def main():
    trials=[]
    for row in list(incumbent_rows().values()):
        source=ROOT/row['object'];c=load(source);g=load(ROOT/f"benchmarks/graphs/{row['graph']}.json")
        actions=shorten(g,c['actions'])
        new=certificate(g,actions,row['budget'],'trial-earliest-free',{'source':row['object'],'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source_method':c['method']})
        improved=admit(g,new,new['method'],new['metadata'])
        trials.append({'graph':row['graph'],'budget':row['budget'],'before':c['claims']['peak_bytes'],'after':new['claims']['peak_bytes'],'improved':improved})
    (OUT/'lifetime-sweep.json').write_text(json.dumps(trials,indent=2)+'\n')
    emit('lifetime_sweep',tested=len(trials),improved=sum(r['improved'] for r in trials))
if __name__=='__main__':main()
