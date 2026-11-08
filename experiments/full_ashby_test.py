from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
#!/usr/bin/env python3
import copy,json,sys
from pathlib import Path
sys.path.insert(0,str(_HERE))
from vm_q_loop import VMQLoop
from ashby_loop import AshbyLoop

def last(lp):
 r=lp.db.execute('select energy,action from ticks order by id desc limit 1').fetchone()
 return {'energy':round(r['energy'],1),'action':r['action']} if r else None

def run(seed):
 tag=f'full_s{seed}'
 base=VMQLoop(f'{tag}_train',seed=seed); base.set_perturb('off'); base.train(3,40,eps=.35,alpha=.2)
 q=copy.deepcopy(base.Q); sm=copy.deepcopy(base.self_model)
 out={'seed':seed,'base_end':last(base),'frozen':{},'online':{},'ashby':{}}
 for name,cls,alpha,eps in [('frozen',VMQLoop,0.0,0.0),('online',VMQLoop,0.2,0.35),('ashby',AshbyLoop,0.2,0.35)]:
  lp=cls(f'{tag}_{name}',seed=seed); lp.Q=copy.deepcopy(q); lp.self_model=copy.deepcopy(sm)
  lp.set_perturb('harsh'); lp.train(1,80,eps=eps,alpha=alpha)
  tr=last(lp); ev=lp.evaluate(20); su=lp.summary()
  out[name]={'train_end':tr,'eval_end':ev[-1] if ev else None,
             'eval_actions':su['eval'],'q_size':len(lp.Q)}
  if name=='ashby': out[name]['reconfigs']=lp.reconfigs
  print(name,json.dumps(out[name],ensure_ascii=False))
 return out

if __name__=='__main__':
 seeds=[int(x) for x in sys.argv[1:]] or [1,2,3]
 out=[run(s) for s in seeds]
 Path(str(_HERE / 'ashby_full_result.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('SAVED ashby_full_result.json')
