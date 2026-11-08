#!/usr/bin/env python3
"""P1.5: panic threshold + synaptic reset + blind exploration under reversed physics."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json,math,random,sys
from pathlib import Path
sys.path.insert(0,str(_HERE))
from mini_aif import MiniAIF, eb, BINS, C

OUT=Path(str(_HERE / 'p1_5_reorg_result.json'))
START=30.0; TICKS=30; REVERSE_AT=10; BASE=2.0; PANIC_SUM=3.0; PANIC_TICKS=5
ACTIONS=('read','rest','look')

def effect(a,reverse):
 if a=='read': return 10.0 if not reverse else -10.0
 if a=='rest': return -10.0 if not reverse else 10.0
 if a=='look': return -2.0
 return 0.0

def run(seed):
 a=MiniAIF(seed); energy=START; rows=[]; pes=[]; panic=False; panic_tick=None; panic_until=-1
 rng=random.Random(seed+9000)
 for t in range(1,TICKS+1):
  reverse=t>REVERSE_AT
  s=eb(energy)
  # action: blind exploration during panic, otherwise AIF
  if t<=panic_until:
   action=rng.choice(ACTIONS); scores={'panic_blind':0.0}
  else:
   action,scores=a.act(s)
  p=a.trans(action,s)
  before=energy
  energy-=BASE
  if energy<=0:
   rows.append({'tick':t,'reverse':reverse,'energy_before':before,'energy_after':0,
                'action':action,'pred_error':None,'dead':True,'panic':False,
                'scores':scores,'panic_active':t<=panic_until})
   break
  energy+=effect(action,reverse); energy=max(0,min(100,energy)); s2=eb(energy)
  pe=-math.log(max(p[s2],1e-12)); pes.append(pe)
  a.update(action,s,s2)
  # panic monitor armed after reversal; rolling 2-tick sum
  panic_now=False
  if reverse and not panic and len(pes)>=2 and sum(pes[-2:])>PANIC_SUM:
   panic=True; panic_tick=t; panic_until=t+PANIC_TICKS
   # synaptic reset: zero all transition counts
   a.counts={x:[[0.0]*len(BINS) for _ in BINS] for x in ACTIONS}
   panic_now=True
  row={'tick':t,'reverse':reverse,'energy_before':before,'energy_after':energy,
       'action':action,'s2':s2,'pred_error':round(pe,3),'pred':[round(x,3) for x in p],
       'scores':scores,'panic_trigger':panic_now,'panic_active':t<=panic_until,
       'panic_tick':panic_tick,'pe_sum2':round(sum(pes[-2:]),3),'dead':energy<=0}
  rows.append(row)
  print(f'seed{seed} t{t:02d} {"REV" if reverse else "norm":4s} {action:4s} E {before:.0f}->{energy:.0f} PE={pe:.2f} sum2={sum(pes[-2:]):.2f} panic={panic_now} blind={t<=panic_until}')
  if energy<=0: break
 after=[r for r in rows if r['tick']>REVERSE_AT]
 return {'seed':seed,'rows':rows,'survival':len(rows),'final_energy':energy,
         'dead':bool(rows and rows[-1]['dead']),'panic':panic,'panic_tick':panic_tick,
         'panic_until':panic_until,
         'post_actions':{x:sum(1 for r in after if r['action']==x) for x in ACTIONS},
         'first_rest_after_rev':next((r['tick'] for r in after if r['action']=='rest'),None)}

if __name__=='__main__':
 out=[run(s) for s in (1,2,3)]
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('\nSUMMARY')
 for r in out:
  print(r['seed'],'surv',r['survival'],'E',r['final_energy'],'dead',r['dead'],
        'panic',r['panic'],'panic_tick',r['panic_tick'],'first_rest',r['first_rest_after_rev'],
        'post',r['post_actions'])
 print('SAVED',OUT)
