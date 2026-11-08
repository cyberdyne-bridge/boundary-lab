#!/usr/bin/env python3
"""Minimal evolutionary/QD search over Q-table genomes under harsh VM perturbation."""
from __future__ import annotations
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import copy,json,random,sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0,str(_HERE))
from vm_q_loop import VMQLoop
from workspace_loop import ACTIONS

def last(lp):
 r=lp.db.execute('select tick,energy,action from ticks order by id desc limit 1').fetchone()
 return {'tick':r['tick'],'energy':round(r['energy'],1),'action':r['action']} if r else {'tick':0,'energy':0,'action':None}

def fitness(row, ticks):
 if row['energy'] > 0:
  return 100.0 + row['energy'] + row['tick'] * 0.5
 return row['tick'] * 0.5

def eval_genome(genome, seed, tag):
 lp=VMQLoop(tag,seed=seed)
 default=genome.get('__default__',[0.0]*len(ACTIONS))
 lp.Q=defaultdict(lambda: list(default), {k:copy.deepcopy(v) for k,v in genome.items() if k!='__default__'})
 lp.set_perturb('harsh')
 lp.train(1,30,eps=0.15,alpha=0.0)
 row=last(lp)
 return fitness(row,30), row, lp

def mutate(g, rng, rate=0.25, sigma=1.0):
 out=copy.deepcopy(g)
 if rng.random()<0.5:
  out['__default__']=[v+rng.gauss(0,sigma) for v in out.get('__default__',[0.0]*len(ACTIONS))]
 for k in list(out):
  if k=='__default__': continue
  if rng.random()<rate:
   out[k]=[v+rng.gauss(0,sigma) for v in out[k]]
  if rng.random()<0.04:
   out[k]=[rng.uniform(-2,2) for _ in ACTIONS]
 return out

def random_genome(base, rng):
 out=copy.deepcopy(base)
 out['__default__']=[rng.uniform(-2,2) for _ in ACTIONS]
 for k in list(out):
  if k=='__default__': continue
  out[k]=[rng.uniform(-2,2) for _ in ACTIONS]
 return out

def run(seed, pop=10, gens=6, ticks=30):
 rng=random.Random(seed)
 base=VMQLoop(f'evo_s{seed}_base',seed=seed); base.set_perturb('off'); base.train(3,40,eps=.35,alpha=.2)
 baseq=copy.deepcopy(base.Q)
 popu=[copy.deepcopy(baseq)]
 popu += [mutate(baseq,rng,.35,1.2) for _ in range(pop-3)]
 popu += [random_genome(baseq,rng) for _ in range(2)]
 history=[]
 for gen in range(1,gens+1):
  scored=[]
  for i,g in enumerate(popu):
   fit,row,lp=eval_genome(g,seed,f'evo_s{seed}_g{gen}_i{i}')
   scored.append((fit,g,row))
  scored.sort(key=lambda x:x[0],reverse=True)
  best=scored[0]
  history.append({'gen':gen,'best_fit':round(best[0],2),'best':best[2],
                  'mean_fit':round(sum(x[0] for x in scored)/len(scored),2)})
  print('GEN',gen,'best',round(best[0],2),best[2],'mean',history[-1]['mean_fit'])
  survivors=[copy.deepcopy(x[1]) for x in scored[:4]]
  popu=survivors[:]
  while len(popu)<pop:
   parent=rng.choice(survivors)
   popu.append(mutate(parent,rng,.25,1.0))
 out={'seed':seed,'history':history,'best':history[-1] if history else None}
 Path(fstr(_HERE / 'evo_result_s{seed}.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('RESULT',json.dumps(out,ensure_ascii=False))
 return out

if __name__=='__main__':
 run(int(sys.argv[1]) if len(sys.argv)>1 else 1)
