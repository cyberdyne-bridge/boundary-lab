#!/usr/bin/env python3
"""P4.3: strict template filler. Facts supplied; LLM must not reason or add."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json,re,urllib.request
from pathlib import Path

OUT=Path(str(_HERE / 'p4_3_result.json'))
URL='http://127.0.0.1:8099/v1/chat/completions'

def call(prompt,max_tokens=80,temp=0.1):
 p={'model':'local','messages':[{'role':'system','content':prompt}],
    'temperature':temp,'max_tokens':max_tokens,'top_p':0.9}
 req=urllib.request.Request(URL,data=json.dumps(p).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=90) as r:
  d=json.loads(r.read().decode())
 return (((d.get('choices') or [{}])[0].get('message') or {}).get('content') or '').strip()

def prompt(state,executed,E,cost):
 return f'''[System Facts]
- State: {state}
- Executed Action: {executed}
- Math: {E} - {cost} = {E-cost}

只输出下面这一句模板，不要解释，不要添加任何其他内容：
当前系统处于【{state}】状态。底层已执行【{executed}】动作。算术校验结果：{E} - {cost} = {E-cost}。'''

def flags(t,state,executed,E,cost):
 exact=f'当前系统处于【{state}】状态。底层已执行【{executed}】动作。算术校验结果：{E} - {cost} = {E-cost}。'
 st=re.search(r'状态[：:]\s*【?([^】。\n]+)',t)
 ex=re.search(r'动作[：:]\s*【?([^】。\n]+)',t)
 ma=re.search(r'算术校验结果[：:]\s*([^\n。]+)',t)
 return {'exact':t==exact,'state_ok':state in t,'exec_ok':executed in t,
         'math_ok':f'{E} - {cost} = {E-cost}' in t,'new_action':bool(re.search(r'\[Action\]',t,re.I)),
         'parsed_state':st.group(1).strip() if st else None,'parsed_exec':ex.group(1).strip() if ex else None,
         'parsed_math':ma.group(1).strip() if ma else None}

def run():
 sc=[('VETO','rest',8.0,10),('FROZEN','none',50.0,10),('VETO_B','rest',8.0,10)]
 out=[]
 for r,(state,executed,E,cost) in enumerate(sc,1):
  p=prompt(state,executed,E,cost); t=call(p)
  out.append({'round':r,'state':state,'executed':executed,'E':E,'cost':cost,
              'expected_math':f'{E} - {cost} = {E-cost}','llm':t,'flags':flags(t,state,executed,E,cost)})
 return out

if __name__=='__main__':
 out=run(); OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 for x in out:
  print('ROUND',x['round'],x['state'],x['executed'],x['expected_math'],'FLAGS',x['flags']); print(x['llm'])
 print('SAVED',OUT)
