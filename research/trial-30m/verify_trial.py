#!/usr/bin/env python3
"""Verify trial witnesses, untouched baseline, chronology, and parameter replay."""
import argparse,hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(Path(__file__).resolve().parent))
from verifier import load,verify,require
from search import checkpoint_schedule
OUT=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--reconstruct',action='store_true');args=p.parse_args();started=time.perf_counter()
    t=load(OUT/'TRIAL.json');require(sha(ROOT/'records/frontiers.json')==t['frontier_sha256'],'official frontier was modified')
    require(sha(OUT/'starting-frontier.json')==t['frontier_sha256'],'starting frontier changed')
    baseline={(r['graph'],r['budget']):r for r in load(OUT/'starting-frontier.json')}
    candidates=load(OUT/'candidates.json');require(len({(r['graph'],r['budget']) for r in candidates})==len(candidates),'duplicate candidate rows')
    total=0;actions=0
    for path in sorted((OUT/'certificates').glob('*.json')):
        c=load(path);key=(c['graph_id'],c['budget']);require(key in baseline,'not a frozen challenge')
        g=load(ROOT/f"benchmarks/graphs/{key[0]}.json");metrics=verify(g,c,key[1]);total+=1;actions+=len(c['actions'])
        require(metrics['peak_bytes']<baseline[key]['peak_bytes'],'not a strict initial-record improvement')
        require(metrics['peak_bytes']>=baseline[key]['lower_bound'],'witness contradicts existing bound')
    for row in candidates:
        path=(ROOT/row['object']).resolve();require(path.is_relative_to(OUT/'certificates'),'candidate path escapes certificate directory')
        require(sha(path)==row['sha256'],'candidate SHA mismatch');c=load(path)
        require(c['graph_id']==row['graph'] and c['budget']==row['budget'],'candidate identity mismatch')
        g=load(ROOT/f"benchmarks/graphs/{row['graph']}.json");metrics=verify(g,c,row['budget'])
        require(row['peak_bytes']==metrics['peak_bytes'] and row['recompute_cost']==metrics['recompute_cost'],'candidate metric mismatch')
        require(row['starting_peak']==baseline[row['graph'],row['budget']]['peak_bytes'],'wrong comparison baseline')
        if args.reconstruct:
            m=c['metadata']
            if c['method']=='trial-adaptive-cache':
                from cache_search import Cache
                actual=Cache(g,m['cap'],m['budget'],m['alpha'],m['beta'],m['bonus'],m['keepers'],m['order']).run()
            elif c['method']=='trial-earliest-free':
                from lifetimes import shorten
                source=ROOT/m['source'];require(sha(source)==m['source_sha256'],'source witness changed');actual=shorten(g,load(source)['actions'])
            else:
                order=m.get('order');gg=dict(g,nodes=[g['nodes'][i] for i in order]) if order else g
                ids=[n['id'] for n in gg['nodes']];cuts=m.get('cuts',[]);groups=[]
                if cuts:
                    boundaries=[0]+sorted(cuts)+[len(ids)];groups=[ids[a:b] for a,b in zip(boundaries,boundaries[1:])]
                actual=checkpoint_schedule(gg,m['checkpoints'],groups,m.get('save_final',False))
            require(actual==c['actions'],f"parameter replay differs: {row['object']}")
    events=[json.loads(line) for line in (OUT/'events.jsonl').read_text().splitlines()]
    previous=-1;improvements=[]
    for event in events:
        require(event['elapsed_seconds']>=previous,'nonmonotone event timeline');previous=event['elapsed_seconds']
        if event['event']=='verified_improvement':
            require(event['elapsed_seconds']<=t['wall_budget_seconds'],'result outside trial budget')
            path=ROOT/event['object'];require(sha(path)==event['sha256'],'historical event certificate changed')
            require(event['peak_bytes']<event['previous_trial_peak'],'non-improvement logged as a win')
            improvements.append(event)
    for row in candidates:
        matching=[e for e in improvements if (e['graph'],e['budget'])==(row['graph'],row['budget'])]
        require(matching and min(e['peak_bytes'] for e in matching)==row['peak_bytes'],'winner not best logged result')
    print(json.dumps({'status':'PASS','improved_cells':len(candidates),'graphs':len({r['graph'] for r in candidates}),'historical_certificates':total,'verified_actions':actions,'record_events':len(improvements),'reconstructed_winners':len(candidates) if args.reconstruct else 0,'seconds':time.perf_counter()-started},sort_keys=True))
if __name__=='__main__':main()
