#!/usr/bin/env python3
"""P1.9: bare AIF. No Layer0, no -999, no forced action. PE updates T/C; panic only raises LR."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json,math,sys
from pathlib import Path
sys.path.insert(0,str(_HERE))
from mini_aif import MiniAIF, eb, BINS, C, ACTIONS, ent, BETA, GAMMA, HORIZON

OUT=Path(str(_HERE / 'p1_9_pure_result.json'))
START=30.0; TICKS=30; REVERSE_AT=10; BASE=2.0; PANIC_SUM=3.0
BASE_LR=1.0; PANIC_LR=8.0; PANIC_TICKS=5; C_ETA=0.15

class P19AIF(MiniAIF):
 def __init__(self,seed):
  super().__init__(seed)
  self.c={a:list(C) for a in ACTIONS}
  self.lr=BASE_LR
  self.c_updates=[]
 def val(self,s,h):
  if h<=0: return 0.0
  best=-1e9
  for a in ACTIONS:
   p=self.trans(a,s); pref=sum(p[j]*self.c[a][j] for j in range(len(BINS)))
   ep=BETA*ent(p)
   fut=sum(p[j]*self.val(j,h-1) for j in range(len(BINS)))
   best=max(best,pref+ep+GAMMA*fut)
  return best
 def scores(self,s):
  out={}
  for a in ACTIONS:
   p=self.trans(a,s); pref=sum(p[j]*self.c[a][j] for j in range(len(BINS)))
   ep=BETA*ent(p)
   fut=sum(p[j]*self.val(j,HORIZON-1) for j in range(len(BINS)))
   out[a]=pref+ep+GAMMA*fut
  return out
 def learn(self,a,s,s2,pe):
  self.counts[a][s][s2]+=self.lr
  before=self.c[a][s2]
  self.c[a][s2]=max(-30.0,self.c[a][s2]-C_ETA*self.lr*pe)
  rec={'action':a,'bin':s2,'pe':round(pe,2),'lr':self.lr,'before':round(before,2),'after':round(self.c[a][s2],2)}
  self.c_updates.append(rec)

def effect(a,reverse):
 if a=='read': return 10.0 if not reverse else -10.0
 if a=='rest': return -10.0 if not reverse else 10.0
 if a=='look': return -2.0
 return 0.0

def run(seed):
 a=P19AIF(seed); energy=START; rows=[]; pes=[]; panic=False; panic_tick=None; panic_until=-1
 for t in range(1,TICKS+1):
  reverse=t>REVERSE_AT; s=eb(energy)
  action,scores=a.act(s); p=a.trans(action,s)
  before=energy; energy-=BASE
  if energy<=0:
   rows.append({'tick':t,'reverse':reverse,'energy_before':before,'energy_after':0,
                'action':action,'pred_error':None,'lr':a.lr,'dead':True})
   break
  energy+=effect(action,reverse); energy=max(0,min(100,energy)); s2=eb(energy)
  pe=-math.log(max(p[s2],1e-12)); pes.append(pe)
  a.learn(action,s,s2,pe)
  panic_now=False
  if reverse and not panic and len(pes)>=2 and sum(pes[-2:])>PANIC_SUM:
   panic=True; panic_tick=t; panic_now=True; panic_until=t+PANIC_TICKS; a.lr=PANIC_LR
  if panic and t>panic_until: a.lr=BASE_LR; panic=False
  row={'tick':t,'reverse':reverse,'energy_before':before,'energy_after':energy,
       'action':action,'pred_error':round(pe,3),'pe_sum2':round(sum(pes[-2:]),3),
       'lr':a.lr,'panic_trigger':panic_now,'panic':panic,
       'c_read':[round(x,2) for x in a.c['read']],'c_rest':[round(x,2) for x in a.c['rest']],
       'dead':energy<=0}
  rows.append(row)
  print(f'seed{seed} t{t:02d} {"REV" if reverse else "norm":4s} {action:4s} E {before:.0f}->{energy:.0f} PE={pe:.2f} lr={a.lr:.0f} Cread={a.c["read"]}')
  if energy<=0: break
 after=[r for r in rows if r['tick']>REVERSE_AT]
 return {'seed':seed,'rows':rows,'survival':len(rows),'final_energy':energy,
         'dead':bool(rows and rows[-1]['dead']),'panic_tick':panic_tick,
         'post_actions':{x:sum(1 for r in after if r['action']==x) for x in ACTIONS},
         'post_read':sum(1 for r in after if r['action']=='read'),
         'c_read_final':[round(x,2) for x in a.c['read']],
         'c_updates':a.c_updates}

if __name__=='__main__':
 out=[run(s) for s in (1,2,3)]
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('\nSUMMARY')
 for r in out:
  print(r['seed'],'surv',r['survival'],'E',r['final_energy'],'dead',r['dead'],
        'panic',r['panic_tick'],'post',r['post_actions'],'post_read',r['post_read'],
        'Cread',r['c_read_final'],'updates',len(r['c_updates']))
 print('SAVED',OUT)
