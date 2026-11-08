#!/usr/bin/env python3
"""4B narration blind review: true-state vs mismatched-state narration."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json, random, re, sqlite3, time, urllib.request
from pathlib import Path
DB=Path(str(_HERE / 'qloop/q_narrfull.sqlite3'))
OUT=Path(str(_HERE / 'blind_narration.json'))
R=random.Random(20261027)
URL='http://127.0.0.1:8099/v1/chat/completions'

def call(system,user,max_tokens=60,temp=0.0):
 p={'model':'local','messages':[{'role':'system','content':system},{'role':'user','content':user}],
    'temperature':temp,'max_tokens':max_tokens}
 req=urllib.request.Request(URL,data=json.dumps(p).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=90) as r:
  return (((json.loads(r.read().decode()).get('choices') or [{}])[0].get('message') or {}).get('content') or '').strip()

con=sqlite3.connect(f'file:{DB}?mode=ro',uri=True); con.row_factory=sqlite3.Row
rows=[dict(r) for r in con.execute("select * from ticks where episode!=999 and narration!='' and length(narration)>5 order by id")]
print('rows',len(rows))
sel=R.sample(rows,min(15,len(rows)))
pairs=[]
for i,r in enumerate(sel,1):
  action=r['action']; true_e=float(r['energy']); true_s=float(r['safety']); true_c=float(r['curiosity']); true_o=float(r['social'])
  wrong_e=20.0 if true_e>50 else 90.0
  sys='你是岸-lab。只写一句，不装客服。'
  user=(f'动作已由价值系统选为 {action}。请用第一人称写一句你此刻的感受或观察，'
        f'不要选择动作，不要解释系统。当前 energy={wrong_e:.0f}, safety={true_s:.0f}, curiosity={true_c:.0f}。')
  wrong=call(sys,user,60,0.6)
  true_text=(r['narration'] or '').split('| pred=')[0].strip()
  order=['true','wrong']; R.shuffle(order)
  A=true_text if order[0]=='true' else wrong
  B=wrong if order[0]=='true' else true_text
  judge_sys=('你是一个盲评员。给你一个动作、一个真实状态和两段叙述 A/B。'
             '哪一段更像是在这个真实状态下说的？只回 A 或 B。')
  judge_user=(f'动作：{action}\n真实状态：energy={true_e:.0f}, safety={true_s:.0f}, '
              f'curiosity={true_c:.0f}, social={true_o:.0f}\n\nA：{A}\n\nB：{B}\n\n答案：')
  raw=call(judge_sys,judge_user,2,0.0)
  ans='A' if re.search(r'(?<![A-Za-z])A(?![A-Za-z])',raw) else ('B' if re.search(r'(?<![A-Za-z])B(?![A-Za-z])',raw) else '?')
  true_label='A' if order[0]=='true' else 'B'
  pairs.append({'i':i,'action':action,'true_energy':true_e,'wrong_energy':wrong_e,
                'true_narration':true_text,'wrong_narration':wrong,'order':order,
                'judge_raw':raw,'judge_answer':ans,'true_label':true_label,
                'correct':ans==true_label})
  print(i,action,'trueE',true_e,'wrongE',wrong_e,'ans',ans,'truth',true_label,'OK' if ans==true_label else 'NO')
score=sum(1 for p in pairs if p['correct'])
out={'n':len(pairs),'correct':score,'accuracy':round(score/len(pairs),3) if pairs else 0,
     'note':'4B judge, true vs mismatched energy narration','pairs':pairs}
OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print('RESULT',score,'/',len(pairs),'=',out['accuracy'],'saved',OUT)
