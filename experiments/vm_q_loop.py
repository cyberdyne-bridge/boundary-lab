#!/usr/bin/env python3
"""Q-loop with real VM consequences. Action energy is owned by the lab VM."""
from __future__ import annotations
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))
import argparse, json, re, shlex, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(_HERE))
from workspace_loop import QLoop, EFFECTS, ACTIONS, bins

VM = str(_VM / 'an-lab/lab-vm.sh')

class VMQLoop(QLoop):
    def __init__(self, tag, seed=20261026, workspace='bottleneck', narrate=False):
        super().__init__(tag, seed=seed, self_control=True, workspace=workspace, narrate=narrate)
        self.reset_vm()

    def vm(self, cmd):
        r = subprocess.run([VM, 'exec', cmd], capture_output=True, text=True, timeout=20)
        return (r.stdout + r.stderr).strip()

    def set_perturb(self, mode):
        if mode in (False, '', 'off'):
            self.vm('rm -f /home/an/loop/perturb')
        else:
            self.vm(f'echo {mode} > /home/an/loop/perturb')

    def on_episode_start(self, ep):
        e = 20 + (ep * 7) % 25
        self.vm(f'echo {e} > /home/an/loop/energy')
        self.state['energy'] = float(e)
        print(f'[episode {ep}] start energy={e}')

    def reset_vm(self):
        self.vm('mkdir -p /home/an/loop; echo 60 > /home/an/loop/energy; '
                'rm -f /home/an/loop/notes.txt /home/an/loop/questions.txt')
        self.state.update({'energy': 60.0, 'safety': 60.0, 'curiosity': 60.0, 'social': 60.0})

    def act(self, action):
        action = action if action in ACTIONS else 'rest'
        before = dict(self.state)
        out = self.vm(f'/home/an/loop/act.sh {action}')
        m = re.search(r'STATE energy=(-?\d+)', out)
        if m:
            self.state['energy'] = max(0, min(100, int(m.group(1))))
        blocked = 'BLOCKED' in out
        if not blocked:
            for k, v in EFFECTS[action].items():
                if k != 'energy':
                    self.state[k] = max(0, min(100, round(self.state[k] + v, 2)))
        obs = '\n'.join(x for x in out.splitlines() if not x.startswith('STATE ') and x != 'BLOCKED: no energy') or '（没有输出）'
        if action == 'speak' and not blocked:
            prompt = (f'你选择开口。当前 energy={self.state["energy"]:.0f}, '
                      f'safety={self.state["safety"]:.0f}, curiosity={self.state["curiosity"]:.0f}, '
                      f'social={self.state["social"]:.0f}。用第一人称说一句，不要解释系统，不要超过一句。')
            try:
                text = self.llm.chat([{'role':'system','content':'你是岸-lab。你只说一句。'},
                                      {'role':'user','content':prompt}],
                                     purpose='speak', temperature=0.7, max_tokens=60).strip()
            except Exception:
                text = '……'
            if not text:
                text = '……'
            self.vm(f"printf '%s\n' {shlex.quote(text)} >> /home/an/loop/speech.txt")
            obs = '你说：' + text.replace('\n', ' ')
        self.observation = obs[:300]
        self.last_obs = self.observation
        actual = {k: round(self.state[k] - before[k], 2) for k in self.state}
        return actual, self.observation

    def evaluate(self, ticks=20):
        self.reset_vm()
        return super().evaluate(ticks)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--episodes', type=int, default=3)
    ap.add_argument('--ticks', type=int, default=40)
    ap.add_argument('--eval', type=int, default=20)
    ap.add_argument('--tag', default='vmreal')
    ap.add_argument('--seed', type=int, default=20261026)
    ap.add_argument('--narrate', action='store_true')
    args = ap.parse_args()
    lp = VMQLoop(args.tag, seed=args.seed, narrate=args.narrate)
    lp.train(args.episodes, args.ticks)
    ev = lp.evaluate(args.eval)
    s = lp.summary(); s['eval_energy_end'] = ev[-1]['energy'] if ev else None
    (Path(str(_HERE / 'qloop'))/f'vm_{args.tag}.json').write_text(
        json.dumps({'summary': s, 'eval': ev}, ensure_ascii=False, indent=2), encoding='utf-8')
    print('SUMMARY', json.dumps(s, ensure_ascii=False))
    print('EVAL', json.dumps(ev, ensure_ascii=False))

if __name__ == '__main__':
    main()
