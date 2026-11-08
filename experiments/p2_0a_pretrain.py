#!/usr/bin/env python3
"""P2.0a: coverage pretraining in both worlds, then frozen-map cue switch test."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json,random,sys
from pathlib import Path
sys.path.insert(0,str(_HERE))
from p2_0_cue import CueAIF, effect
from mini_aif import ACTIONS, eb

OUT=Path(str(_HERE / 'p2_0a_pretrain_result.json'))
PHASE0_ENERGY=30.0; PHASE1_ENERGY=30.0; BASE=2.0
FORCE=['read','rest','look','read','rest','look','read','rest','look','read']

def run(seed):
 a=CueAIF(seed); e=PHASE0_ENERGY; train=[]; dead0=False
 # Phase 0: coverage curriculum, both worlds, 10 ticks each
 for cue in (0,1):
  e=PHASE0_ENERGY
  for i,act in enumerate(FORCE):
   s=eb(e)*2+cue; before=e; e-=BASE
   if e<=0: dead0=True; break
   e+=effect(act,cue); e=max(0,min(100,e)); s2=eb(e)*2+cue
   a.update(act,s,s2)
   train.append({'cue':cue,'tick':len(train)+1,'energy_before':before,'energy_after':e,'action':act})
   e=PHASE0_ENERGY
  if dead0: break
 # Phase 1: reset energy, alternate cue blocks, frozen T
 e=PHASE1_ENERGY; rows=[]; rng=random.Random(seed+777); tick=0; cue=0; prev=None
 while tick<30 and not dead0:
  seg=rng.randint(4,6)
  for _ in range(seg):
   tick+=1
   s=eb(e)*2+cue; act,sc=a.act(s); before=e; e-=BASE
   if e<=0:
    rows.append({'tick':tick,'cue':cue,'energy_before':before,'energy_after':0,'action':act,
                 'correct':False,'switch':prev is not None and cue!=prev,'dead':True})
    dead0=True; break
   e+=effect(act,cue); e=max(0,min(100,e))
   correct=(cue==0 and act=='read') or (cue==1 and act=='rest')
   switch=prev is not None and cue!=prev
   rows.append({'tick':tick,'cue':cue,'energy_before':before,'energy_after':e,'action':act,
                'correct':correct,'switch':switch,'dead':False})
   prev=cue
   if tick>=30: break
  if tick>=30: break
  cue=1-cue
 switches=[r for r in rows if r['switch']]
 switch_correct=sum(1 for r in switches if r['correct'])
 correct=sum(1 for r in rows if r['correct'])
 counts={}
 for c in (0,1):
  counts[c]={x:sum(1 for tr in train if tr['cue']==c and tr['action']==x) for x in ACTIONS}
 return {'seed':seed,'train':train,'rows':rows,'phase0_dead':dead0 and not rows,
         'survival':len(rows),'final_energy':e,'dead':bool(rows and rows[-1]['dead']),
         'accuracy':round(correct/len(rows),3) if rows else None,
         'switches':len(switches),'switch_correct':switch_correct,
         'zero_delay':len(switches)>0 and switch_correct==len(switches),
         'train_actions':counts}

if __name__=='__main__':
 out=[run(s) for s in (1,2,3)]
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('SUMMARY')
 for r in out:
  print('seed',r['seed'],'surv',r['survival'],'E',r['final_energy'],'dead',r['dead'],
        'acc',r['accuracy'],'switch',r['switch_correct'],'/',r['switches'],
        'zero_delay',r['zero_delay'],'train',r['train_actions'])
 print('SAVED',OUT)
