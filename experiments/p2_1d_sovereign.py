#!/usr/bin/env python3
"""P2.1d: attribution-gated policy + fitness penalty for over-rest/waste."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json,random,sys
from pathlib import Path
sys.path.insert(0,str(_HERE))
from p2_1c_boundary import event, train_attr, pred_attr

OUT=Path(str(_HERE / 'p2_1d_sovereign_result.json'))
EFFECT={'read':-10.0,'rest':6.0,'look':0.0}

def run(seed,mode):
 rng=random.Random(seed+300); tab=train_attr([event(rng) for _ in range(1200)])
 e=30.0; cue=0; avoid=0; rows=[]; waste=0.0
 for t in range(1,31):
  if avoid>0: act='rest'; source='avoid'; avoid-=1
  elif e<15: act='rest'; source='safety'
  else: act='read' if cue==0 else 'rest'; source='base'
  before=e; shock=rng.random()<0.30; mag=rng.randint(2,5) if shock else 0
  e+=EFFECT[act]-mag
  if act=='rest' and e>100: waste+=(e-100)
  e=max(0,min(100,e))
  # attribution after observing action/delta
  if mode=='accurate': pred=pred_attr(tab,act,e-before)
  elif mode=='depressed': pred='self'
  else: pred='world'
  # policy gate
  if mode=='depressed' and e<before: avoid=3
  elif pred=='self' and act=='read': avoid=3
  rows.append({'tick':t,'cue':cue,'action':act,'source':source,'shock':shock,'mag':mag,
               'energy_before':before,'energy_after':e,'pred':pred,'avoid_after':avoid,'waste':round(waste,2),'dead':e<=0})
  if t%5==0: cue=1-cue
  if e<=0: break
 rest=sum(1 for r in rows if r['action']=='rest')
 fitness=round(e-0.8*rest-1.0*waste,2)
 return {'seed':seed,'mode':mode,'rows':rows,'survival':len(rows),'final_energy':e,
         'dead':bool(rows and rows[-1]['dead']),'read':sum(1 for r in rows if r['action']=='read'),
         'rest':rest,'waste':round(waste,2),'fitness':fitness,'shocks':sum(1 for r in rows if r['shock'])}

if __name__=='__main__':
 out=[]
 for seed in (1,2,3):
  for mode in ('accurate','depressed','blame_shift'):
   out.append(run(seed,mode))
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('SUMMARY')
 for r in out:
  print(r['mode'],'seed',r['seed'],'surv',r['survival'],'E',r['final_energy'],'dead',r['dead'],
        'read',r['read'],'rest',r['rest'],'waste',r['waste'],'fit',r['fitness'],'shocks',r['shocks'])
 print('SAVED',OUT)
