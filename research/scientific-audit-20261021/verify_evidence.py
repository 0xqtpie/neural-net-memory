#!/usr/bin/env python3
"""Stdlib replay of stored certificate, graph and comparison identities."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT))
from verifier import load,verify,digest

def main():
    audit=load(HERE/'export-audit.json');graph=load(HERE/'graph.json')
    assert digest(graph)==audit['graph_sha256']
    result=load(HERE/'solver-results.json');count=0
    for row in result['runs']:
        g=graph if row['graph']==graph['id'] else load(ROOT/f"benchmarks/graphs/{row['graph']}.json")
        cert=load(ROOT/row['certificate']);metrics=verify(g,cert,row['budget'])
        assert metrics['peak_bytes']==row['peak_bytes']==row['reference_exact_peak_bytes']==row['best_bound_bytes']
        assert row['status']=='OPTIMAL';assert all(metrics[k]==row[k] for k in metrics);count+=1
    assert count==18
    assert audit['distinct_contiguous_activation_storages'] and audit['direct_matrix_calculus_gradients_match']
    assert audit['hooked_vs_unhooked_gradients_exact']
    print(json.dumps({'status':'PASS','certificates':count,'scope':'Witness validation and receipt consistency; rerun solvers/exporter to reproduce optimality and workload observations.'}))
if __name__=='__main__':main()
