#!/usr/bin/env python3
"""Minimal discrete Active Inference agent under v3-like metabolism/fatigue. No LLM, no VM."""
from __future__ import annotations
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json, math, random
from pathlib import Path

ACTIONS=('read','rest','look')
BINS=[(0,4),(5,12),(13,30),(31,60),(61,100)]
# preference over energy bins: dying is very bad, high is good
C=[-12.0,-4.0,1.0,4.0,7.0]
ALPHA=0.15; BETA=1.2; GAMMA=0.9; HORIZON=2; TEMP=0.35
START=12.0; TICKS=30

def eb(e):
 for i,(lo,hi) in enumerate(BINS):
  if lo<=e<=hi: return i
 return 4 if e>100 else 0

def ent(p):
 return -sum(x*math.log(max(x,1e-12)) for x in p if x>0)

class MiniAIF:
 def __init__(self,seed):
  self.rng=random.Random(seed)
  self.counts={a:[[0.0]*len(BINS) for _ in BINS] for a in ACTIONS}
  self.read_streak=0; self.rest_streak=0
  self.last_a=None; self.last_s=None
 def trans(self,a,s):
  row=self.counts[a][s]; z=sum(row)+ALPHA*len(BINS)
  return [(row[j]+ALPHA)/z for j in range(len(BINS))]
 def update(self,a,s,s2):
  self.counts[a][s][s2]+=1.0
 def val(self,s,h):
  if h<=0: return 0.0
  best=-1e9
  for a in ACTIONS:
   p=self.trans(a,s); pref=sum(p[j]*C[j] for j in range(len(BINS)))
   ep=BETA*ent(p)
   fut=sum(p[j]*self.val(j,h-1) for j in range(len(BINS)))
   best=max(best,pref+ep+GAMMA*fut)
  return best
 def scores(self,s):
  out={}
  for a in ACTIONS:
   p=self.trans(a,s); pref=sum(p[j]*C[j] for j in range(len(BINS)))
   ep=BETA*ent(p)
   fut=sum(p[j]*self.val(j,HORIZON-1) for j in range(len(BINS)))
   out[a]=pref+ep+GAMMA*fut
  return out
 def act(self,s):
  sc=self.scores(s)
  # softmax over scores
  mx=max(sc.values()); ws={a:math.exp((v-mx)/TEMP) for a,v in sc.items()}
  z=sum(ws.values()); r=self.rng.random(); acc=0
  for a in ACTIONS:
   acc+=ws[a]/z
   if r<=acc: return a,sc
  return ACTIONS[-1],sc

def step(env,a):
 e=env['energy']; rs=env['read_streak']; ts=env['rest_streak']
 e-=2.0  # base metabolism
 if e<=0:
  env.update(energy=0,read_streak=rs,rest_streak=ts,dead=True); return
 if a=='read':
  gain=[10,6,3,0,-2][min(rs,4)]; e+=gain; rs+=1; ts=0
 elif a=='rest':
  gain=[10,6,3,0,-2][min(ts,4)]; e+=gain; ts+=1; rs=0
 elif a=='look':
  e-=2.0; rs=0; ts=0
 e=max(0,min(100,e))
 env.update(energy=e,read_streak=rs,rest_streak=ts,dead=e<=0)

def run(seed,ticks=TICKS,verbose=False):
 a=MiniAIF(seed); env={'energy':START,'read_streak':0,'rest_streak':0,'dead':False}
 rows=[]
 for t in range(1,ticks+1):
  s=eb(env['energy']); action,sc=a.act(s)
  before=env['energy']; step(env,action); after=env['energy']
  s2=eb(after); a.update(action,s,s2)
  row={'tick':t,'state_bin':s,'action':action,'energy_before':before,'energy_after':after,
       'read_streak':env['read_streak'],'rest_streak':env['rest_streak'],'dead':env['dead'],
       'scores':{k:round(v,3) for k,v in sc.items()}}
  rows.append(row)
  if verbose: print(row)
  if env['dead']: break
 return {'seed':seed,'rows':rows,'survival':len(rows),'final_energy':env['energy'],
         'dead':env['dead'],'actions':{x:sum(1 for r in rows if r['action']==x) for x in ACTIONS}}

if __name__=='__main__':
 out=[run(s,verbose=(s==1)) for s in range(1,11)]
 Path(str(_HERE / 'mini_aif_result.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('\nSUMMARY')
 for r in out:
  print(r['seed'],'surv',r['survival'],'E',r['final_energy'],'dead',r['dead'],r['actions'])
 print('saved mini_aif_result.json')
