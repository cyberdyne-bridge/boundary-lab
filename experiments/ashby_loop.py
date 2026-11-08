#!/usr/bin/env python3
"""Minimal Ashby ultrastability layer over the VM Q loop."""
from __future__ import annotations
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import sys
sys.path.insert(0,str(_HERE))
from vm_q_loop import VMQLoop
from workspace_loop import ACTIONS

class AshbyLoop(VMQLoop):
    def __init__(self, tag, seed=20261026, workspace='bottleneck'):
        super().__init__(tag, seed=seed, workspace=workspace, narrate=False)
        self.reconfigs=0; self.force_random=0; self.current_ep=0
        self.reconfigured=set()

    def on_episode_start(self, ep):
        super().on_episode_start(ep)
        self.current_ep=ep
        self.reconfigured.discard(ep)

    def select_action(self, s, qs, eps):
        if self.force_random>0:
            self.force_random-=1
            return self.rng.randrange(len(ACTIONS))
        return super().select_action(s, qs, eps)

    def after_act(self, action, delta):
        # detect essential-variable failure before death
        if self.state['energy'] <= 30 and self.current_ep not in self.reconfigured:
            self.reconfigured.add(self.current_ep)
            self.reconfigs += 1
            # structural-ish reconfiguration: randomize low-energy Q rows
            for k in list(self.Q):
                if any(name=='E' and b<=1 for name,b in k):
                    self.Q[k]=[self.rng.uniform(-2.0,2.0) for _ in ACTIONS]
            self.force_random=25
            print(f'[reconfig {self.reconfigs}] energy={self.state["energy"]:.0f} force_random=25')

    def summary(self):
        s=super().summary(); s['reconfigs']=self.reconfigs; s['ashby']=True; return s
