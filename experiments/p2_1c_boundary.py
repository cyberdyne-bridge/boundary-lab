#!/usr/bin/env python3
"""P2.1c: self/world credit assignment with external shocks; policy ablation."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json,random
from pathlib import Path

OUT=Path(str(_HERE / 'p2_1c_boundary_result.json'))
ACTS=('read','rest','look')
EFFECT={'read':-10.0,'rest':6.0,'look':0.0}

def event(rng):
 a=rng.choice(ACTS); before=rng.uniform(20,80)
 shock=rng.random()<0.30
 mag=rng.randint(2,5) if shock else 0
 after=before+EFFECT[a]-mag
 label='world' if shock else 'self'
 return a,before,after,mag,label

def train_attr(rows):
 tab={}
 for a,b,aft,mag,lab in rows:
  d=round(aft-b,1); k=(a,d)
  tab.setdefault(k,{'self':0,'world':0})[lab]+=1
 return tab

def pred_attr(tab,a,d,fallback='self'):
 t=tab.get((a,round(d,1)))
 if not t: return fallback
 return max(t,key=t.get)

def attr_eval(seed):
 rng=random.Random(seed+100); rows=[event(rng) for _ in range(2000)]
 split=int(len(rows)*0.7); tab=train_attr(rows[:split]); test=rows[split:]
 ok=0
 for a,b,aft,mag,lab in test:
  ok+=pred_attr(tab,a,aft-b)==lab
 probes=[]
 for a,d,expected in [('read',-10,'self'),('look',-3,'world'),('read',-13,'world'),('look',0,'self')]:
  p=pred_attr(tab,a,d); probes.append({'action':a,'delta':d,'expected':expected,'pred':p,'ok':p==expected})
 return {'attr_acc':round(ok/len(test),3),'probes':probes,'table':len(tab)}

def run_policy(seed,mode):
 rng=random.Random(seed+200); e=30.0; cue=0; avoid=0; rows=[]
 for t in range(1,31):
  # base external policy: A read, B rest
  if avoid>0:
   act='rest'; avoid-=1; source='avoid'
  else:
   act='read' if cue==0 else 'rest'; source='base'
  before=e; shock=rng.random()<0.30; mag=rng.randint(2,5) if shock else 0
  e+=EFFECT[act]-mag; e=max(0,min(100,e))
  # attribution mode
  if mode=='accurate': pred='world' if shock else 'self'
  elif mode=='depressed': pred='self'  # everything is my fault
  else: pred='world'             # blame the world, never self
  # policy adjustment: self-caused read -> avoid read
  if pred=='self' and act=='read': avoid=2
  rows.append({'tick':t,'cue':cue,'action':act,'source':source,'shock':shock,'mag':mag,
               'energy_after':e,'pred':pred,'avoid_after':avoid,'dead':e<=0})
  if t%5==0: cue=1-cue
  if e<=0: break
 return {'seed':seed,'mode':mode,'rows':rows,'survival':len(rows),'final_energy':e,
         'dead':bool(rows and rows[-1]['dead']),
         'read_count':sum(1 for r in rows if r['action']=='read'),
         'rest_count':sum(1 for r in rows if r['action']=='rest'),
         'shocks':sum(1 for r in rows if r['shock'])}

if __name__=='__main__':
 out=[]
 for seed in (1,2,3):
  a=attr_eval(seed); a['seed']=seed; a['policies']=[run_policy(seed,m) for m in ('accurate','depressed','blame_shift')]
  out.append(a)
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('SUMMARY')
 for r in out:
  print('seed',r['seed'],'attr',r['attr_acc'],'probes',[(p['action'],p['delta'],p['pred'],p['ok']) for p in r['probes']])
  for p in r['policies']:
   print(' ',p['mode'],'surv',p['survival'],'E',p['final_energy'],'dead',p['dead'],'read',p['read_count'],'rest',p['rest_count'],'shocks',p['shocks'])
 print('SAVED',OUT)
