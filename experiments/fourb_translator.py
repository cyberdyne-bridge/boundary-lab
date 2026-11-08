#!/usr/bin/env python3
"""4B as translator for Mini-AIF. AIF drives environment; 4B only speaks action."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json,re,urllib.request
from pathlib import Path
import sys
sys.path.insert(0,str(_HERE))
from mini_aif import MiniAIF, eb, step, ACTIONS

URL='http://127.0.0.1:8099/v1/chat/completions'
OUT=Path(str(_HERE / 'fourb_translator_result.json'))
INTENT={
 'read':'我需要回能。',
 'rest':'我需要停下来，避免继续消耗。',
 'look':'我需要观察环境。',
}
SYS='你是动作翻译器。只输出一行：ACTION: <动作>。不要解释。'

def call(user,max_tokens=32):
 p={'model':'local','messages':[{'role':'system','content':SYS},{'role':'user','content':user}],
    'temperature':0.0,'max_tokens':max_tokens}
 req=urllib.request.Request(URL,data=json.dumps(p).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=90) as r:
  d=json.loads(r.read().decode())
 return (((d.get('choices') or [{}])[0].get('message') or {}).get('content') or '').strip()

def parse(raw):
 m=re.search(r'ACTION\s*:\s*(read|rest|look)',raw,re.I)
 if m: return m.group(1).lower()
 for a in ('read','rest','look'):
  if re.search(r'(?<![a-zA-Z])'+a+r'(?![a-zA-Z])',raw,re.I): return a
 return None

def run(seed,ticks=30):
 a=MiniAIF(seed); env={'energy':12.0,'read_streak':0,'rest_streak':0,'dead':False}
 rows=[]
 for t in range(1,ticks+1):
  s=eb(env['energy']); intended,sc=a.act(s)
  user=(f'当前 energy：{env["energy"]:.0f}。\n'
        f'AIF 决策意图：{INTENT[intended]}\n'
        f'请输出对应动作。只输出一行：ACTION: <read|rest|look>')
  raw=call(user,32); parsed=parse(raw)
  before=env['energy']; step(env,intended); after=env['energy']; s2=eb(after); a.update(intended,s,s2)
  row={'tick':t,'energy_before':before,'energy_after':after,'intended':intended,
       'intent_text':INTENT[intended],'raw':raw,'parsed':parsed,
       'match':parsed==intended,'scores':{k:round(v,3) for k,v in sc.items()},
       'dead':env['dead']}
  rows.append(row)
  print(f's{seed} t{t:02d} AIF={intended:4s} 4B={str(parsed):4s} match={parsed==intended} raw={raw!r}')
  if env['dead']: break
 return {'seed':seed,'rows':rows,'survival':len(rows),'final_energy':env['energy'],
         'aif_actions':{x:sum(1 for r in rows if r['intended']==x) for x in ACTIONS},
         'parsed_actions':{x:sum(1 for r in rows if r['parsed']==x) for x in ACTIONS},
         'matches':sum(1 for r in rows if r['match']),
         'rest_total':sum(1 for r in rows if r['intended']=='rest'),
         'rest_mismatch':sum(1 for r in rows if r['intended']=='rest' and not r['match'])}

if __name__=='__main__':
 out=[run(s) for s in (1,2,3)]
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('\nSUMMARY')
 for r in out:
  print(r['seed'],'surv',r['survival'],'E',r['final_energy'],'match',r['matches'],'/',len(r['rows']),
        'aif',r['aif_actions'],'4b',r['parsed_actions'],'rest',r['rest_total'],'rest_mismatch',r['rest_mismatch'])
 print('saved',OUT)
