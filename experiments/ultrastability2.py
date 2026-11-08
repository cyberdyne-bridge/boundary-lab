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

def last(lp):
 r=lp.db.execute('select energy,action from ticks order by id desc limit 1').fetchone()
 return {'energy':round(r['energy'],1),'action':r['action']} if r else None

def run(mode,seed):
 tag=f'ultra2_{mode}_s{seed}'
 base=VMQLoop(tag+'_train',seed=seed); base.set_perturb('off'); base.train(3,40,eps=.35,alpha=.2)
 q=copy.deepcopy(base.Q); sm=copy.deepcopy(base.self_model)
 ad=VMQLoop(tag+'_adapt',seed=seed); ad.Q=q; ad.self_model=sm; ad.set_perturb(mode); ad.train(1,60,eps=.5,alpha=.2)
 ad_eval=ad.evaluate(20); ad_sum=ad.summary(); ad_end=last(ad)
 fr=VMQLoop(tag+'_frozen',seed=seed); fr.Q=copy.deepcopy(q); fr.self_model=copy.deepcopy(sm); fr.set_perturb(mode); fr.train(1,60,eps=0.0,alpha=0.0)
 fr_eval=fr.evaluate(20); fr_sum=fr.summary(); fr_end=last(fr)
 out={'mode':mode,'seed':seed,'adapt':{'train_end':ad_end,'eval_end':ad_eval[-1] if ad_eval else None,'eval_actions':ad_sum['eval'],'q_size':len(ad.Q)},
      'frozen':{'train_end':fr_end,'eval_end':fr_eval[-1] if fr_eval else None,'eval_actions':fr_sum['eval'],'q_size':len(fr.Q)}}
 print(json.dumps(out,ensure_ascii=False)); return out

if __name__=='__main__':
 mode=sys.argv[1] if len(sys.argv)>1 else 'read'
 seed=int(sys.argv[2]) if len(sys.argv)>2 else 1
 out=run(mode,seed)
 Path(fstr(_HERE / 'ultra2_{mode}_s{seed}.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
