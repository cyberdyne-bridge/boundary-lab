#!/usr/bin/env python3
"""P2.1g: four-way ablation: risk prediction x attribution."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json,math,random
from pathlib import Path

OUT=Path(str(_HERE / 'p2_1g_reckless_result.json'))
ACTS=('read','rest','look'); BINS=[(0,4),(5,12),(13,30),(31,60),(61,100)]
CSTATE=[-12.0,-4.0,1.0,4.0,7.0]; BETA=1.0
EFFECT={'read':-10.0,'rest':6.0,'look':0.0}
START=30.0; TICKS=30

def eb(e):
 for i,(lo,hi) in enumerate(BINS):
  if lo<=e<=hi: return i
 return 4 if e>100 else 0

def ent(p): return -sum(x*math.log(max(x,1e-12)) for x in p if x>0)

class EFE:
 def __init__(self,seed,risk):
  self.rng=random.Random(seed); self.n=len(BINS); self.risk=risk
  self.counts={a:[[0.0]*self.n for _ in range(self.n)] for a in ACTS}
  self.read_c=10.0; self.rest_c=3.0; self.look_c=0.0
  self.guard=0; self.updates=[]
 def trans(self,a,s):
  row=self.counts[a][s]; z=sum(row)+0.2*self.n
  return [(row[j]+0.2)/z for j in range(self.n)]
 def update(self,a,s,s2): self.counts[a][s][s2]+=1.0
 def scores(self,e,s):
  if self.risk:
   lam=0.5+max(0.0,30.0-e)*0.08
   read_c=self.read_c-10.0*lam
   if e<20.0: read_c-=100.0; self.guard+=1
   rest_c=self.rest_c
   if e>80.0: rest_c-=20.0
  else:
   read_c=10.0; rest_c=3.0; self.guard+=0
  ca={'read':read_c,'rest':rest_c,'look':self.look_c}
  out={}
  for a in ACTS:
   p=self.trans(a,s); util=ca[a]+sum(p[j]*CSTATE[j] for j in range(self.n))
   out[a]=util+BETA*ent(p)
  return out,ca
 def act(self,e,s):
  sc,ca=self.scores(e,s); return max(ACTS,key=lambda a:sc[a]),sc,ca
 def attr(self,mode,act,before,after):
  if not self.risk: return
  if mode=='accurate' and act=='read' and after<before:
   self.read_c-=5.0; self.updates.append('self_read')
  elif mode=='depressed' and after<before:
   self.rest_c=100.0; self.updates.append('panic')

def run(seed,mode):
 risk = mode!='reckless'
 a=EFE(seed,risk); e=START; rows=[]; waste=0.0; reads=0
 for t in range(1,TICKS+1):
  s=eb(e); act,sc,ca=a.act(e,s)
  before=e; shock=random.Random(seed*1000+t).random()<0.30
  mag=random.Random(seed*2000+t).randint(2,5) if shock else 0
  e+=EFFECT[act]-mag
  if act=='rest' and e>100: waste+=e-100
  e=max(0,min(100,e))
  if act=='read': reads+=1
  a.attr(mode,act,before,e)
  a.update(act,s,eb(e))
  rows.append({'tick':t,'action':act,'energy_before':before,'energy_after':e,'shock':shock,
               'mag':mag,'read_c':round(ca['read'],2),'rest_c':round(ca['rest'],2),
               'scores':{k:round(v,3) for k,v in sc.items()},'dead':e<=0})
  if e<=0: break
 fitness=round(e+1.5*reads-2.0*waste,2)
 return {'seed':seed,'mode':mode,'risk':risk,'rows':rows,'survival':len(rows),
         'final_energy':e,'dead':bool(rows and rows[-1]['dead']),'read':reads,
         'rest':sum(1 for r in rows if r['action']=='rest'),
         'look':sum(1 for r in rows if r['action']=='look'),
         'waste':round(waste,2),'fitness':fitness,'guard':a.guard,'updates':len(a.updates)}

if __name__=='__main__':
 out=[]
 for seed in (1,2,3):
  for mode in ('accurate','blame_shift','depressed','reckless'):
   out.append(run(seed,mode))
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('SUMMARY')
 for r in out:
  print(r['mode'],'seed',r['seed'],'risk',r['risk'],'surv',r['survival'],'E',r['final_energy'],
        'dead',r['dead'],'read',r['read'],'rest',r['rest'],'look',r['look'],'waste',r['waste'],
        'fit',r['fitness'],'guard',r['guard'])
 print('SAVED',OUT)
