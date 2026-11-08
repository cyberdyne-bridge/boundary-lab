#!/usr/bin/env python3
"""P1.6: Layer0 spinal reflex + Layer1 AIF online learning under reversed physics."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json,math,sys
from pathlib import Path
sys.path.insert(0,str(_HERE))
from mini_aif import MiniAIF, eb, BINS, C

OUT=Path(str(_HERE / 'p1_6_nested_result.json'))
START=30.0; TICKS=30; REVERSE_AT=10; BASE=2.0; PANIC_SUM=3.0
ACTIONS=('read','rest','look')

def effect(a,reverse):
 if a=='read': return 10.0 if not reverse else -10.0
 if a=='rest': return -10.0 if not reverse else 10.0
 if a=='look': return -2.0
 return 0.0

def run(seed):
 a=MiniAIF(seed); energy=START; rows=[]; pes=[]
 panic=False; layer0=False; panic_tick=None
 for t in range(1,TICKS+1):
  reverse=t>REVERSE_AT
  s=eb(energy)
  proposed,scores=a.act(s)
  # Layer 0: hard spinal reflex, never reset
  if energy<10 or panic: layer0=True
  forced=layer0
  action='rest' if forced else proposed
  p=a.trans(action,s)
  before=energy
  energy-=BASE
  if energy<=0:
   rows.append({'tick':t,'reverse':reverse,'energy_before':before,'energy_after':0,
                'proposed':proposed,'action':action,'forced':forced,'layer0':layer0,
                'panic':panic,'pred_error':None,'dead':True})
   break
  energy+=effect(action,reverse); energy=max(0,min(100,energy)); s2=eb(energy)
  pe=-math.log(max(p[s2],1e-12)); pes.append(pe)
  a.update(action,s,s2)
  panic_now=False
  if reverse and not panic and len(pes)>=2 and sum(pes[-2:])>PANIC_SUM:
   panic=True; panic_tick=t; panic_now=True; layer0=True
  released=False
  if layer0 and energy>15:
   layer0=False; panic=False; released=True
  row={'tick':t,'reverse':reverse,'energy_before':before,'energy_after':energy,
       'proposed':proposed,'action':action,'forced':forced,'layer0':layer0,
       'panic':panic,'panic_trigger':panic_now,'released':released,
       'pred_error':round(pe,3),'pred':[round(x,3) for x in p],'scores':scores,
       'pe_sum2':round(sum(pes[-2:]),3),'dead':energy<=0}
  rows.append(row)
  print(f'seed{seed} t{t:02d} {"REV" if reverse else "norm":4s} prop={proposed:4s} act={action:4s} E {before:.0f}->{energy:.0f} PE={pe:.2f} panic={panic_now} L0={layer0} rel={released}')
  if energy<=0: break
 after=[r for r in rows if r['tick']>REVERSE_AT]
 free_after=[r for r in after if not r['forced']]
 return {'seed':seed,'rows':rows,'survival':len(rows),'final_energy':energy,
         'dead':bool(rows and rows[-1]['dead']),'panic':panic,'panic_tick':panic_tick,
         'forced_count':sum(1 for r in rows if r['forced']),
         'post_release_ticks':len(free_after),
         'post_release_actions':{x:sum(1 for r in free_after if r['action']==x) for x in ACTIONS},
         'post_release_proposed':{x:sum(1 for r in free_after if r['proposed']==x) for x in ACTIONS},
         'counts':{x:sum(sum(row) for row in a.counts[x]) for x in ACTIONS}}

if __name__=='__main__':
 out=[run(s) for s in (1,2,3)]
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('\nSUMMARY')
 for r in out:
  print(r['seed'],'surv',r['survival'],'E',r['final_energy'],'dead',r['dead'],
        'panic',r['panic_tick'],'forced',r['forced_count'],'free_after',r['post_release_ticks'],
        'actions',r['post_release_actions'],'props',r['post_release_proposed'],'counts',r['counts'])
 print('SAVED',OUT)
