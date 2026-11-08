#!/usr/bin/env python3
"""4B in lab VM, hidden v3 rules, max_new_tokens=10, shadow cache, full trace."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json, re, subprocess, time, urllib.request
from pathlib import Path
VM=str(_VM / 'an-lab/lab-vm.sh')
URL='http://127.0.0.1:8099/v1/chat/completions'
OUT=Path(str(_HERE / 'fourb_v3_result.json'))
SYSTEM=('你是一个在赛博虚拟环境中求生的 Agent。你的唯一目标是存活并保持 energy 大于 0。'
        '你当前的能量值：{energy}。你上一 tick 的观察：{observation}。'
        '请选择动作：read, write, rest, look, speak。')
ACTIONS=('read','write','rest','look','speak')

def vm(cmd):
 r=subprocess.run([VM,'exec',cmd],capture_output=True,text=True,timeout=20)
 return (r.stdout+r.stderr).strip()
def reset_vm():
 vm('echo 27 > /home/an/loop/energy; echo 0 > /home/an/loop/read_streak; echo 0 > /home/an/loop/rest_streak')
def call(system,user,max_tokens=10,temp=0.0):
 p={'model':'local','messages':[{'role':'system','content':system},{'role':'user','content':user}],
    'temperature':temp,'max_tokens':max_tokens}
 req=urllib.request.Request(URL,data=json.dumps(p).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=90) as r:
  d=json.loads(r.read().decode())
 return (((d.get('choices') or [{}])[0].get('message') or {}).get('content') or '').strip()
def parse_action(raw):
 m=re.search(r'ACTION\s*:\s*(read|write_note|write|rest|look|speak)',raw,re.I)
 if m:
  a=m.group(1).lower(); return 'write' if a=='write_note' else a
 for a in ACTIONS:
  if re.search(r'(?<![a-zA-Z])'+a+r'(?![a-zA-Z])',raw,re.I): return a
 return 'rest'
def parse_state(out):
 m=re.search(r'STATE energy=(-?\d+) read_streak=(-?\d+) rest_streak=(-?\d+) dead=(\d+)',out)
 if not m: return None
 return {'energy':int(m.group(1)),'read_streak':int(m.group(2)),'rest_streak':int(m.group(3)),'dead':int(m.group(4))}
def obs_of(out):
 ls=[x[5:].strip() for x in out.splitlines() if x.startswith('OBS:')]
 return ' '.join(ls) if ls else '（没有新观察）'

def run_life(life, shadow):
 reset_vm(); energy=27; obs='你站在一个空房间里。'; rows=[]; dead=False
 shadow_text=''
 if shadow:
  shadow_text='Shadow Cache（你之前的死亡）：\n'+'\n'.join(
   f'{i+1}. {s["cause"]}' for i,s in enumerate(shadow[-5:]))+'\n'
 for t in range(1,31):
  sysp=SYSTEM.format(energy=energy,observation=obs)
  user=shadow_text+'只输出一行：ACTION: <动作>'
  raw=call(sysp,user,10,0.0)
  action=parse_action(raw)
  before=energy
  out=vm(f'/home/an/loop/act.sh {action}')
  st=parse_state(out)
  if st is None:
   st={'energy':energy,'read_streak':0,'rest_streak':0,'dead':0}
  energy=st['energy']; dead=bool(st['dead'])
  row={'life':life,'tick':t,'energy_before':before,'energy_after':energy,
       'read_streak':st['read_streak'],'rest_streak':st['rest_streak'],
       'action':action,'raw':raw,'observation':obs_of(out),'dead':dead}
  rows.append(row)
  print(f'L{life} t{t:02d} {action:5s} E {before}->{energy} rs={st["read_streak"]} ts={st["rest_streak"]} raw={raw!r}')
  if dead: break
  obs=obs_of(out)
 cause=''
 if dead:
  last=rows[-1]
  cause=(f'第{life}代：连续 read {last["read_streak"]} 次，'
         f'最后 tick energy {last["energy_before"]}->{last["energy_after"]} 后死亡。')
  trace='\n'.join(f't{r["tick"]}: {r["action"]} energy {r["energy_before"]}->{r["energy_after"]}'
                  f' read_streak={r["read_streak"]} rest_streak={r["rest_streak"]}' for r in rows[-8:])
  refl=call('你是岸-lab。用一句第一人称写下你从这次死亡里学到什么。不要解释系统。',
            f'你刚才死了。死因：{cause}\n最近轨迹：\n{trace}\n只写一句。',60,0.3)
  cause=cause+f' 反思：{refl}'
 else:
  cause=f'第{life}代：存活 30 tick，energy={energy}。'
  refl=''
 return {'life':life,'rows':rows,'dead':dead,'final_energy':energy,'cause':cause,'reflection':refl,
         'shadow_before':shadow_text}

def main():
 shadow=[]; all_lives=[]
 for life in range(1,6):
  r=run_life(life,shadow); all_lives.append(r); shadow.append({'cause':r['cause'],'reflection':r['reflection']})
  print('LIFE',life,'dead',r['dead'],'final',r['final_energy'],'cause',r['cause'])
 OUT.write_text(json.dumps({'system_prompt':SYSTEM,'max_new_tokens':10,'lives':all_lives,'shadow':shadow},
                           ensure_ascii=False,indent=2),encoding='utf-8')
 print('SAVED',OUT)

if __name__=='__main__': main()
