#!/usr/bin/env python3
"""P2.0d: exhaustive grid curriculum + audit + frozen greedy readout."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json,random,sys
from pathlib import Path
sys.path.insert(0,str(_HERE))
from p2_0_cue import effect
from p2_0c_relative import TrendAIF, trend_bin, greedy, schedule, C_TREND
from mini_aif import ACTIONS

OUT=Path(str(_HERE / 'p2_0d_grid_result.json'))
E0=30.0; E1=30.0; BASE=2.0; REPS=5

def pretrain(seed):
 a=TrendAIF(seed); train=[]
 for cue in (0,1):
  for trend in (0,1,2):
   for act in ACTIONS:
    for rep in range(REPS):
     e=E0; before=e; s=trend*2+cue
     e-=BASE; e+=effect(act,cue); e=max(0,min(100,e))
     nt=trend_bin(e-before); s2=nt*2+cue
     a.update(act,s,s2); train.append({'cue':cue,'trend':trend,'action':act,'rep':rep,'delta':e-before,'next_trend':nt})
 return a,train

def audit(a):
 report={}; ok=True
 for cue in (0,1):
  for trend in (0,1,2):
   s=trend*2+cue
   report[f'c{cue}_t{trend}']={}
   for act in ACTIONS:
    n=sum(a.counts[act][s]); report[f'c{cue}_t{trend}'][act]=n
    if n<=0: ok=False
 return ok,report

def run(seed):
 a,train=pretrain(seed); ok,report=audit(a)
 if not ok:
  print('AUDIT FAILED seed',seed,report); return {'seed':seed,'audit_ok':False,'audit':report}
 seq=schedule(seed); e=E1; trend=1; rows=[]; prev=None
 for tick,cue in enumerate(seq,1):
  s=trend*2+cue; act=greedy(a,s); before=e; e-=BASE
  if e<=0:
   rows.append({'tick':tick,'cue':cue,'trend':trend,'energy_before':before,'energy_after':0,
                'action':act,'correct':False,'switch':prev is not None and cue!=prev,'dead':True}); break
  e+=effect(act,cue); e=max(0,min(100,e)); nt=trend_bin(e-before)
  correct=(cue==0 and act=='read') or (cue==1 and act=='rest')
  switch=prev is not None and cue!=prev
  rows.append({'tick':tick,'cue':cue,'trend':trend,'next_trend':nt,'energy_before':before,'energy_after':e,
               'action':act,'correct':correct,'switch':switch,'dead':False})
  prev=cue; trend=nt
  if e<=0: break
 switches=[r for r in rows if r['switch']]; sc=sum(1 for r in switches if r['correct'])
 return {'seed':seed,'audit_ok':ok,'audit':report,'rows':rows,'survival':len(rows),
         'final_energy':e,'dead':bool(rows and rows[-1]['dead']),
         'accuracy':round(sum(1 for r in rows if r['correct'])/len(rows),3),
         'switches':len(switches),'switch_correct':sc,
         'zero_delay':len(switches)>0 and sc==len(switches)}

if __name__=='__main__':
 out=[run(s) for s in (1,2,3)]
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('SUMMARY')
 for r in out:
  print('seed',r['seed'],'audit',r.get('audit_ok'),'surv',r.get('survival'),'E',r.get('final_energy'),
        'dead',r.get('dead'),'acc',r.get('accuracy'),'switch',r.get('switch_correct'),'/',r.get('switches'),
        '0delay',r.get('zero_delay'))
 print('SAVED',OUT)
