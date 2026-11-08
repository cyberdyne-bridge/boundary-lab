#!/usr/bin/env python3
"""P2.0c: relative trend state (up/flat/down) x cue; coverage pretrain; greedy readout."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json,math,random,sys
from pathlib import Path
sys.path.insert(0,str(_HERE))
from p2_0_cue import effect
from mini_aif import ACTIONS, ent, BETA, GAMMA, HORIZON, TEMP

OUT=Path(str(_HERE / 'p2_0c_relative_result.json'))
TREND_NAMES=('down','flat','up'); C_TREND=[-12.0,0.0,7.0]
PHASE0_ENERGY=30.0; PHASE1_ENERGY=30.0; BASE=2.0
FORCE=['read','rest','look','read','rest','look','read','rest','look','read','rest','look']

def trend_bin(delta):
 if delta>=5: return 2
 if delta<=-5: return 0
 return 1

class TrendAIF:
 def __init__(self,seed):
  self.rng=random.Random(seed); self.n=3*2
  self.counts={a:[[0.0]*self.n for _ in range(self.n)] for a in ACTIONS}
 def trans(self,a,s):
  row=self.counts[a][s]; z=sum(row)+0.15*self.n
  return [(row[j]+0.15)/z for j in range(self.n)]
 def update(self,a,s,s2): self.counts[a][s][s2]+=1.0
 def val(self,s,h):
  if h<=0: return 0.0
  best=-1e9
  for a in ACTIONS:
   p=self.trans(a,s); pref=sum(p[j]*C_TREND[j//2] for j in range(self.n))
   ep=BETA*ent(p); fut=sum(p[j]*self.val(j,h-1) for j in range(self.n))
   best=max(best,pref+ep+GAMMA*fut)
  return best
 def scores(self,s):
  out={}
  for a in ACTIONS:
   p=self.trans(a,s); pref=sum(p[j]*C_TREND[j//2] for j in range(self.n))
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

def greedy(a,s):
 best=None; best_a=None
 for act in ACTIONS:
  p=a.trans(act,s); pref=sum(p[j]*C_TREND[j//2] for j in range(len(p)))
  if best is None or pref>best: best=pref; best_a=act
 return best_a

def pretrain(seed):
 a=TrendAIF(seed); train=[]
 for cue in (0,1):
  e=PHASE0_ENERGY; trend=1
  for act in FORCE:
   s=trend*2+cue; before=e; e-=BASE
   if e<=0: break
   e+=effect(act,cue); e=max(0,min(100,e))
   nt=trend_bin(e-before); s2=nt*2+cue
   a.update(act,s,s2); train.append({'cue':cue,'trend':trend,'action':act,'delta':e-before,'next_trend':nt})
   e=PHASE0_ENERGY; trend=nt
 return a,train

def schedule(seed):
 rng=random.Random(seed+777); out=[]; cue=0
 while len(out)<30:
  seg=rng.randint(4,6); out.extend([cue]*min(seg,30-len(out))); cue=1-cue
 return out

def run(seed,policy):
 a,train=pretrain(seed); seq=schedule(seed); e=PHASE1_ENERGY; trend=1; rows=[]; prev=None
 for tick,cue in enumerate(seq,1):
  s=trend*2+cue
  act=greedy(a,s) if policy=='greedy' else a.act(s)[0]
  before=e; e-=BASE
  if e<=0:
   rows.append({'tick':tick,'cue':cue,'trend':trend,'energy_before':before,'energy_after':0,
                'action':act,'correct':False,'switch':prev is not None and cue!=prev,'dead':True}); break
  e+=effect(act,cue); e=max(0,min(100,e))
  nt=trend_bin(e-before)
  correct=(cue==0 and act=='read') or (cue==1 and act=='rest')
  switch=prev is not None and cue!=prev
  rows.append({'tick':tick,'cue':cue,'trend':trend,'next_trend':nt,'energy_before':before,'energy_after':e,
               'action':act,'correct':correct,'switch':switch,'dead':False})
  prev=cue; trend=nt
  if e<=0: break
 switches=[r for r in rows if r['switch']]
 sc=sum(1 for r in switches if r['correct'])
 return {'seed':seed,'policy':policy,'rows':rows,'survival':len(rows),'final_energy':e,
         'dead':bool(rows and rows[-1]['dead']),'accuracy':round(sum(1 for r in rows if r['correct'])/len(rows),3),
         'switches':len(switches),'switch_correct':sc,'zero_delay':len(switches)>0 and sc==len(switches),
         'train':train}

if __name__=='__main__':
 out=[]
 for seed in (1,2,3):
  for pol in ('greedy','aif'):
   out.append(run(seed,pol))
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('SUMMARY')
 for r in out:
  print(r['policy'],'seed',r['seed'],'surv',r['survival'],'E',r['final_energy'],'dead',r['dead'],
        'acc',r['accuracy'],'switch',r['switch_correct'],'/',r['switches'],'0delay',r['zero_delay'])
 print('SAVED',OUT)
