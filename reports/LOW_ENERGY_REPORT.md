# 低能量训练分布修复报告

## 诊断

原始训练里，Q 几乎从没见过 energy ≤ 25：

- 训练动作总是把 energy 维持在 50+
- eval greedy 从 60 开始，先 look，掉到低能量时进入未训练状态
- Q 表默认动作顺序选中 look
- 不是“她不怕死”，是训练分布没覆盖死亡边缘

## 修复

每个 episode 从低能量开始：

```text
ep1 energy=27
ep2 energy=34
ep3 energy=41
```

不修改 eval，不加硬规则。  
只是把训练分布扩展到 20–45。

## 结果

| seed | eval rest | eval look | eval read | 结束 energy |
|---:|---:|---:|---:|---:|
| 1 | 12 | 6 | 2 | 100 |
| 2 | 7 | 13 | 0 | 100 |
| 3 | 10 | 10 | 0 | 100 |

**3/3 seed 活到 100。**

之前无低能量开局：1/3 活到 100。

## 结论

- 诊断成立：训练没覆盖低能量状态
- 低能量开局是有效的 curriculum
- Q 学会了在低能量时 rest
- 没有写“if energy<20: rest”这种硬规则

## 不能夸大

- 这是 tabular Q + workspace
- 只覆盖 energy 真实
- 4B 不参与
- 3 seeds
- 没有主观体验证据

它证明的是：

> **训练分布覆盖死亡边缘，策略才学会生存。**

## 资源

```text
MemAvailable ~2.5Gi
Swap 21Gi, used ~5Gi
OOM 无
lab VM stopped
主 VM restored
```

## 下一步

把 4B 叙述加回来，做盲评；或者跑 5 seeds 固化结论。
