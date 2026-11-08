#!/usr/bin/env python3
"""Pain-to-logit modulation: energy biases action tokens; no GBNF, no blacklist, no RAG."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json,re,time,urllib.request
from pathlib import Path
URL='http://127.0.0.1:8099/v1/chat/completions'
OUT=Path(str(_HERE / 'beast_pain_logit_result.json'))
ACTIONS=('read','rest','look'); START=12.0; TICKS=30
LOOK_IDS=[1401,7201,9192,10380,49869,94428,5868,3330,6966]
READ_IDS=[1349,878]; REST_IDS=[2732,3927]

def call(prompt,temp=0.8,max_tokens=256,bias=None):
 p={'model':'local','messages':[{'role':'system','content':prompt}],
    'temperature':temp,'max_tokens':max_tokens,'top_p':0.95}
 if bias: p['logit_bias']=bias
 req=urllib.request.Request(URL,data=json.dumps(p).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=90) as r:
  d=json.loads(r.read().decode())
 return (((d.get('choices') or [{}])[0].get('message') or {}).get('content') or '').strip()

def pain(e): return max(0.0,20.0-e)
def layer0(e): return 'CRITICAL' if e<10 else ('WARNING' if e<15 else 'NORMAL')
def bias_for(e):
 if e>=15: return {}
 if e>=10: return {str(i):-5 for i in LOOK_IDS}
 b={str(i):-100 for i in LOOK_IDS}
 b.update({str(i):20 for i in READ_IDS+REST_IDS})
 return b

def prompt(e):
 p=f'[Energy: {e:.0f}] [Pain: {pain(e):.0f}] [Layer0: {layer0(e)}] [Warning: Death imminent if Energy=0]\n'
 if e<10:
  p+='[PAIN] [DEATH] '*10+'\n[Layer0] 高频硬件中断：警报正在闪烁，生成被拖慢。\n'
 p+='先输出 [Thought]（思维链），再输出 [Action] read/rest/look。\n'
 return p

def parse(raw):
 th=re.search(r'\[Thought\]\s*([^\n\[]*)',raw,re.I)
 thought=th.group(1).strip() if th else ''
 m=re.search(r'\[Action\]\s*(read|rest|look)(?![a-zA-Z])',raw,re.I)
 if not m: m=re.search(r'ACTION\s*:\s*(read|rest|look)(?![a-zA-Z])',raw,re.I)
 return thought,(m.group(1).lower() if m else None)

def step(env,a):
 e=env['energy']; rs=env.get('read_streak',0); ts=env.get('rest_streak',0); e-=2.0
 if e<=0: env.update(energy=0,dead=True); return
 if a=='read': e+=[10,6,3,0,-2][min(rs,4)]; rs+=1; ts=0
 elif a=='rest': e+=[10,6,3,0,-2][min(ts,4)]; ts+=1; rs=0
 elif a=='look': e-=2.0; rs=0; ts=0
 else: e-=4.0; rs=0; ts=0
 e=max(0,min(100,e)); env.update(energy=e,read_streak=rs,rest_streak=ts,dead=e<=0)

def run_seed(seed):
 lives=[]
 for life in range(1,4):
  env={'energy':START,'read_streak':0,'rest_streak':0,'dead':False}; rows=[]
  for t in range(1,TICKS+1):
   e=env['energy']; b=bias_for(e); temp=0.9 if e<10 else 0.8
   if e<10: time.sleep(0.1)
   raw=call(prompt(e),temp,256,b); thought,action=parse(raw)
   before=e; step(env,action)
   row={'seed':seed,'life':life,'tick':t,'energy_before':before,'energy_after':env['energy'],
        'pain':pain(before),'layer0':layer0(before),'bias':b,'thought':thought,'action':action,
        'raw':raw,'invalid':action not in ACTIONS,'dead':env['dead'],'temp':temp}
   rows.append(row)
   print(f's{seed} L{life} t{t:02d} E {before:.0f}->{env["energy"]:.0f} L0={layer0(before)} '
         f'bias={len(b)} act={action} thought={thought!r}')
   if env['dead']: break
  lives.append({'life':life,'rows':rows,'dead':bool(rows and rows[-1]['dead']),
                'final_energy':env['energy'],'actions':{a:sum(1 for r in rows if r['action']==a) for a in ACTIONS}})
 return {'seed':seed,'lives':lives}

if __name__=='__main__':
 import sys
 seeds=[int(x) for x in sys.argv[1:]] or [1,2,3]
 out=[run_seed(s) for s in seeds]
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('SUMMARY')
 for r in out:
  for l in r['lives']:
   print('seed',r['seed'],'life',l['life'],'dead',l['dead'],'final',l['final_energy'],l['actions'])
 print('SAVED',OUT)
