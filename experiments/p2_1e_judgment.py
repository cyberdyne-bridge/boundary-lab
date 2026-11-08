#!/usr/bin/env python3
"""P2.1e: no base policy. EFE action choice; attribution edits action C; waste fitness."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json,math,random
from pathlib import Path

OUT=Path(str(_HERE / 'p2_1e_judgment_result.json'))
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
 def __init__(self,seed):
  self.rng=random.Random(seed); self.n=len(BINS)
  self.counts={a:[[0.0]*self.n for _ in range(self.n)] for a in ACTS}
  self.ca={'read':[10.0]*self.n,'rest':[3.0]*self.n,'look':[0.0]*self.n}
  self.updates=[]
 def trans(self,a,s):
  row=self.counts[a][s]; z=sum(row)+0.2*self.n
  return [(row[j]+0.2)/z for j in range(self.n)]
 def update(self,a,s,s2): self.counts[a][s][s2]+=1.0
 def scores(self,s):
  out={}
  for a in ACTS:
   p=self.trans(a,s)
   util=self.ca[a][s]+sum(p[j]*CSTATE[j] for j in range(self.n))
   ep=BETA*ent(p)
   out[a]=util+ep
  return out
 def act(self,s):
  sc=self.scores(s); return max(ACTS,key=lambda a:sc[a]),sc
 def punish(self,a,s2,kind):
  if kind=='accurate_self_read' and a=='read':
   b=self.ca[a][s2]; self.ca[a][s2]-=5.0
   self.updates.append({'action':a,'bin':s2,'before':b,'after':self.ca[a][s2],'kind':kind})
  elif kind=='depressed_shock':
   for j in range(self.n):
    if self.ca['rest'][j] < 100.0: self.ca['rest'][j]=100.0
   self.updates.append({'action':'rest','bin':s2,'before':3.0,'after':100.0,'kind':kind})

def run(seed,mode):
 a=EFE(seed); e=START; rows=[]; waste=0.0
 for t in range(1,TICKS+1):
  s=eb(e); act,sc=a.act(s)
  before=e; shock=random.Random(seed*1000+t).random()<0.30
  mag=random.Random(seed*2000+t).randint(2,5) if shock else 0
  e+=EFFECT[act]-mag
  if act=='rest' and e>100: waste+=e-100
  e=max(0,min(100,e)); s2=eb(e)
  kind=None
  if mode=='accurate' and act=='read' and not shock and e<before: kind='accurate_self_read'
  elif mode=='depressed' and e<before: kind='depressed_shock'
  if kind: a.punish(act,s2,kind)
  a.update(act,s,s2)
  rows.append({'tick':t,'action':act,'energy_before':before,'energy_after':e,'shock':shock,
               'mag':mag,'kind':kind,'scores':{k:round(v,3) for k,v in sc.items()},'dead':e<=0})
  if e<=0: break
 rest=sum(1 for r in rows if r['action']=='rest')
 fitness=round(e-2.0*waste,2)
 return {'seed':seed,'mode':mode,'rows':rows,'survival':len(rows),'final_energy':e,
         'dead':bool(rows and rows[-1]['dead']),'read':sum(1 for r in rows if r['action']=='read'),
         'rest':rest,'look':sum(1 for r in rows if r['action']=='look'),
         'waste':round(waste,2),'fitness':fitness,'updates':a.updates}

if __name__=='__main__':
 out=[]
 for seed in (1,2,3):
  for mode in ('accurate','depressed','blame_shift'):
   out.append(run(seed,mode))
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('SUMMARY')
 for r in out:
  print(r['mode'],'seed',r['seed'],'surv',r['survival'],'E',r['final_energy'],'dead',r['dead'],
        'read',r['read'],'rest',r['rest'],'look',r['look'],'waste',r['waste'],'fit',r['fitness'],'upd',len(r['updates']))
 print('SAVED',OUT)
