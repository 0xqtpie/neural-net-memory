"""Check pins, rebuild the winning policy and verify the full fixed-graph trace."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
sys.path[:0]=[str(ROOT),str(P)]
from verifier import load,verify,digest
from search import certificate
from cache_policy import construct,WINNING_POLICY,GRAPH_SHA256

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--record',action='store_true');args=parser.parse_args()
    if not args.record:
        for name,want in load(P/'SOURCES.json')['sha256'].items():
            assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==want,name
    graph=load(ROOT/'benchmarks/graphs/transformer-b4-t128.json');assert digest(graph)==GRAPH_SHA256
    saved=load(P/'certificates/transformer-b4-t128-cap11.json')
    metrics=verify(graph,saved,956301312)
    actions=construct(graph)
    assert actions==saved['actions'],'constructor changed the pinned action trace'
    rebuilt=certificate(graph,actions,956301312,'pdb-marginal-cache-secondary',dict(global_optimal=False,policy=WINNING_POLICY))
    assert metrics==rebuilt['claims']
    assert metrics['peak_bytes']==1441792 and metrics['recompute_cost']==702349312
    result=dict(status='PASS',graph_sha256=digest(graph),claims=metrics,action_trace_reconstructed=True,evidence='author-checked only',global_optimal=False)
    if args.record:(P/'VERIFY.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
if __name__=='__main__':main()
