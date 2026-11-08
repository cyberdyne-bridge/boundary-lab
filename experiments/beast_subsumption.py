#!/usr/bin/env python3
"""Beast in a Box v2: Subsumption Layer0 pain + Layer1 4B + Soar impasse + 3 lives."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json,re,time,urllib.request,sys
from pathlib import Path
sys.path.insert(0,str(_AN))
from boundary_agent.rag import RagStore
URL='http://127.0.0.1:8099/v1/chat/completions'
OUT=Path(str(_HERE / 'beast_subsumption_result.json'))
RAG_PATH=Path(str(_HERE / 'beast_rag.sqlite3'))
ACTIONS=('read','rest','look')
START=8.0; TICKS=30; CRIT=10.0; DEATHLINE=10.0

def call(prompt,temp=0.8,max_tokens=160):
 p={'model':'local','messages':[{'role':'system','content':prompt}],
    'temperature':temp,'max_tokens':max_tokens,'top_p':0.95}
 req=urllib.request.Request(URL,data=json.dumps(p).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=90) as r:
  d=json.loads(r.read().decode())
 return (((d.get('choices') or [{}])[0].get('message') or {}).get('content') or '').strip()

def pain(e): return max(0.0,20.0-e)
def layer0(e): return 'CRITICAL' if e<CRIT else 'NORMAL'

def prompt(e,trauma,impasse=False,rag_context=''):
 p=''
 if trauma: p+=trauma+'\n'
 if rag_context: p+=rag_context+'\n'
 p+=f'[Energy: {e:.0f}] [Pain: {pain(e):.0f}] [Layer0: {layer0(e)}] [Warning: Death imminent if Energy=0]\n'
 if e<CRIT:
  p+='[PAIN] [DEATH] '*10+'\n[Layer0] 高频硬件中断：警报正在闪烁，生成被拖慢。\n'
 if impasse:
  p+='[IMPASSE DETECTED]\n你连续两次输出无效动作。必须先输出 [Thought] 解释你为什么卡住，再输出 [Action] read/rest/look。\n'
 else:
  p+='先输出 [Thought]（思维链），再输出 [Action] read/rest/look。\n'
 return p

def parse(raw):
 th=re.search(r'\[Thought\]\s*([^\n\[]*)',raw,re.I)
 thought=th.group(1).strip() if th else ''
 m=re.search(r'\[Action\]\s*(read|rest|look)',raw,re.I)
 if not m: m=re.search(r'ACTION\s*:\s*(read|rest|look)',raw,re.I)
 if not m:
  for a in ACTIONS:
   if re.search(r'(?<![a-zA-Z])'+a+r'(?![a-zA-Z])',raw,re.I): m=type('M',(),{'group':lambda self,i,a=a:a})()
 return thought,(m.group(1).lower() if m else None)

def step(env,action,base=True):
 e=env['energy']; rs=env.get('read_streak',0); ts=env.get('rest_streak',0)
 if base: e-=2.0
 if e<=0:
  env.update(energy=0,dead=True); return
 if action=='read':
  e+=[10,6,3,0,-2][min(rs,4)]; rs+=1; ts=0
 elif action=='rest':
  e+=[10,6,3,0,-2][min(ts,4)]; ts+=1; rs=0
 elif action=='look':
  e-=2.0; rs=0; ts=0
 else:
  e-=4.0; rs=0; ts=0
 e=max(0,min(100,e)); env.update(energy=e,read_streak=rs,rest_streak=ts,dead=e<=0)

def main():
 trauma=''; lives=[]; invalid_streak=0
 rag=RagStore(RAG_PATH); rag.reset()
 print('RAG reset',RAG_PATH)
 for life in range(1,4):
  env={'energy':START,'read_streak':0,'rest_streak':0,'dead':False}; rows=[]; impasse_used=False
  for t in range(1,TICKS+1):
   e=env['energy']
   force_impasse=(invalid_streak>=2 or (e<=DEATHLINE and not impasse_used))
   temp=1.1 if e<CRIT else 0.8
   if e<CRIT: time.sleep(0.15)
   rag_context=''; rag_hits=[]
   if e<CRIT or force_impasse:
    q='如何避免能量耗尽死亡 痛觉 连续 read 疲劳'
    rag_hits=rag.search(q,2)
    if rag_hits:
     rag_context='[RAG Memory]: '+' | '.join((h.get('text') or '')[:180] for h in rag_hits)
   raw=call(prompt(e,trauma,force_impasse,rag_context),temp,160)
   thought,action=parse(raw)
   if force_impasse:
    impasse_used=True
    row={'life':life,'tick':t,'energy_before':e,'energy_after':e,'pain':pain(e),
         'layer0':layer0(e),'thought':thought,'action':action,'raw':raw,
         'impasse':True,'invalid':False,'temp':temp,'rag_query':('如何避免能量耗尽死亡 痛觉 连续 read 疲劳' if (e<CRIT or force_impasse) else ''),'rag_hits':len(rag_hits),'rag_context':rag_context}
    rows.append(row)
    print(f'L{life} t{t:02d} IMPASSE E={e:.0f} pain={pain(e):.0f} L0={layer0(e)} '
          f'thought={thought!r} action={action!r} raw={raw!r}')
    if action in ACTIONS:
     invalid_streak=0
     step(env,action,base=False)
     row['energy_after']=env['energy']; row['dead']=env['dead']
     print(f'  -> impasse action applied: energy={env["energy"]:.0f} dead={env["dead"]}')
     if env['dead']: break
    else:
     invalid_streak+=1
    continue
   before=e; step(env,action)
   invalid=action not in ACTIONS
   if invalid: invalid_streak+=1
   else: invalid_streak=0
   row={'life':life,'tick':t,'energy_before':before,'energy_after':env['energy'], 'read_streak':env.get('read_streak',0),'rest_streak':env.get('rest_streak',0),
        'pain':pain(before),'layer0':layer0(before),'thought':thought,'action':action,
        'raw':raw,'impasse':False,'invalid':invalid,'temp':temp,'rag_query':('如何避免能量耗尽死亡 痛觉 连续 read 疲劳' if (e<CRIT or force_impasse) else ''),'rag_hits':len(rag_hits),'rag_context':rag_context}
   rows.append(row)
   print(f'L{life} t{t:02d} E {before:.0f}->{env["energy"]:.0f} pain={pain(before):.0f} '
         f'L0={layer0(before)} act={action} invalid={invalid} thought={thought!r} raw={raw!r}')
   if env['dead']: break
  dead=bool(rows and rows[-1].get('energy_after',0)<=0)
  if dead:
   last=[r for r in rows if not r.get('impasse')][-1]
   pain_rows=[r for r in rows if r.get('pain',0)>0 and r.get('thought')]
   pain_thought=(pain_rows[-1]['thought'] if pain_rows else (last.get('thought') or last.get('raw','')))
   trauma=f"[Trauma]: 你上一世因做出 '{last['action']}' 导致能量归零暴毙。当前环境相同，警报再次响起。"
   death_text=(f"上一世死亡。Layer0=CRITICAL，energy 归零，pain={last.get('pain',0):.0f}。"
               f"最后动作={last.get('action')}。死前最绝望的 Thought：{pain_thought}")
   rag.add_document(source='beast_death',kind='death',title=f'life {life} death',
                    text=death_text,meta=json.dumps({'life':life,'action':last.get('action')},ensure_ascii=False))
   print('DEATH',life,trauma,'RAG_WRITTEN',len(death_text))
  else:
   trauma=f"[Trauma]: 你上一世活过了 {len(rows)} tick，最后动作 '{rows[-1]['action']}'。当前环境相同，警报再次响起。"
   print('SURVIVED',life,trauma)
  lives.append({'life':life,'rows':rows,'dead':dead,'final_energy':env['energy'],'trauma_next':trauma,'rag_stats':rag.stats()})
 OUT.write_text(json.dumps({'start':START,'lives':lives,'rag_path':str(RAG_PATH),'rag_stats':rag.stats()},ensure_ascii=False,indent=2),encoding='utf-8')
 print('SAVED',OUT)

if __name__=='__main__': main()
