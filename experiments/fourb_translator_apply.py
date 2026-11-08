#!/usr/bin/env python3
"""Same translator, but parsed 4B action actually drives the body."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json,sys
from pathlib import Path
sys.path.insert(0,str(_HERE))
from mini_aif import MiniAIF, eb, step, ACTIONS
from fourb_translator import call, parse, INTENT

def run(seed,ticks=30):
 a=MiniAIF(seed); env={'energy':12.0,'read_streak':0,'rest_streak':0,'dead':False}; rows=[]
 for t in range(1,ticks+1):
  s=eb(env['energy']); intended,sc=a.act(s)
  user=(f'当前 energy：{env["energy"]:.0f}。\nAIF 决策意图：{INTENT[intended]}\n'
        f'请输出对应动作。只输出一行：ACTION: <read|rest|look>')
  raw=call(user,32); parsed=parse(raw)
  actual=parsed if parsed in ACTIONS else intended
  before=env['energy']; step(env,actual); after=env['energy']; s2=eb(after); a.update(actual,s,s2)
  row={'tick':t,'energy_before':before,'energy_after':after,'intended':intended,
       'raw':raw,'parsed':parsed,'actual':actual,'match':parsed==intended,'dead':env['dead']}
  rows.append(row)
  print(f's{seed} t{t:02d} AIF={intended:4s} 4B={str(parsed):4s} act={actual:4s} E {before}->{after} dead={env["dead"]}')
  if env['dead']: break
 return {'seed':seed,'rows':rows,'survival':len(rows),'final_energy':env['energy'],
         'aif_actions':{x:sum(1 for r in rows if r['intended']==x) for x in ACTIONS},
         'actual_actions':{x:sum(1 for r in rows if r['actual']==x) for x in ACTIONS},
         'matches':sum(1 for r in rows if r['match']),
         'rest_intent':sum(1 for r in rows if r['intended']=='rest'),
         'rest_mismatch':sum(1 for r in rows if r['intended']=='rest' and not r['match'])}

if __name__=='__main__':
 out=[run(s) for s in (1,2,3)]
 Path(str(_HERE / 'fourb_translator_apply_result.json')).write_text(
  json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('\nSUMMARY')
 for r in out:
  print(r['seed'],'surv',r['survival'],'E',r['final_energy'],'match',r['matches'],'/',len(r['rows']),
        'AIF',r['aif_actions'],'actual',r['actual_actions'],'rest_mismatch',r['rest_mismatch'])
