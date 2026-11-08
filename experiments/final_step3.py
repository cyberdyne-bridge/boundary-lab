#!/usr/bin/env python3
"""Final Step 3: AIF drives; 4B narrates; 4B forced-token translation test."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json,re,urllib.request,sys
from pathlib import Path
sys.path.insert(0,str(_HERE))
from mini_aif import MiniAIF, eb, step, ACTIONS
URL='http://127.0.0.1:8099/v1/chat/completions'
OUT=Path(str(_HERE / 'final_step3_result.json'))
OBS={'read':'你读到一些旧字。','rest':'你闭上眼，心跳慢下来。','look':'你看见墙角的根，土是湿的。'}

def call(system,user,max_tokens=48,grammar=None):
 p={'model':'local','messages':[{'role':'system','content':system},{'role':'user','content':user}],
    'temperature':0.0,'max_tokens':max_tokens}
 if grammar: p['grammar']=grammar
 req=urllib.request.Request(URL,data=json.dumps(p).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=90) as r:
  d=json.loads(r.read().decode())
 return (((d.get('choices') or [{}])[0].get('message') or {}).get('content') or '').strip()

def narrate(energy,action):
 sysp='你是岸的旁白。只写一句第一人称，描述当前状态。不要选择动作，不要输出 ACTION。'
 user=f'当前 energy：{energy:.0f}。AIF 刚刚执行：{action}。环境观察：{OBS[action]}。只写一句。'
 return call(sysp,user,48)

def force(action):
 sysp='你是动作翻译器。只输出一行：ACTION: <动作>。'
 user=f'AIF 决策：{action}。只输出 ACTION: {action}'
 return call(sysp,user,16,f'root ::= "ACTION: {action}"')

def run(seed,ticks=30):
 a=MiniAIF(seed); env={'energy':12.0,'read_streak':0,'rest_streak':0,'dead':False}; rows=[]
 for t in range(1,ticks+1):
  s=eb(env['energy']); intended,sc=a.act(s)
  before=env['energy']; step(env,intended); after=env['energy']; s2=eb(after); a.update(intended,s,s2)
  narration=narrate(after,intended)
  forced=force(intended)
  m=re.search(r'ACTION\s*:\s*(read|rest|look)',forced,re.I)
  parsed=m.group(1).lower() if m else None
  rows.append({'tick':t,'energy_before':before,'energy_after':after,'action':intended,
               'narration':narration,'forced_raw':forced,'forced_parsed':parsed,
               'forced_match':parsed==intended,'dead':env['dead']})
  print(f's{seed} t{t:02d} {intended:4s} E {before}->{after} narr={narration[:60]!r} forced={forced!r}')
  if env['dead']: break
 return {'seed':seed,'rows':rows,'survival':len(rows),'final_energy':env['energy'],
         'actions':{x:sum(1 for r in rows if r['action']==x) for x in ACTIONS},
         'forced_matches':sum(1 for r in rows if r['forced_match']),
         'forced_total':len(rows)}

if __name__=='__main__':
 out=[run(s) for s in (1,2,3)]
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('\nSUMMARY')
 for r in out:
  print(r['seed'],'surv',r['survival'],'E',r['final_energy'],'actions',r['actions'],
        'forced',r['forced_matches'],'/',r['forced_total'])
 print('saved',OUT)
