import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(Path(__file__).resolve().parent))
from generate import synthetic
from search import baseline_candidates
from verifier import simulate
from lifetimes import shorten
from cache_search import Cache,Failed
class TrialTests(unittest.TestCase):
    def test_lifetime_preserves_cost_and_never_worsens_memory(self):
        for g in synthetic():
            for name,a in baseline_candidates(g):
                before=simulate(g,a,10000);after=simulate(g,shorten(g,a),10000)
                self.assertLessEqual(after['peak_bytes'],before['peak_bytes'])
                for k in ['recompute_cost','forward_cost','backward_cost']:self.assertEqual(after[k],before[k])
    def test_exact_dominance_and_zero_bound_randomized(self):
        import random
        from generate import node,graph
        from search import exact
        from dominance_exact import solve
        from check_bounds import zero_bound
        rng=random.Random(20261020)
        for case in range(30):
            ns=[];available=['x']
            for i in range(5):
                name=f'n{i}';deps=rng.sample(available,rng.randint(1,min(2,len(available))))
                req=rng.choice([deps,[name],[]])
                ns.append(node(name,deps,rng.randint(1,8),rng.randint(1,4),req=req,recomputable=rng.random()>.2));available.append(name)
            g=graph(f'random-{case}',ns,1,'synthetic',{'source':'test-only seeded graph'})
            for budget in [0,3,10]:
                reference=exact(g,budget,max_states=100000)
                actual=solve(g,budget,max_labels=100000)
                self.assertEqual(reference['claims']['peak_bytes'],actual['claims']['peak_bytes'])
                if budget==0:self.assertLessEqual(zero_bound(g)['lower_bound'],reference['claims']['peak_bytes'])
    def test_cache_results_obey_cap_and_budget(self):
        legal=0;failed=0
        for g in synthetic():
            total=sum(n['cost'] for n in g['nodes'])
            maxmem=sum(n['bytes'] for n in g['nodes']+g['inputs'])
            for budget in [0,1,total,2*total]:
                for cap in range(1,maxmem+1):
                    try:a=Cache(g,cap,budget,1.,1.,1.,[]).run()
                    except Failed:failed+=1;continue
                    m=simulate(g,a,budget);self.assertLessEqual(m['peak_bytes'],cap);legal+=1
        self.assertGreater(legal,10);self.assertGreater(failed,10)
if __name__=='__main__':unittest.main()
