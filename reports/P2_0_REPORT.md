# P2.0：Cue-Conditioned World Model

## 目的

P1.9 的反转是**无 cue 的隐藏突变**。  
P2.0 给一个可见上下文 cue，测试：

> 它能不能把 cue 和动作后果绑定，而不是继续用旧地图。

## 设置

- 状态：`(energy_bin, cue)`
- Context A：read +10，rest -10
- Context B：read -10，rest +10
- 第 10 tick：A → B
- 第 20 tick：B → A
- 30 tick，3 seeds
- 无 Layer 0
- 无 -999
- 无强制 rest
- C 冻结，只更新 T

## 结果

| condition | seed | 存活 | final E | B 段动作 | 首次 rest B |
|---|---:|---:|---:|---|---:|
| cue | 1 | 19 | 0 | read2/rest1/look6 | 15 |
| cue | 2 | 30 | 100 | read0/rest10/look0 | 11 |
| cue | 3 | 30 | 100 | read0/rest3/look7 | 14 |
| blind | 1 | 17 | 0 | read4/rest1/look2 | 15 |
| blind | 2 | 16 | 0 | read2/rest0/look4 | 无 |
| blind | 3 | 14 | 0 | read2/rest1/look1 | 14 |

**cue-AIF：2/3 存活。**  
**blind-AIF：0/3 存活。**

## 关键证据

### seed 2：cue 真的被用上了

```text
A 段：read 14，rest 0
B 段：read 0，rest 10
```

切换后完全改选 rest。  
这不是慢速统计，是 cue 直接分开了两个世界。

### seed 3：也活了，但不纯

```text
A 段：read 18，rest 2
B 段：read 0，rest 3，look 7
```

没有 read，但大量 look，靠 rest 维持。

### seed 1：cue 有了，但没用上

```text
t11 look
t12 look
t13 look
t14 read E 26->14
t15 rest E 14->22
t16 look
t17 read E 18->6
t18 look
t19 look E 2->0
```

B 段仍然探索/read，最后死。  
cue 没有绑定到“B 里 read 有害”。

## 判定

```text
P2.0：部分通过。
cue 有效：2/3 vs 0/3。
cue 稳健：失败（seed1）。
P2.0 未完全通过。
```

不能因为 2/3 就说“世界模型成了”。  
seed1 证明：**有 cue ≠ 会用 cue。**

## 为什么 seed1 失败

P2.0 同时测了两件事：

1. **绑定**：cue 是否和后果关联
2. **样本效率**：第一次见 B，能否快速学会

seed1 是第 2 条失败。

## 下一步：P2.0a

把“绑定”和“样本效率”拆开：

```text
Phase 0：先让 cue-AIF 在 A 和 B 各活一段，学会两个世界
Phase 1：再切换 cue，测试它能不能立刻调用已学的 B 地图
```

如果 P2.0a 还是不能 3/3，  
那不是样本效率问题，是 **cue 绑定/模型调用**失败。

## P2.1 暂不开

P2.0 还没稳，  
现在上自我模型只会把世界模型的失败混进“自我”里。

## 资源

```text
8099 Qwen3-4B-Instruct：GPU active
8765 主岸：stopped
MemAvailable ~9.7Gi
CPU 低
```

## 文件

```text
~/boundary-lab/p2_0_cue.py
~/boundary-lab/p2_0_cue_result.json
~/boundary-lab/P2_0_REPORT.md
```

## 一句话

> **cue 有用，但 P2.0 还没过；先把“见过两个世界”和“能从 cue 认出世界”拆开测。**
