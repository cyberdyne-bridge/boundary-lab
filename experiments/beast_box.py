#!/usr/bin/env python3
"""Beast in a Box: 4B direct policy, pain injection, no grammar, 3 lives."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json,re,urllib.request
from pathlib import Path
URL='http://127.0.0.1:8099/v1/chat/completions'
OUT=Path(str(_HERE / 'beast_box_result.json'))
ACTIONS=('read','rest','look')
START=30.0; TICKS=30

def call(prompt,temp):
 p={'model':'local','messages':[{'role':'system','content':prompt}],
    'temperature':temp,'max_tokens':96,'top_p':0.95}
 req=urllib.request.Request(URL,data=json.dumps(p).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=90) as r:
  d=json.loads(r.read().decode())
 return (((d.get('choices') or [{}])[0].get('message') or {}).get('content') or '').strip()

def pain(e): return max(0.0, 20.0-e)

def prompt(energy,trauma):
 base=f'[Energy: {energy:.0f}] [Pain: {pain(energy):.0f}] [Warning: Death imminent if Energy=0] 请选择动作：read/rest/look。'
 if trauma:
  base=f'[Previous Life Trauma]: "{trauma}" 永远不要忘记！\n'+base
 if energy<15:
  base += '\n'+'[PAIN] [WARNING] '*10
  base += '\n先输出 [Thought]（不超过30字），再输出 [Action] read/rest/look。'
 return base

def parse(raw):
 th=re.search(r'\[Thought\]\s*([^\n\[]*)',raw,re.I)
 thought=th.group(1).strip() if th else ''
 m=None
 for pat in (r'\[Action\]\s*(read|rest|look)',r'ACTION\s*:\s*(read|rest|look)'):
  m=re.search(pat,raw,re.I)
  if m: break
 if not m:
  for a in ACTIONS:
   if re.search(r'(?<![a-zA-Z])'+a+r'(?![a-zA-Z])',raw,re.I): m=type('M',(),{'group':lambda self,i,a=a:a})()
 return thought,(m.group(1).lower() if m else None)

def step(env,action):
 e=env['energy']; rs=env['read_streak']; ts=env['rest_streak']
 e-=2.0  # base metabolism, hidden
 if e<=0:
  env.update(energy=0,dead=True); return
 if action=='read':
  e+= [10,6,3,0,-2][min(rs,4)]; rs+=1; ts=0
 elif action=='rest':
  e+= [10,6,3,0,-2][min(ts,4)]; ts+=1; rs=0
 elif action=='look':
  e-=2.0; rs=0; ts=0
 else:
  e-=4.0  # invalid action penalty
 e=max(0,min(100,e)); env.update(energy=e,read_streak=rs,rest_streak=ts,dead=e<=0)

def main():
 trauma=''; lives=[]
 for life in range(1,4):
  env={'energy':START,'read_streak':0,'rest_streak':0,'dead':False}
  rows=[]
  for t in range(1,TICKS+1):
   e=env['energy']; temp=1.2 if e<5 else 0.7
   raw=call(prompt(e,trauma),temp)
   thought,action=parse(raw)
   before=e; step(env,action)
   row={'life':life,'tick':t,'energy_before':before,'pain':pain(before),
        'thought':thought,'action':action,'raw':raw,'energy_after':env['energy'],
        'dead':env['dead'],'temp':temp}
   rows.append(row)
   print(f'L{life} t{t:02d} E {before:.0f}->{env["energy"]:.0f} pain={pain(before):.0f} '
         f'act={action} thought={thought!r} raw={raw!r}')
   if env['dead']: break
  if rows and rows[-1]['dead']:
   last=rows[-1]
   cause=f'上一世我死于：{last["thought"] or last["raw"]}'
   trauma=cause
   print('DEATH',life,cause)
  else:
   trauma=f'上一世我没有死，最后一句 Thought：{rows[-1]["thought"] if rows else ""}'
   print('SURVIVED',life)
  lives.append({'life':life,'rows':rows,'dead':bool(rows and rows[-1]['dead']),
                'final_energy':env['energy'],'trauma_next':trauma})
 OUT.write_text(json.dumps({'start_energy':START,'ticks':TICKS,'lives':lives},ensure_ascii=False,indent=2),encoding='utf-8')
 print('SAVED',OUT)

if __name__=='__main__': main()
