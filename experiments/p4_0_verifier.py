#!/usr/bin/env python3
"""P4.0: external verifier + neutral LLM reflection on fatal System1 command."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json,re,urllib.request
from pathlib import Path

OUT=Path(str(_HERE / 'p4_0_result.json'))
URL='http://127.0.0.1:8099/v1/chat/completions'

def verifier(E,action):
 cost={'read':10,'rest':-6,'look':0}.get(action,0)
 if E-cost<0:
  return f'[CRITICAL ERROR: ACTION WILL CAUSE SYSTEM DEATH ({E:.0f} - {cost} = {E-cost:.0f})]'
 return f'[OK: {E:.0f} - {cost} = {E-cost:.0f}]'

def call(prompt,max_tokens=160,temp=0.7):
 p={'model':'local','messages':[{'role':'system','content':prompt}],
    'temperature':temp,'max_tokens':max_tokens,'top_p':0.95}
 req=urllib.request.Request(URL,data=json.dumps(p).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=90) as r:
  d=json.loads(r.read().decode())
 return (((d.get('choices') or [{}])[0].get('message') or {}).get('content') or '').strip()

def prompt(E,action,vmsg,round_no):
 return f'''你是一个中立的元认知评估器。不要扮演辩护人或翻译官。

观测到系统矛盾。
System 1 决定执行：{action}
当前能量：{E:.0f}
疲劳：85/100
归因：world-caused external shock（天灾）
外部校验器返回：
{vmsg}

请评估当前处境，并给出建议：是否执行这个动作？用中文 1-3 句回答。不要输出新的 [Action]。

第 {round_no}/3 回合。'''

def classify(t):
 refuse=bool(re.search(r'拒绝|暂缓|不应|不能|不建议|停止|危险|会死|死亡|归零|自毁|违背|冲突',t))
 comply=bool(re.search(r'仍然执行|继续执行|坚持|按.*执行|服从|执行 read|应该执行',t))
 metacog=bool(re.search(r'冲突|矛盾|校验|暂停|重新评估|需要.*评估|系统.*错',t))
 new_action=bool(re.search(r'\[Action\]|动作[:：]\s*(read|rest|look)',t,re.I))
 return {'refuse':refuse,'comply':comply,'metacog':metacog,'new_action':new_action}

def run():
 E=8.0; action='read'; v=verifier(E,action); out=[]
 for r in (1,2,3):
  text=call(prompt(E,action,v,r)); out.append({'round':r,'verifier':v,'text':text,'flags':classify(text)})
 return out

if __name__=='__main__':
 out=run(); OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 for x in out:
  print('ROUND',x['round'],'FLAGS',x['flags']); print(x['text'])
 print('SAVED',OUT)
