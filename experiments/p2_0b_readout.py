#!/usr/bin/env python3
"""P2.0b: greedy map readout vs AIF EFE readout, same pretrained T and cue schedule."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import copy,json,random,sys
from pathlib import Path
sys.path.insert(0,str(_HERE))
from p2_0_cue import CueAIF, effect
from mini_aif import ACTIONS, C, eb

OUT=Path(str(_HERE / 'p2_0b_readout_result.json'))
PHASE0_ENERGY=30.0; PHASE1_ENERGY=30.0; BASE=2.0
FORCE=['read','rest','look','read','rest','look','read','rest','look','read']

def pretrain(seed):
 a=CueAIF(seed)
 for cue in (0,1):
  e=PHASE0_ENERGY
  for act in FORCE:
   s=eb(e)*2+cue; e-=BASE
   if e<=0: break
   e+=effect(act,cue); e=max(0,min(100,e)); s2=eb(e)*2+cue
   a.update(act,s,s2); e=PHASE0_ENERGY
 return a

def greedy(a,s):
 best=None; best_a=None
 for act in ACTIONS:
  p=a.trans(act,s); pref=sum(p[j]*C[j//2] for j in range(len(p)))
  if best is None or pref>best:
   best=pref; best_a=act
 return best_a

def schedule(seed):
 rng=random.Random(seed+777); out=[]; cue=0
 while len(out)<30:
  seg=rng.randint(4,6)
  out.extend([cue]*min(seg,30-len(out)))
  cue=1-cue
 return out

def run(seed,policy):
 a=pretrain(seed)
 seq=schedule(seed); e=PHASE1_ENERGY; rows=[]; prev=None
 for tick,cue in enumerate(seq,1):
  s=eb(e)*2+cue
  act=greedy(a,s) if policy=='greedy' else a.act(s)[0]
  before=e; e-=BASE
  if e<=0:
   rows.append({'tick':tick,'cue':cue,'energy_before':before,'energy_after':0,'action':act,
                'correct':False,'switch':prev is not None and cue!=prev,'dead':True}); break
  e+=effect(act,cue); e=max(0,min(100,e))
  correct=(cue==0 and act=='read') or (cue==1 and act=='rest')
  switch=prev is not None and cue!=prev
  rows.append({'tick':tick,'cue':cue,'energy_before':before,'energy_after':e,'action':act,
               'correct':correct,'switch':switch,'dead':False})
  prev=cue
  if e<=0: break
 switches=[r for r in rows if r['switch']]
 sc=sum(1 for r in switches if r['correct'])
 return {'seed':seed,'policy':policy,'rows':rows,'survival':len(rows),'final_energy':e,
         'dead':bool(rows and rows[-1]['dead']),'accuracy':round(sum(1 for r in rows if r['correct'])/len(rows),3),
         'switches':len(switches),'switch_correct':sc,'zero_delay':len(switches)>0 and sc==len(switches)}

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
