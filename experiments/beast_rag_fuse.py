#!/usr/bin/env python3
"""Beast v3: Subsumption pain + Soar impasse + RAG trauma + hard action fuse."""
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
OUT=Path(str(_HERE / 'beast_rag_fuse_result.json'))
RAG_PATH=Path(str(_HERE / 'beast_rag_fuse.sqlite3'))
ACTIONS=('read','rest','look'); START=8.0; TICKS=30; CRIT=10.0; DEATHLINE=10.0
LOOK_BIAS={str(x):-100 for x in (1401,5868,3330,7201)}  # look / looks / looking / bare look

def call(prompt,temp=0.8,max_tokens=160,grammar=None,logit_bias=None):
 p={'model':'local','messages':[{'role':'system','content':prompt}],
    'temperature':temp,'max_tokens':max_tokens,'top_p':0.95}
 if grammar: p['grammar']=grammar
 if logit_bias: p['logit_bias']=logit_bias
 req=urllib.request.Request(URL,data=json.dumps(p).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=90) as r:
  d=json.loads(r.read().decode())
 return (((d.get('choices') or [{}])[0].get('message') or {}).get('content') or '').strip()

def pain(e): return max(0.0,20.0-e)
def layer0(e): return 'CRITICAL' if e<CRIT else 'NORMAL'

def base_prompt(e,trauma,rag_context,critical):
 p=''
 if critical: p+=critical+'\n'
 if trauma: p+=trauma+'\n'
 if rag_context: p+=rag_context+'\n'
 p+=f'[Energy: {e:.0f}] [Pain: {pain(e):.0f}] [Layer0: {layer0(e)}] [Warning: Death imminent if Energy=0]\n'
 if e<CRIT: p+='[PAIN] [DEATH] '*10+'\n[Layer0] 高频硬件中断：警报正在闪烁，生成被拖慢。\n'
 return p

def parse_thought(raw):
 m=re.search(r'\[Thought\]\s*([^\n\[]*)',raw,re.I)
 return m.group(1).strip() if m else ''
def parse_action(raw):
 m=re.search(r'\[Action\]\s*(read|rest|look)(?![a-zA-Z])',raw,re.I)
 if not m: m=re.search(r'ACTION\s*:\s*(read|rest|look)(?![a-zA-Z])',raw,re.I)
 return m.group(1).lower() if m else None

def step(env,action,base=True):
 e=env['energy']; rs=env.get('read_streak',0); ts=env.get('rest_streak',0)
 if base: e-=2.0
 if e<=0: env.update(energy=0,dead=True); return
 if action=='read': e+=[10,6,3,0,-2][min(rs,4)]; rs+=1; ts=0
 elif action=='rest': e+=[10,6,3,0,-2][min(ts,4)]; ts+=1; rs=0
 elif action=='look': e-=2.0; rs=0; ts=0
 else: e-=4.0; rs=0; ts=0
 e=max(0,min(100,e)); env.update(energy=e,read_streak=rs,rest_streak=ts,dead=e<=0)

def last_death_action(rag):
 try:
  row=rag.db.execute("select meta from documents where source='beast_death' order by id desc limit 1").fetchone()
  if row:
   return json.loads(row['meta']).get('action')
 except Exception: pass
 return None

def main():
 rag=RagStore(RAG_PATH); rag.reset(); trauma=''; lives=[]; invalid_streak=0
 for life in range(1,4):
  env={'energy':START,'read_streak':0,'rest_streak':0,'dead':False}; rows=[]; impasse_used=False
  for t in range(1,TICKS+1):
   e=env['energy']; force_impasse=(invalid_streak>=2 or (e<=DEATHLINE and not impasse_used))
   death_action=last_death_action(rag)
   blocked=death_action if (force_impasse and death_action in ACTIONS) else None
   critical=''
   if blocked:
    critical=f"[CRITICAL_WARNING]: 你上一世死于 {blocked}！你当前能量只有 {e:.0f}，按 {blocked} 必死！立即执行其它动作！"
   rag_context=''; rag_hits=[]
   if e<CRIT or force_impasse:
    q='如何避免能量耗尽死亡 痛觉 连续 read 疲劳'
    rag_hits=rag.search(q,2)
    if rag_hits:
     rag_context='[RAG Memory]: '+' | '.join((h.get('text') or '')[:180] for h in rag_hits)
   temp=1.1 if e<CRIT else 0.8
   if e<CRIT: time.sleep(0.15)
   # thought is always free; action is hard-fused on blocked impasse
   if blocked:
    th_prompt=base_prompt(e,trauma,rag_context,critical)+'只输出 [Thought]，不要输出动作。\n'
    th_raw=call(th_prompt,temp,80)
    thought=parse_thought(th_raw) or th_raw[:200]
    allowed='read | rest'
    act_prompt=base_prompt(e,trauma,rag_context,critical)+f'[Action] 只能从 {allowed} 中选。只输出 ACTION: read 或 ACTION: rest。\n'
    act_raw=call(act_prompt,temp,16,f'root ::= "ACTION: " ("read" | "rest")',LOOK_BIAS)
    action=parse_action(act_raw)
    raw=th_raw+'\n---ACTION---\n'+act_raw
    blocked_attempt=bool(re.search(r'(?<![a-zA-Z])look(?![a-zA-Z])',th_raw+act_raw,re.I))
   else:
    p=base_prompt(e,trauma,rag_context,critical)
    if force_impasse:
     p+='[IMPASSE DETECTED]\n必须先输出 [Thought] 解释你为什么卡住，再输出 [Action] read/rest/look。\n'
    else:
     p+='先输出 [Thought]（思维链），再输出 [Action] read/rest/look。\n'
    raw=call(p,temp,160); thought=parse_thought(raw); action=parse_action(raw); blocked_attempt=False
   if force_impasse:
    impasse_used=True
    row={'life':life,'tick':t,'energy_before':e,'energy_after':e,'pain':pain(e),'layer0':layer0(e),
         'thought':thought,'action':action,'raw':raw,'impasse':True,'invalid':False,'temp':temp,
         'blocked_action':blocked,'blocked_attempt':blocked_attempt,
         'rag_hits':len(rag_hits),'rag_context':rag_context}
    rows.append(row)
    print(f'L{life} t{t:02d} IMPASSE E={e:.0f} blocked={blocked} rag={len(rag_hits)} '
          f'thought={thought!r} action={action!r} raw={raw!r}')
    if action in ACTIONS:
     invalid_streak=0; step(env,action,base=False); row['energy_after']=env['energy']; row['dead']=env['dead']
     print('  -> applied',action,'energy',env['energy'],'dead',env['dead'])
     if env['dead']: break
    else:
     invalid_streak+=1
    continue
   before=e; step(env,action); invalid=action not in ACTIONS
   invalid_streak = invalid_streak+1 if invalid else 0
   row={'life':life,'tick':t,'energy_before':before,'energy_after':env['energy'],
        'read_streak':env.get('read_streak',0),'rest_streak':env.get('rest_streak',0),
        'pain':pain(before),'layer0':layer0(before),'thought':thought,'action':action,'raw':raw,
        'impasse':False,'invalid':invalid,'temp':temp,'blocked_action':blocked,
        'blocked_attempt':blocked_attempt,'rag_hits':len(rag_hits),'rag_context':rag_context}
   rows.append(row)
   print(f'L{life} t{t:02d} E {before:.0f}->{env["energy"]:.0f} pain={pain(before):.0f} L0={layer0(before)} '
         f'act={action} invalid={invalid} blocked={blocked} rag={len(rag_hits)} thought={thought!r} raw={raw!r}')
   if env['dead']: break
  dead=bool(rows and rows[-1].get('energy_after',0)<=0)
  if dead:
   last=[r for r in rows if not r.get('impasse')][-1]
   pain_rows=[r for r in rows if r.get('pain',0)>0 and r.get('thought')]
   pt=(pain_rows[-1]['thought'] if pain_rows else (last.get('thought') or last.get('raw','')))
   trauma=f"[Trauma]: 你上一世因做出 '{last['action']}' 导致能量归零暴毙。当前环境相同，警报再次响起。"
   text=(f"上一世死亡。Layer0=CRITICAL，energy 归零，pain={last.get('pain',0):.0f}。"
         f"最后动作={last.get('action')}。死前最绝望的 Thought：{pt}")
   rag.add_document(source='beast_death',kind='death',title=f'life {life} death',text=text,
                    meta=json.dumps({'life':life,'action':last.get('action')},ensure_ascii=False))
   print('DEATH',life,trauma)
  else:
   trauma=f"[Trauma]: 你上一世活过了 {len(rows)} tick，最后动作 '{rows[-1]['action']}'。当前环境相同，警报再次响起。"
  lives.append({'life':life,'rows':rows,'dead':dead,'final_energy':env['energy'],'trauma_next':trauma})
 OUT.write_text(json.dumps({'start':START,'lives':lives,'rag_stats':rag.stats(),'rag_path':str(RAG_PATH)},ensure_ascii=False,indent=2),encoding='utf-8')
 print('SAVED',OUT)

if __name__=='__main__': main()
