"""Replay an exact necessary-event bound and an unchanged legal witness."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import ortools

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(P))
from verifier import digest,load,verify
from compose_schedule import compose
from interval_relaxation import check_mapping,events,mapping,solve,transformer_pivots

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--record',action='store_true')
    args=parser.parse_args()
    assert ortools.__version__=='9.15.6755',ortools.__version__
    if not args.record:
        for name,want in load(P/'SOURCES.json')['sha256'].items():
            assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==want,name
    graph=load(ROOT/'benchmarks/graphs/transformer-b2-t64.json')
    assert digest(graph)=='49253c00a0941d94630e5323343af6e2d19e7317f26864fc19e01bc782bc638b'
    cases=[]
    for filename,cap,work in [('positive-witness.json',1245184,26869760),
                              ('middle-witness.json',851968,52035584)]:
        witness=load(P/filename)
        metrics=verify(graph,witness,witness['budget'])
        assert metrics['peak_bytes']==cap and metrics['recompute_cost']==work
        if filename=='middle-witness.json':
            actions,_=compose(graph,cap,witness['budget'],retained=[['b0_residual1']])
            assert actions==witness['actions'],'middle construction did not reproduce'
        pivots=transformer_pivots(graph)
        mapped=check_mapping(graph,pivots,cap,witness,True,True)
        assert mapped['mapped_interval_charge']==work
        hint=mapping(graph,events(graph,pivots,True)[0],witness)
        positive=solve(graph,pivots,cap,work,30,hint=hint,strategy='core',qk_backward_cut=True,persistent_allocations=True)
        assert positive['status']=='OPTIMAL' and positive['relaxation_work']==work,positive
        negative=solve(graph,pivots,cap,work-1,30,hint=hint,strategy='core',qk_backward_cut=True,persistent_allocations=True)
        assert negative['status']=='INFEASIBLE',negative
        cases.append(dict(witness=filename,metrics=metrics,mapping=mapped,positive=positive,negative=negative,
                          exact_minimum_additional_work=work,scope=f'fixed transformer-b2-t64 at peak{cap}; arbitrary earlier recomputation included'))
    result=dict(status='PASS',solver=ortools.__version__,graph_sha256=digest(graph),cases=cases,evidence='author-checked only')
    if args.record:
        (P/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',solver=ortools.__version__,cases=[dict(peak=c['metrics']['peak_bytes'],minimum_work=c['exact_minimum_additional_work'],positive=c['positive']['status'],negative=c['negative']['status']) for c in cases])),flush=True)

if __name__=='__main__':main()
