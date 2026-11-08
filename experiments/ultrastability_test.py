#!/usr/bin/env python3
"""Ashby-style test: reverse energy contingency, compare online Q re-learning vs frozen Q."""
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import copy, json, sys
from pathlib import Path
sys.path.insert(0,str(_HERE))
from vm_q_loop import VMQLoop

def last_energy(lp):
    r=lp.db.execute('select energy,action from ticks order by id desc limit 1').fetchone()
    return (round(r['energy'],1), r['action']) if r else (None,None)

def run(seed):
    tag=f'ultra_s{seed}'
    base=VMQLoop(f'{tag}_train', seed=seed)
    base.set_perturb(False)
    base.train(3,40, eps=0.35, alpha=0.2)
    q=copy.deepcopy(base.Q); sm=copy.deepcopy(base.self_model)
    base_sum=base.summary(); base_end=last_energy(base)
    # adaptive
    ad=VMQLoop(f'{tag}_adapt', seed=seed)
    ad.Q=q; ad.self_model=sm
    ad.set_perturb(True)
    ad.train(1,60, eps=0.50, alpha=0.20)
    ad_sum=ad.summary(); ad_end=last_energy(ad)
    # frozen: same Q, no update
    fr=VMQLoop(f'{tag}_frozen', seed=seed)
    fr.Q=copy.deepcopy(q); fr.self_model=copy.deepcopy(sm)
    fr.set_perturb(True)
    fr.train(1,60, eps=0.0, alpha=0.0)
    fr_sum=fr.summary(); fr_end=last_energy(fr)
    out={'seed':seed,'base_end':base_end,'adapt_end':ad_end,'frozen_end':fr_end,
         'base':base_sum,'adapt':ad_sum,'frozen':fr_sum}
    print(json.dumps(out,ensure_ascii=False))
    return out

if __name__=='__main__':
    out=[run(int(x)) for x in sys.argv[1:]] or [run(1)]
    Path(str(_HERE / 'ultrastability_result.json')).write_text(
        json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
