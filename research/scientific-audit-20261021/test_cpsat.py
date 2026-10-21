import random,unittest
from cpsat_compare import solve,exact,verify
class SolverTests(unittest.TestCase):
    def test_seeded_small_dags_against_enumeration(self):
        rng=random.Random(271828)
        for trial in range(8):
            nodes=[]
            for i in range(3+trial%3):
                available=['x']+[n['id'] for n in nodes]
                deps=rng.sample(available,rng.randrange(min(3,len(available))+1))
                name=f'n{i}';req=rng.sample(deps+[name],rng.randrange(len(deps)+2))
                nodes.append({'id':name,'deps':deps,'bytes':rng.randrange(1,9),'cost':rng.randrange(1,4),'backward_cost':1,'backward_requires':req,'recomputable':rng.random()>.25})
            used={d for n in nodes for d in n['deps']}
            g={'model':'activation-memory/v1','id':f'random-{trial}','inputs':[{'id':'x','bytes':2}],'nodes':nodes,'outputs':[n['id'] for n in nodes if n['id'] not in used]}
            for budget in (0,2):
                with self.subTest(trial=trial,budget=budget):
                    result,c=solve(g,budget,5);self.assertEqual(result['status'],'OPTIMAL')
                    self.assertEqual(result['peak_bytes'],exact(g,budget)['claims']['peak_bytes']);verify(g,c,budget)
    def test_horizon_cap_no_optimality_claim(self):
        g={'model':'activation-memory/v1','id':'limit','inputs':[{'id':'x','bytes':1}],'nodes':[{'id':'n','deps':['x'],'bytes':1,'cost':1,'backward_cost':1,'backward_requires':['x'],'recomputable':True}],'outputs':['n']}
        with self.assertRaises(ValueError):solve(g,1000)
if __name__=='__main__':unittest.main()
