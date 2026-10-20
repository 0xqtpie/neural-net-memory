import sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from cache_search import probe
from trial_search import OUT,START,load,emit
plan=load(OUT/'TRIAL.json')
# Same precommitted transfer order, 1,000 sampled policies per graph.
for i,name in enumerate(plan['transfer_order']):
    if time.time()>=START+1260:break
    probe(name,int(plan['seed'][24:],16)+i,1000,90)
emit('cache_transfer_finished')
