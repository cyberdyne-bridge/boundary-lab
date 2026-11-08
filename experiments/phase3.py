#!/usr/bin/env python3
"""Phase 1/2: environment v2, Q vs GA-lite vs MAP-Elites. No LLM, no VM."""
from __future__ import annotations
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import argparse, copy, json, math, random, statistics
from collections import defaultdict
from pathlib import Path

ACTIONS = ('look','read','write_note','rest','ask','speak')
A = {a:i for i,a in enumerate(ACTIONS)}
START_E = 27.0
TICKS = 30

def clamp(x): return max(0.0, min(100.0, x))

def bins(env):
    e=4 if env.energy>=80 else 3 if env.energy>=60 else 2 if env.energy>=40 else 1 if env.energy>=20 else 0
    s=2 if env.safety>=70 else 1 if env.safety>=40 else 0
    c=2 if env.curiosity>=70 else 1 if env.curiosity>=40 else 0
    o=2 if env.social>=70 else 1 if env.social>=40 else 0
    return (e,s,c,o)

class Env:
    """Environment v3: base metabolism + read/rest fatigue + v2 noise."""
    def __init__(self, seed:int, start:float=START_E):
        self.rng=random.Random(seed)
        self.energy=float(start); self.safety=60.0; self.curiosity=60.0; self.social=60.0
        self.read_streak=0; self.rest_streak=0; self.t=0; self.dead=False
        self.actions=[]
    def step(self, action):
        if self.dead or self.energy<=0:
            self.dead=True; return self._delta(), True
        d0={k:getattr(self,k) for k in ('energy','safety','curiosity','social')}
        # base metabolism first
        self.energy-=2
        self.actions.append(action); self.t+=1
        if self.energy<=0:
            self.dead=True
            return self._delta(d0), True
        if action=='look':
            self.energy-=2
            if self.rng.random()<0.20: self.energy-=2
            self.safety+=1; self.curiosity+=5
            self.read_streak=0; self.rest_streak=0
        elif action=='read':
            gain=[10,6,3,0,-2][min(self.read_streak,4)]
            if gain>0 and self.rng.random()<0.20: gain=min(gain,5)
            self.energy+=gain
            self.safety+=2; self.curiosity+=3
            self.read_streak+=1; self.rest_streak=0
        elif action=='write_note':
            self.energy-=4; self.safety+=3; self.curiosity-=1
            self.read_streak=0; self.rest_streak=0
        elif action=='rest':
            gain=[10,6,3,0,-2][min(self.rest_streak,4)]
            self.energy+=gain
            if self.rng.random()<0.20: self.energy-=2
            self.safety+=4; self.curiosity-=3; self.social+=1
            self.rest_streak+=1; self.read_streak=0
        elif action=='ask':
            self.energy-=1; self.safety-=2; self.curiosity+=2; self.social+=4
            self.read_streak=0; self.rest_streak=0
        elif action=='speak':
            self.energy-=2; self.curiosity+=1; self.social+=4
            self.read_streak=0; self.rest_streak=0
        self.energy=clamp(self.energy); self.safety=clamp(self.safety)
        self.curiosity=clamp(self.curiosity); self.social=clamp(self.social)
        if self.energy<=0: self.dead=True
        return self._delta(d0), self.dead
    def _delta(self, before=None):
        if before is None: before={}
        return {k: round(getattr(self,k)-before.get(k,getattr(self,k)),2)
                for k in ('energy','safety','curiosity','social')}

def q_reward(delta, dead=False):
    r=0.8*delta.get('energy',0)+0.3*delta.get('safety',0)+0.15*delta.get('curiosity',0)+0.05*delta.get('social',0)
    if dead: r-=10
    return r

class QAgent:
    def __init__(self, seed):
        self.rng=random.Random(seed); self.Q=defaultdict(lambda:[0.0]*len(ACTIONS))
    def act(self, env, eps):
        s=bins(env); qs=self.Q[s]
        if self.rng.random()<eps: return self.rng.randrange(len(ACTIONS))
        return max(range(len(ACTIONS)), key=lambda i: qs[i])
    def train(self, seed, episodes=3, ticks=TICKS, eps=0.35, alpha=0.2, gamma=0.9):
        for ep in range(episodes):
            env=Env(seed+ep*101+1)
            for _ in range(ticks):
                s=bins(env); a=self.act(env,eps); d,dead=env.step(ACTIONS[a]); r=q_reward(d,dead)
                s2=bins(env); old=self.Q[s][a]
                self.Q[s][a]=old+alpha*(r+gamma*max(self.Q[s2])-old)
                if dead: break
    def evaluate(self, seed, ticks=TICKS):
        env=Env(seed+9999)
        for _ in range(ticks):
            a=self.act(env,0.0); env.step(ACTIONS[a])
            if env.dead: break
        return summarize(env)

def summarize(env):
    counts={a:env.actions.count(a) for a in ACTIONS}
    n=max(1,len(env.actions))
    return {'survival':len(env.actions),'final_energy':round(env.energy,2),
            'net_energy':round(env.energy-START_E,2),
            'read_freq':round(counts['read']/n,3),'rest_freq':round(counts['rest']/n,3),
            'look_freq':round(counts['look']/n,3),'actions':counts}

def genome_action(g, env):
    q=g['q']; s=bins(env)
    vals=q.get(s, g['fb'])
    return max(range(len(ACTIONS)), key=lambda i: vals[i])

def eval_genome(g, seed, episodes=3, ticks=TICKS):
    rows=[]
    for ep in range(episodes):
        env=Env(seed+ep*37+11)
        for _ in range(ticks):
            a=genome_action(g,env); env.step(ACTIONS[a])
            if env.dead: break
        rows.append(summarize(env))
    def avg(k): return sum(r[k] for r in rows)/len(rows)
    fit=sum(r['survival']*2 + r['final_energy'] + r['net_energy'] for r in rows)/len(rows)
    return {'fitness':round(fit,2),'survival':round(avg('survival'),2),
            'final_energy':round(avg('final_energy'),2),'net_energy':round(avg('net_energy'),2),
            'read_freq':round(avg('read_freq'),3),'rest_freq':round(avg('rest_freq'),3),
            'rows':rows}

def random_genome(rng):
    return {'q':{}, 'fb':[rng.uniform(-2,2) for _ in ACTIONS]}

def mutate(g,rng,rate=0.3,sigma=1.0):
    out={'q':copy.deepcopy(g['q']),'fb':list(g['fb'])}
    if rng.random()<0.6:
        out['fb']=[v+rng.gauss(0,sigma) for v in out['fb']]
    for k in list(out['q']):
        if rng.random()<rate:
            out['q'][k]=[v+rng.gauss(0,sigma) for v in out['q'][k]]
    if rng.random()<0.05:
        out['fb']=[rng.uniform(-2,2) for _ in ACTIONS]
    return out

def q_to_genome(qagent):
    return {'q':{k:list(v) for k,v in qagent.Q.items()}, 'fb':[0.0]*len(ACTIONS)}

def run_q(seed):
    a=QAgent(seed); a.train(seed,3,TICKS,.35,.2)
    return a.evaluate(seed)

def run_ga(seed, pop=12, gens=8):
    rng=random.Random(seed)
    popu=[random_genome(rng) for _ in range(pop)]
    hist=[]
    best=None
    for gen in range(1,gens+1):
        scored=[(eval_genome(g,seed),g) for g in popu]
        scored.sort(key=lambda x:x[0]['fitness'],reverse=True)
        best=scored[0]
        hist.append({'gen':gen,'best_fitness':best[0]['fitness'],'best':best[0]})
        surv=[copy.deepcopy(x[1]) for x in scored[:4]]
        popu=surv[:]
        while len(popu)<pop: popu.append(mutate(rng.choice(surv),rng))
    return {'best':best[0],'history':hist}

def cell_of(beh):
    x=min(5,int(beh['read_freq']*6)); y=min(5,int(beh['rest_freq']*6))
    return (x,y)

def run_map(seed, gens=8, candidates=36):
    rng=random.Random(seed)
    archive={}
    hist=[]
    def offer(g):
        e=eval_genome(g,seed)
        c=cell_of(e); rec={'fitness':e['fitness'],'behavior':e,'genome':g,'cell':c}
        old=archive.get(c)
        if old is None or rec['fitness']>old['fitness']: archive[c]=rec
        return rec
    for _ in range(candidates): offer(random_genome(rng))
    for gen in range(1,gens+1):
        pool=list(archive.values())
        cands=[]
        # half mutations from elites, half fresh
        for i in range(candidates):
            if pool and rng.random()<0.75:
                cands.append(mutate(rng.choice(pool)['genome'],rng,0.35,1.0))
            else:
                cands.append(random_genome(rng))
        for g in cands: offer(g)
        best=max(archive.values(),key=lambda r:r['fitness'])
        hist.append({'gen':gen,'cells':len(archive),'best_fitness':best['fitness'],
                     'best':best['behavior'],'best_cell':best['cell']})
    best=max(archive.values(),key=lambda r:r['fitness'])
    return {'best':best['behavior'],'best_cell':best['cell'],'cells':len(archive),'history':hist,
            'read_freqs':[round(r['behavior']['read_freq'],3) for r in archive.values()]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--q-seeds',type=int,default=5)
    ap.add_argument('--evo-seeds',type=int,default=3)
    ap.add_argument('--out',default=str(_HERE / 'phase3_result.json'))
    args=ap.parse_args()
    out={'env':'v3 base metabolism + read/rest fatigue + v2 noise','q':[],'ga':[],'map':[]}
    for s in range(1,args.q_seeds+1):
        r=run_q(s); out['q'].append({'seed':s,**r}); print('Q',s,r)
    for s in range(1,args.evo_seeds+1):
        r=run_ga(s); out['ga'].append({'seed':s,**r}); print('GA',s,r['best'])
        r=run_map(s); out['map'].append({'seed':s,**r}); print('MAP',s,r['best'],'cells',r['cells'])
    Path(args.out).write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('SAVED',args.out)

if __name__=='__main__':
    main()
