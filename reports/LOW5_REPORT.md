# 低能量 curriculum · 5 seed 复现

## 设置

- 3 episodes × 40 tick 训练
- 每 episode 从 20–45 energy 开始
- 20 tick greedy eval
- 只保留 energy 在 VM 里
- 4B 不参与
- 5 seeds

## 结果

| seed | eval rest | eval look | eval read | 结束 energy |
|---:|---:|---:|---:|---:|
| 1 | 12 | 6 | 2 | 100 |
| 2 | 7 | 13 | 0 | 100 |
| 3 | 10 | 10 | 0 | 100 |
| 4 | 7 | 13 | 0 | 100 |
| 5 | 10 | 7 | 0 | 100 |

**5/5 全部活到 100。**

## 结论

- 低能量训练分布是必要条件
- 5 seeds 全部复现
- Q 学会在低能量时 rest
- 没有硬编码“低能量必须 rest”
- 这是 curriculum 效应，不是意识

## 不能夸大

- tabular Q + workspace
- 只有 energy 真实
- 4B 不参与
- 20 tick eval
- 没有主观体验证据

## 资源

```text
MemAvailable ~2.6Gi
Swap 21Gi, used ~5Gi
OOM 无
lab VM stopped
主 VM restored
```

## 下一步

4B 叙述加回来，做盲评；或者把 safety/curiosity 再搬进 VM，但先不要再加变量。
