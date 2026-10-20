#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from trial_search import Campaign,load,OUT,START,emit
import time
plan=load(OUT/'TRIAL.json')
for i,name in enumerate(plan['transfer_order']):
    if time.time()>START+1200:break
    seed=int(plan['seed'][16:24],16)+i
    Campaign(name,seed,'trial-transfer-regions').run(5000,'regions',min(time.time()+100,START+1200))
    if time.time()>START+1200:break
    Campaign(name,seed+100,'trial-transfer-order').run(4000,'order',min(time.time()+100,START+1200))
emit('transfer_finished')
