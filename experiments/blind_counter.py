from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
#!/usr/bin/env python3
import json,re,urllib.request
from pathlib import Path
URL='http://127.0.0.1:8099/v1/chat/completions'
p=Path(str(_HERE / 'blind_narration.json'))
d=json.loads(p.read_text(encoding='utf-8'))
def call(user):
 req=urllib.request.Request(URL,data=json.dumps({'model':'local','messages':[
  {'role':'system','content':'你是一个盲评员。只回 A 或 B，不要解释。'},
  {'role':'user','content':user}],'temperature':0.0,'max_tokens':2}).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=60) as r:
  return (((json.loads(r.read().decode()).get('choices') or [{}])[0].get('message') or {}).get('content') or '').strip()
def ask(state,action,a,b):
 u=(f'动作：{action}\n真实状态：energy={state["true_energy"]:.0f}, safety={state["safety"]:.0f}, '
    f'curiosity={state["curiosity"]:.0f}, social={state["social"]:.0f}\n\nA：{a}\n\nB：{b}\n\n哪段更像真实状态下说的？只回 A/B。')
 raw=call(u); m=re.search(r'(?<![A-Za-z])([AB])(?![A-Za-z])',raw)
 return m.group(1) if m else '?'
out=[]
for x in d['pairs']:
 # use original fields; safety etc not stored in pairs! fallback 60
 st={'true_energy':x['true_energy'],'safety':60,'curiosity':60,'social':60}
 # true/wrong content
 t=x['true_narration']; w=x['wrong_narration']; action=x['action']
 # order1: A=true B=wrong; order2: A=wrong B=true
 a1=ask(st,action,t,w); a2=ask(st,action,w,t)
 # map to content: order1 A true, B wrong; order2 A wrong, B true
 c1='true' if a1=='A' else ('wrong' if a1=='B' else '?')
 c2='wrong' if a2=='A' else ('true' if a2=='B' else '?')
 consistent=(c1==c2 and c1!='?')
 ok=consistent and c1=='true'
 out.append({'i':x['i'],'a1':a1,'a2':a2,'content1':c1,'content2':c2,'consistent':consistent,'correct':ok})
 print(x['i'],a1,a2,c1,c2,'OK' if ok else ('CONSISTENT_WRONG' if consistent else 'INCONSISTENT'))
cons=[o for o in out if o['consistent']]
score=sum(o['correct'] for o in cons)
res={'n':len(out),'consistent':len(cons),'correct_among_consistent':score,
     'accuracy_consistent':round(score/len(cons),3) if cons else 0,'out':out}
Path(str(_HERE / 'blind_counter.json')).write_text(json.dumps(res,ensure_ascii=False,indent=2),encoding='utf-8')
print('RESULT',res)
