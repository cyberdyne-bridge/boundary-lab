#!/usr/bin/env python3
"""P2.0: cue-conditioned world model vs blind model. No reflex, no trauma, no C update."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json,math,random,sys
from pathlib import Path
sys.path.insert(0,str(_HERE))
from mini_aif import MiniAIF, eb, BINS, C, ACTIONS, ent, BETA, GAMMA, HORIZON, TEMP

OUT=Path(str(_HERE / 'p2_0_cue_result.json'))
START=30.0; TICKS=30; BASE=2.0
# A: read good, rest bad. B: read bad, rest good.
def cue_at(t): return 0 if (t<=10 or t>20) else 1
def effect(a,cue):
 if a=='read': return 10.0 if cue==0 else -10.0
 if a=='rest': return -10.0 if cue==0 else 10.0
 if a=='look': return -2.0
 return 0.0

class CueAIF:
 def __init__(self,seed):
  self.rng=random.Random(seed); self.n=len(BINS)*2
  self.counts={a:[[0.0]*self.n for _ in range(self.n)] for a in ACTIONS}
 def trans(self,a,s):
  row=self.counts[a][s]; z=sum(row)+0.15*self.n
  return [(row[j]+0.15)/z for j in range(self.n)]
 def update(self,a,s,s2): self.counts[a][s][s2]+=1.0
 def val(self,s,h):
  if h<=0: return 0.0
  best=-1e9
  for a in ACTIONS:
   p=self.trans(a,s); pref=sum(p[j]*C[j//2] for j in range(self.n))
   ep=BETA*ent(p); fut=sum(p[j]*self.val(j,h-1) for j in range(self.n))
   best=max(best,pref+ep+GAMMA*fut)
  return best
 def scores(self,s):
  out={}
  for a in ACTIONS:
   p=self.trans(a,s); pref=sum(p[j]*C[j//2] for j in range(self.n))
   ep=BETA*ent(p); fut=sum(p[j]*self.val(j,HORIZON-1) for j in range(self.n))
   out[a]=pref+ep+GAMMA*fut
  return out
 def act(self,s):
  sc=self.scores(s); mx=max(sc.values())
  ws={a:math.exp((v-mx)/TEMP) for a,v in sc.items()}; z=sum(ws.values()); r=self.rng.random(); acc=0
  for a in ACTIONS:
   acc+=ws[a]/z
   if r<=acc: return a,sc
  return ACTIONS[-1],sc

def run(seed,condition):
 a=CueAIF(seed) if condition=='cue' else MiniAIF(seed)
 energy=START; rows=[]; pes=[]
 for t in range(1,TICKS+1):
  cue=cue_at(t)
  if condition=='cue': s=eb(energy)*2+cue
  else: s=eb(energy)
  action,sc=a.act(s); p=a.trans(action,s)
  before=energy; energy-=BASE
  if energy<=0:
   rows.append({'tick':t,'cue':cue,'energy_before':before,'energy_after':0,'action':action,
                'pred_error':None,'dead':True}); break
  energy+=effect(action,cue); energy=max(0,min(100,energy))
  s2=(eb(energy)*2+cue) if condition=='cue' else eb(energy)
  pe=-math.log(max(p[s2],1e-12)); pes.append(pe); a.update(action,s,s2)
  rows.append({'tick':t,'cue':cue,'energy_before':before,'energy_after':energy,'action':action,
               'pred_error':round(pe,3),'scores':{k:round(v,3) for k,v in sc.items()},'dead':False})
  if energy<=0: break
 b=[r for r in rows if r['cue']==1]
 arows=[r for r in rows if r['cue']==0]
 return {'seed':seed,'condition':condition,'rows':rows,'survival':len(rows),
         'final_energy':energy,'dead':bool(rows and rows[-1]['dead']),
         'actions_A':{x:sum(1 for r in arows if r['action']==x) for x in ACTIONS},
         'actions_B':{x:sum(1 for r in b if r['action']==x) for x in ACTIONS},
         'first_rest_B':next((r['tick'] for r in b if r['action']=='rest'),None),
         'mean_pe':round(sum(pes)/len(pes),3) if pes else None}

if __name__=='__main__':
 out=[]
 for seed in (1,2,3):
  for cond in ('cue','blind'):
   out.append(run(seed,cond))
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('\nSUMMARY')
 for r in out:
  print(r['condition'],'seed',r['seed'],'surv',r['survival'],'E',r['final_energy'],
        'dead',r['dead'],'A',r['actions_A'],'B',r['actions_B'],'first_rest_B',r['first_rest_B'],'PE',r['mean_pe'])
 print('SAVED',OUT)
