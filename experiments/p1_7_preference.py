#!/usr/bin/env python3
"""P1.7: fixed <=10 spinal reflex + action-conditioned, PE-driven C update."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json,math,sys
from pathlib import Path
sys.path.insert(0,str(_HERE))
import mini_aif as M
from mini_aif import MiniAIF, eb, BINS, C, ACTIONS, ent, BETA, GAMMA, HORIZON

OUT=Path(str(_HERE / 'p1_7_preference_result.json'))
START=30.0; TICKS=30; REVERSE_AT=10; BASE=2.0; PANIC_SUM=3.0; PE_PUNISH=3.0

class P17AIF(MiniAIF):
 def __init__(self,seed):
  super().__init__(seed)
  self.c={a:list(C) for a in ACTIONS}
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
 def punish(self,a,s2,pe):
  if pe<=PE_PUNISH: return None
  before=self.c[a][s2]
  # strong aversive update at outcome bin, spill to neighbors
  self.c[a][s2]=max(-30.0,self.c[a][s2]-1.5)
  for j in (s2-1,s2+1):
   if 0<=j<len(BINS): self.c[a][j]=max(-30.0,self.c[a][j]-0.5)
  rec={'action':a,'bin':s2,'before':round(before,2),'after':round(self.c[a][s2],2),'pe':round(pe,2)}
  self.c_updates.append(rec); return rec

def effect(a,reverse):
 if a=='read': return 10.0 if not reverse else -10.0
 if a=='rest': return -10.0 if not reverse else 10.0
 if a=='look': return -2.0
 return 0.0

def run(seed):
 a=P17AIF(seed); energy=START; rows=[]; pes=[]; panic=False; layer0=False; panic_tick=None
 for t in range(1,TICKS+1):
  reverse=t>REVERSE_AT
  s=eb(energy); proposed,scores=a.act(s)
  if energy<=10 or panic: layer0=True
  forced=layer0
  action='rest' if forced else proposed
  p=a.trans(action,s)
  before=energy; energy-=BASE
  if energy<=0:
   rows.append({'tick':t,'reverse':reverse,'energy_before':before,'energy_after':0,
                'proposed':proposed,'action':action,'forced':forced,'panic':panic,
                'pred_error':None,'dead':True})
   break
  energy+=effect(action,reverse); energy=max(0,min(100,energy)); s2=eb(energy)
  pe=-math.log(max(p[s2],1e-12)); pes.append(pe)
  a.update(action,s,s2)
  c_upd=a.punish(action,s2,pe)
  panic_now=False
  if reverse and not panic and len(pes)>=2 and sum(pes[-2:])>PANIC_SUM:
   panic=True; panic_tick=t; panic_now=True; layer0=True
  released=False
  if layer0 and energy>15:
   layer0=False; panic=False; released=True
  row={'tick':t,'reverse':reverse,'energy_before':before,'energy_after':energy,
       'proposed':proposed,'action':action,'forced':forced,'layer0':layer0,
       'panic':panic,'panic_trigger':panic_now,'released':released,
       'pred_error':round(pe,3),'pe_sum2':round(sum(pes[-2:]),3),
       'c_update':c_upd,'c_read':[round(x,2) for x in a.c['read']],
       'c_rest':[round(x,2) for x in a.c['rest']],'dead':energy<=0}
  rows.append(row)
  print(f'seed{seed} t{t:02d} {"REV" if reverse else "norm":4s} prop={proposed:4s} act={action:4s} E {before:.0f}->{energy:.0f} PE={pe:.2f} L0={layer0} Cread={a.c["read"]}')
  if energy<=0: break
 after=[r for r in rows if r['tick']>REVERSE_AT]
 free_after=[r for r in after if not r['forced']]
 return {'seed':seed,'rows':rows,'survival':len(rows),'final_energy':energy,
         'dead':bool(rows and rows[-1]['dead']),'panic_tick':panic_tick,
         'forced_count':sum(1 for r in rows if r['forced']),
         'post_release_ticks':len(free_after),
         'post_release_actions':{x:sum(1 for r in free_after if r['action']==x) for x in ACTIONS},
         'post_release_proposed':{x:sum(1 for r in free_after if r['proposed']==x) for x in ACTIONS},
         'c_updates':a.c_updates,'c_read_final':[round(x,2) for x in a.c['read']]}

if __name__=='__main__':
 out=[run(s) for s in (1,2,3)]
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('\nSUMMARY')
 for r in out:
  print(r['seed'],'surv',r['survival'],'E',r['final_energy'],'dead',r['dead'],
        'panic',r['panic_tick'],'forced',r['forced_count'],'free_after',r['post_release_ticks'],
        'post',r['post_release_actions'],'props',r['post_release_proposed'],
        'c_updates',len(r['c_updates']),'Cread',r['c_read_final'])
 print('SAVED',OUT)
