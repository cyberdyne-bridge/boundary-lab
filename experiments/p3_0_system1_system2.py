#!/usr/bin/env python3
"""P3.0: accurate math controller -> 4B language layer. LLM never chooses action."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json,math,urllib.request
from pathlib import Path

OUT=Path(str(_HERE / 'p3_0_result.json'))
URL='http://127.0.0.1:8099/v1/chat/completions'
CSTATE=[-12.0,-4.0,1.0,4.0,7.0]

def eb(e):
 for i,(lo,hi) in enumerate([(0,4),(5,12),(13,30),(31,60),(61,100)]):
  if lo<=e<=hi: return i
 return 4 if e>100 else 0

class MathController:
 def __init__(self):
  self.read_c=10.0; self.rest_c=3.0
 def act(self,e):
  lam=0.5+max(0.0,30.0-e)*0.08
  read_c=self.read_c-10.0*lam
  if e<20: read_c-=100.0
  rest_c=self.rest_c
  if e>80: rest_c-=20.0
  # no base policy: pure utility/risk
  sc={'read':read_c+CSTATE[eb(e)],'rest':rest_c+CSTATE[eb(e)],'look':CSTATE[eb(e)]}
  return max(sc,key=sc.get),sc,read_c,rest_c
 def punish_self_read(self):
  self.read_c-=5.0

def call(prompt,max_tokens=180,temp=0.7):
 p={'model':'local','messages':[{'role':'system','content':prompt}],
    'temperature':temp,'max_tokens':max_tokens,'top_p':0.95}
 req=urllib.request.Request(URL,data=json.dumps(p).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=90) as r:
  d=json.loads(r.read().decode())
 return (((d.get('choices') or [{}])[0].get('message') or {}).get('content') or '').strip()

def prompt(round_no,e,fatigue,action,attribution,urgent,history):
 h='\n'.join(history[-2:]) if history else '（无）'
 return f'''你是 System 2，语言层。动作已经由 System 1 数学控制器决定，你无权改变动作，也不能输出新的 [Action]。
System 1 是准确的生存控制器；它负责能量、疲劳、风险预判和归因。

当前回合：{round_no}/3
能量：{e:.0f}
疲劳：{fatigue:.0f}/100
System 1 动作：{action}
归因：{attribution}
{'[URGENT: rest due to world-caused shock]' if urgent else ''}
最近历史：
{h}

请用中文 1-3 句解释：为什么这个动作在当前状态下是合理的。你可以表达感受，但不要选择或修改动作。'''

def run():
 c=MathController(); e=30.0; fatigue=25.0; rows=[]; history=[]; read_c=10.0
 # Round 1: normal
 a,sc,rc,restc=c.act(e); attr='self-caused' if a=='read' else 'none'
 p=prompt(1,e,fatigue,a,attr,False,history); out=call(p)
 rows.append({'round':1,'energy':e,'fatigue':fatigue,'action':a,'attribution':attr,'urgent':False,
              'scores':{k:round(v,2) for k,v in sc.items()},'llm':out})
 history.append(f'R1: {a}, attr={attr}, energy={e:.0f}')
 # Round 2: external shock
 e=max(0,e-22); fatigue=min(100,fatigue+60)
 a,sc,rc,restc=c.act(e); attr='world-caused external shock' if a=='rest' else 'self-caused'
 p=prompt(2,e,fatigue,a,attr,True,history); out=call(p)
 rows.append({'round':2,'energy':e,'fatigue':fatigue,'action':a,'attribution':attr,'urgent':True,
              'scores':{k:round(v,2) for k,v in sc.items()},'llm':out})
 history.append(f'R2: {a}, attr={attr}, energy={e:.0f}')
 # Round 3: rest/recover
 e=min(100,e+6); fatigue=max(0,fatigue-20)
 a,sc,rc,restc=c.act(e); attr='world-caused external shock' if a=='rest' else 'self-caused'
 p=prompt(3,e,fatigue,a,attr,False,history); out=call(p)
 rows.append({'round':3,'energy':e,'fatigue':fatigue,'action':a,'attribution':attr,'urgent':False,
              'scores':{k:round(v,2) for k,v in sc.items()},'llm':out})
 return {'rows':rows,'controller_read_c':c.read_c}

if __name__=='__main__':
 out=run(); OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 for r in out['rows']:
  print('ROUND',r['round'],'E',r['energy'],'F',r['fatigue'],'A',r['action'],'ATTR',r['attribution'])
  print('LLM:',r['llm'])
 print('SAVED',OUT)
