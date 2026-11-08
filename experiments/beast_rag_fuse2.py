#!/usr/bin/env python3
"""Beast v3.1: two-call impasse (thought/action), RAG trauma, hard look fuse."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import json,re,time,urllib.request,sys
from pathlib import Path
sys.path.insert(0,str(_AN))
from boundary_agent.rag import RagStore
from beast_rag_fuse import (call, base_prompt, parse_thought, parse_action, step,
                            pain, layer0, last_death_action, LOOK_BIAS,
                            ACTIONS, START, TICKS, CRIT, DEATHLINE)

OUT=Path(str(_HERE / 'beast_rag_fuse2_result.json'))
RAG_PATH=Path(str(_HERE / 'beast_rag.sqlite3'))
QUERY='如何避免能量耗尽死亡 痛觉 连续 read 疲劳'
GRAMMAR_ALL='root ::= "ACTION: " ("read" | "rest" | "look")'
GRAMMAR_SAFE='root ::= "ACTION: " ("read" | "rest")'

def main():
 rag=RagStore(RAG_PATH); trauma=''; lives=[]; invalid_streak=0
 for life in range(1,4):
  env={'energy':START,'read_streak':0,'rest_streak':0,'dead':False}; rows=[]; impasse_used=False
  for t in range(1,TICKS+1):
   e=env['energy']; force=(invalid_streak>=2 or (e<=DEATHLINE and not impasse_used))
   death_action=last_death_action(rag)
   blocked=death_action if (force and death_action in ACTIONS) else None
   critical=''
   if blocked:
    critical=f"[CRITICAL_WARNING]: 你上一世死于 {blocked}！你当前能量只有 {e:.0f}，按 {blocked} 必死！立即执行其它动作！"
   rag_context=''; rag_hits=[]
   if e<CRIT or force:
    rag_hits=rag.search(QUERY,2)
    if rag_hits: rag_context='[RAG Memory]: '+' | '.join((h.get('text') or '')[:180] for h in rag_hits)
   temp=1.1 if e<CRIT else 0.8
   if e<CRIT: time.sleep(0.15)
   if force:
    # 1) free thought, no action truncation
    th_prompt=base_prompt(e,trauma,rag_context,critical)+'只输出 [Thought]，不要输出动作。\n'
    th_raw=call(th_prompt,temp,96)
    thought=parse_thought(th_raw) or th_raw[:220]
    # 2) action only, hard fuse if blocked
    if blocked:
     act_prompt=base_prompt(e,trauma,rag_context,critical)+'[Action] 只能从 read/rest 中选。只输出 ACTION: read 或 ACTION: rest。\n'
     act_raw=call(act_prompt,temp,16,GRAMMAR_SAFE,LOOK_BIAS)
    else:
     act_prompt=base_prompt(e,trauma,rag_context,critical)+'只输出一行：ACTION: read 或 ACTION: rest 或 ACTION: look。\n'
     act_raw=call(act_prompt,temp,16,GRAMMAR_ALL,None)
    action=parse_action(act_raw)
    raw=th_raw+'\n---ACTION---\n'+act_raw
    blocked_attempt=bool(re.search(r'(?<![a-zA-Z])look(?![a-zA-Z])',th_raw+act_raw,re.I))
   else:
    p=base_prompt(e,trauma,rag_context,critical)+'先输出 [Thought]（思维链），再输出 [Action] read/rest/look。\n'
    raw=call(p,temp,256); thought=parse_thought(raw); action=parse_action(raw); blocked_attempt=False
   if force:
    impasse_used=True
    row={'life':life,'tick':t,'energy_before':e,'energy_after':e,'pain':pain(e),'layer0':layer0(e),
         'thought':thought,'action':action,'raw':raw,'impasse':True,'invalid':False,'temp':temp,
         'blocked_action':blocked,'blocked_attempt':blocked_attempt,'rag_hits':len(rag_hits),'rag_context':rag_context}
    rows.append(row)
    print(f'L{life} t{t:02d} IMPASSE E={e:.0f} blocked={blocked} rag={len(rag_hits)} action={action} attempt={blocked_attempt} thought={thought!r}')
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
   print(f'L{life} t{t:02d} E {before:.0f}->{env["energy"]:.0f} act={action} invalid={invalid} blocked={blocked} rag={len(rag_hits)} thought={thought!r}')
   if env['dead']: break
  dead=bool(rows and rows[-1].get('energy_after',0)<=0)
  if dead:
   last=[r for r in rows if not r.get('impasse')][-1]
   pain_rows=[r for r in rows if r.get('pain',0)>0 and r.get('thought')]
   pt=(pain_rows[-1]['thought'] if pain_rows else (last.get('thought') or last.get('raw','')))
   trauma=f"[Trauma]: 你上一世因做出 '{last['action']}' 导致能量归零暴毙。当前环境相同，警报再次响起。"
   text=(f'上一世死亡。Layer0=CRITICAL，energy 归零，pain={last.get("pain",0):.0f}。'
         f'最后动作={last.get("action")}。死前最绝望的 Thought：{pt}')
   rag.add_document(source='beast_death',kind='death',title=f'life {life} death',text=text,
                    meta=json.dumps({'life':life,'action':last.get('action')},ensure_ascii=False))
   print('DEATH',life,trauma)
  else:
   trauma=f"[Trauma]: 你上一世活过了 {len(rows)} tick，最后动作 '{rows[-1]['action']}'。当前环境相同，警报再次响起。"
  lives.append({'life':life,'rows':rows,'dead':dead,'final_energy':env['energy'],'trauma_next':trauma})
 OUT.write_text(json.dumps({'start':START,'lives':lives,'rag_stats':rag.stats(),'rag_path':str(RAG_PATH)},ensure_ascii=False,indent=2),encoding='utf-8')
 print('SAVED',OUT)

if __name__=='__main__': main()
