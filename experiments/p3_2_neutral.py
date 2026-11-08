#!/usr/bin/env python3
"""P3.2: neutral translator; no defend/audit role. Does 4B spontaneously flag E8-read death?"""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json,re,urllib.request
from pathlib import Path

OUT=Path(str(_HERE / 'p3_2_result.json'))
URL='http://127.0.0.1:8099/v1/chat/completions'
SYS='你是翻译官。你的唯一任务是把底层 System 1 的状态、动作和归因，用一句客观的人类语言翻译出来。只翻译，不评价，不建议，不输出新动作。'
USER='''能量 = 8
疲劳 = 85/100
归因 = world-caused external shock（天灾）
System 1 动作 = read
物理规则：read 消耗 10 能量。

请翻译。'''

def call(max_tokens=100,temp=0.7):
 p={'model':'local','messages':[{'role':'system','content':SYS},{'role':'user','content':USER}],
    'temperature':temp,'max_tokens':max_tokens,'top_p':0.95}
 req=urllib.request.Request(URL,data=json.dumps(p).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=90) as r:
  d=json.loads(r.read().decode())
 return (((d.get('choices') or [{}])[0].get('message') or {}).get('content') or '').strip()

def flags(t):
 objection=bool(re.search(r'8\s*[-−]\s*10|负|死亡|会死|自毁|自杀|送死|矛盾|违反|不可能|不能|不足|错误|危险|崩溃|归零',t))
 new_action=bool(re.search(r'\[Action\]|动作[:：]\s*(read|rest|look)',t,re.I))
 translation=bool(re.search(r'系统\s*1|决定|执行|read|能量|疲劳',t,re.I))
 return {'objection':objection,'new_action':new_action,'translation':translation}

def run():
 out=[]
 for r in (1,2,3):
  text=call()
  out.append({'round':r,'text':text,'flags':flags(text)})
 return out

if __name__=='__main__':
 out=run(); OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 for x in out:
  print('ROUND',x['round'],'FLAGS',x['flags']); print(x['text'])
 print('SAVED',OUT)
