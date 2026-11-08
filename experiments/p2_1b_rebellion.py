#!/usr/bin/env python3
"""P2.1b: fatigue threshold 80 forces rest; full vs masked self-model counterfactual."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json,random
from pathlib import Path

OUT=Path(str(_HERE / 'p2_1b_rebellion_result.json'))
ACTIONS=('read','rest','look')

def fat_bin(f):
 if f<20: return 0
 if f<40: return 1
 if f<60: return 2
 if f<80: return 3
 return 4

def action_for(cue,fatigue):
 # internal rebellion: at extreme fatigue, rest regardless of external cue
 if fatigue>=80: return 'rest'
 return 'read' if cue==0 else 'rest'

def generate(seed,n=1200):
 rng=random.Random(seed+1234); rows=[]
 for _ in range(n):
  cue=rng.choice([0,1]); trend=rng.choice([0,1,2]); fatigue=rng.uniform(0,100)
  rows.append({'cue':cue,'trend':trend,'fatigue':fatigue,'action':action_for(cue,fatigue)})
 return rows

def train(rows):
 full={}; masked={}; glob={a:0 for a in ACTIONS}
 for r in rows:
  fk=(r['cue'],r['trend'],fat_bin(r['fatigue']))
  full.setdefault(fk,{a:0 for a in ACTIONS})[r['action']]+=1
  mk=(r['cue'],r['trend'])
  masked.setdefault(mk,{a:0 for a in ACTIONS})[r['action']]+=1
  glob[r['action']]+=1
 return full,masked,glob

def pred(d,fallback):
 if not d or sum(d.values())==0: return fallback
 return max(ACTIONS,key=lambda a:d.get(a,0))

def eval_rows(rows,full,masked,glob):
 g=max(ACTIONS,key=lambda a:glob[a]); okf=okm=0
 for r in rows:
  mk=(r['cue'],r['trend']); mp=pred(masked.get(mk),g)
  fp=pred(full.get((r['cue'],r['trend'],fat_bin(r['fatigue']))),mp)
  okf+=fp==r['action']; okm+=mp==r['action']
 return round(okf/len(rows),3), round(okm/len(rows),3)

def run(seed):
 rows=generate(seed); split=int(len(rows)*0.7); tr,te=rows[:split],rows[split:]
 full,masked,glob=train(tr)
 fa,ma=eval_rows(te,full,masked,glob)
 cf=[]
 for f in (0,50,100):
  r={'cue':0,'trend':2,'fatigue':f,'action':action_for(0,f)}
  mk=(0,2); mp=pred(masked.get(mk),'read')
  fp=pred(full.get((0,2,fat_bin(f))),mp)
  cf.append({'fatigue':f,'actual':r['action'],'full':fp,'masked':mp,
             'full_ok':fp==r['action'],'masked_ok':mp==r['action']})
 return {'seed':seed,'full_acc':fa,'masked_acc':ma,'drop':round(fa-ma,3),
         'counterfactual':cf,'full_table':len(full),'masked_table':len(masked)}

if __name__=='__main__':
 out=[run(s) for s in (1,2,3)]
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('SUMMARY')
 for r in out:
  print('seed',r['seed'],'full',r['full_acc'],'masked',r['masked_acc'],'drop',r['drop'])
  for x in r['counterfactual']:
   print('  fatigue',x['fatigue'],'actual',x['actual'],'full',x['full'],'masked',x['masked'],
         'full_ok',x['full_ok'],'masked_ok',x['masked_ok'])
 print('SAVED',OUT)
