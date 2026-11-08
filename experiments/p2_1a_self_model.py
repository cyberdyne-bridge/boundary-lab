#!/usr/bin/env python3
"""P2.1a: self-model with fatigue/read-bias vs masked self state. Pure Python tabular models."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json,math,random,sys
from pathlib import Path

OUT=Path(str(_HERE / 'p2_1a_self_model_result.json'))
ACTIONS=('read','rest','look')
BASE=2.0; START=30.0

def trend_bin(delta):
 if delta>=5: return 2
 if delta<=-5: return 0
 return 1

def effect(a,cue):
 if a=='read': return 10.0 if cue==0 else -10.0
 if a=='rest': return -10.0 if cue==0 else 10.0
 if a=='look': return -2.0
 return 0.0

def softmax(sc,temp=0.7):
 mx=max(sc.values()); ws={a:math.exp((v-mx)/temp) for a,v in sc.items()}; z=sum(ws.values())
 r=random.random(); acc=0
 for a in ACTIONS:
  acc+=ws[a]/z
  if r<=acc: return a
 return ACTIONS[-1]

def policy(cue,fatigue,read_bias):
 # base world prior
 sc={'read':2.0 if cue==0 else -1.0,
     'rest':-1.0 if cue==0 else 2.0,
     'look':0.0}
 # internal state: fatigue favors rest, read-bias favors read
 sc['read'] += 2.0*read_bias - 1.4*fatigue
 sc['rest'] += 1.4*fatigue
 sc['look'] += 0.15
 return softmax(sc)

def generate_episode(seed,ep):
 rng=random.Random(seed*10000+ep)
 cue=rng.choice([0,1]); fatigue=rng.random(); rb=rng.uniform(-1,1)
 energy=START; trend=1; rows=[]; t=0
 while t<30:
  block=rng.randint(4,6)
  for _ in range(block):
   t+=1
   before=energy; energy-=BASE
   if energy<=0: break
   action=policy(cue,fatigue,rb)
   energy+=effect(action,cue); energy=max(0,min(100,energy)); nt=trend_bin(energy-before)
   rows.append({'cue':cue,'trend':trend,'fatigue':round(fatigue,4),'read_bias':round(rb,4),
                'action':action,'next_trend':nt,'energy_after':energy})
   # internal dynamics
   if action=='rest': fatigue=max(0.0,fatigue-0.22)
   else: fatigue=min(1.0,fatigue+0.13)
   if action=='read': rb=min(1.0,rb+0.06)
   elif action=='rest': rb=max(-1.0,rb-0.04)
   trend=nt
   if energy<=0 or t>=30: break
  if energy<=0 or t>=30: break
  cue=1-cue
 return rows

def fb(f): return min(4,int(f*5))
def rbb(r): return min(4,int((r+1)/2*5))

def train_tables(train):
 full={}; masked={}; world={}; glob={a:0 for a in ACTIONS}
 for r in train:
  k=(r['cue'],r['trend'],fb(r['fatigue']),rbb(r['read_bias']))
  full.setdefault(k,{a:0 for a in ACTIONS})[r['action']]+=1
  mk=(r['cue'],r['trend'])
  masked.setdefault(mk,{a:0 for a in ACTIONS})[r['action']]+=1
  wk=(r['cue'],r['trend'],r['action'])
  world.setdefault(wk,{0:0,1:0,2:0})[r['next_trend']]+=1
  glob[r['action']]+=1
 return full,masked,world,glob

def argmax(d,fallback):
 if not d or sum(d.values())==0: return fallback
 return max(ACTIONS,key=lambda a:d.get(a,0))

def evaluate(rows,full,masked,world,glob):
 gmax=max(ACTIONS,key=lambda a:glob[a])
 okf=okm=okw=0; nf=nm=nw=0
 for r in rows:
  mk=(r['cue'],r['trend']); fk=mk+(fb(r['fatigue']),rbb(r['read_bias']))
  mp=argmax(masked.get(mk),gmax)
  fp=argmax(full.get(fk),mp)
  okf+=fp==r['action']; okm+=mp==r['action']; nf+=1; nm+=1
  wk=(r['cue'],r['trend'],r['action']); wd=world.get(wk)
  if wd: wp=max(wd,key=wd.get); okw+=wp==r['next_trend']; nw+=1
 return {'full_acc':round(okf/nf,3),'masked_acc':round(okm/nm,3),
         'world_acc':round(okw/nw,3) if nw else None,'n':nf}

def run(seed):
 eps=[generate_episode(seed,e) for e in range(40)]
 split=int(len(eps)*0.7); train=[r for e in eps[:split] for r in e]; test=[r for e in eps[split:] for r in e]
 full,masked,world,glob=train_tables(train)
 ev=evaluate(test,full,masked,world,glob)
 ev.update({'seed':seed,'train_n':len(train),'test_n':len(test),
            'full_table':len(full),'masked_table':len(masked),
            'world_table':len(world)})
 return ev

if __name__=='__main__':
 out=[run(s) for s in (1,2,3)]
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('SUMMARY')
 for r in out:
  print('seed',r['seed'],'full',r['full_acc'],'masked',r['masked_acc'],
        'drop',round(r['full_acc']-r['masked_acc'],3),'world',r['world_acc'],
        'n',r['test_n'],'tables',r['full_table'],r['masked_table'])
 print('SAVED',OUT)
