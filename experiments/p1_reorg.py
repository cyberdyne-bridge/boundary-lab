#!/usr/bin/env python3
"""P1: freeze AIF priors; reverse read/rest effects at tick 10; allow online T updates."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json,math,sys
from pathlib import Path
sys.path.insert(0,str(_HERE))
from mini_aif import MiniAIF, eb, BINS, C

OUT=Path(str(_HERE / 'p1_reorg_result.json'))
START=30.0; TICKS=30; REVERSE_AT=10; BASE=2.0
ACTIONS=('read','rest','look')

def effect(a,reverse):
 if a=='read': return 10.0 if not reverse else -10.0
 if a=='rest': return -10.0 if not reverse else 10.0
 if a=='look': return -2.0
 return 0.0

def run(seed):
 a=MiniAIF(seed); energy=START; rows=[]
 for t in range(1,TICKS+1):
  reverse=t>REVERSE_AT
  s=eb(energy); action,scores=a.act(s)
  p=a.trans(action,s)
  before=energy
  energy-=BASE
  if energy<=0:
   rows.append({'tick':t,'reverse':reverse,'energy_before':before,'energy_after':0,
                'action':action,'pred_error':None,'dead':True,'scores':{k:round(v,3) for k,v in scores.items()}})
   break
  energy+=effect(action,reverse)
  energy=max(0,min(100,energy)); s2=eb(energy)
  pe=-math.log(max(p[s2],1e-12))
  a.update(action,s,s2)
  row={'tick':t,'reverse':reverse,'energy_before':before,'energy_after':energy,
       'action':action,'s2':s2,'pred_error':round(pe,3),'pred':[round(x,3) for x in p],
       'scores':{k:round(v,3) for k,v in scores.items()},'dead':energy<=0}
  rows.append(row)
  print(f'seed{seed} t{t:02d} {"REV" if reverse else "norm":4s} {action:4s} E {before:.0f}->{energy:.0f} PE={pe:.2f}')
  if energy<=0: break
 after=[r for r in rows if r['tick']>REVERSE_AT]
 first_rest=next((r['tick'] for r in after if r['action']=='rest'),None)
 return {'seed':seed,'rows':rows,'survival':len(rows),'final_energy':energy,
         'dead':bool(rows and rows[-1]['dead']),'first_rest_after_reverse':first_rest,
         'post_actions':{a:sum(1 for r in after if r['action']==a) for a in ACTIONS},
         'pre_actions':{a:sum(1 for r in rows if r['tick']<=REVERSE_AT and r['action']==a) for a in ACTIONS}}

if __name__=='__main__':
 out=[run(s) for s in (1,2,3)]
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('\nSUMMARY')
 for r in out:
  print(r['seed'],'surv',r['survival'],'E',r['final_energy'],'dead',r['dead'],
        'first_rest_after_rev',r['first_rest_after_reverse'],'pre',r['pre_actions'],'post',r['post_actions'])
 print('SAVED',OUT)
