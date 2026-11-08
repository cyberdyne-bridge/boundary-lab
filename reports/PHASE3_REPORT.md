# Phase 3 报告：基础代谢 + 双疲劳

## 环境 v3

```text
每 tick 先扣 2 energy
read 连续：+10 / +6 / +3 / 0 / -2
rest 连续：+10 / +6 / +3 / 0 / -2
非 read 重置 read streak；非 rest 重置 rest streak
保留 v2 噪声：read 20% 只 +5；rest 20% 额外 -2；look 20% 额外 -2
```

纯 Python，无 4B，无 VM。

## Q：5 seeds

| seed | survival | final E | read | rest | look |
|---:|---:|---:|---:|---:|---:|
| 1 | 19 | -1 | 0.368 | 0.158 | 0.474 |
| 2 | 30 | 39 | 0.900 | 0.100 | 0.000 |
| 3 | 13 | 0 | 0.692 | 0.000 | 0.308 |
| 4 | 30 | 44 | 0.900 | 0.100 | 0.000 |
| 5 | 30 | 76 | 0.533 | 0.067 | 0.400 |

**3/5 存活，2/5 死亡。**

## GA-lite：3 seeds

| seed | survival | final E | read | rest | fitness |
|---:|---:|---:|---:|---:|---:|
| 1 | 13.67 | -0.67 | 1.0 | 0.0 | -1.0 |
| 2 | 13.33 | 0.0 | 1.0 | 0.0 | -0.33 |
| 3 | 13.67 | -0.67 | 1.0 | 0.0 | -1.0 |

**0/3 存活，全部 read-only。**

## MAP-Elites：3 seeds

| seed | cells | survival | final E | read | rest | fitness |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 3 | 13.67 | -0.67 | 1.0 | 0.0 | -1.0 |
| 2 | 3 | 13.33 | 0.0 | 1.0 | 0.0 | -0.33 |
| 3 | 3 | 13.67 | -0.67 | 1.0 | 0.0 | -1.0 |

**0/3 存活，格子仍只有 3 个。**

## 关键发现

### 1. read-only 确实被 v3 杀死了

v2 里 read-only 能活到 100。  
v3 里 read-only 在 13–14 tick 死亡。

基础代谢 + read 疲劳生效了。

### 2. 但 GA/MAP 没有找到 read/rest 交替

它们仍然坍缩在 read-only。

原因：

- 初始随机基因组里 read-only 能活 13–14 tick
- 任何带 rest 的突变早期 fitness 更低
- 8 代 × 36 个体不够跨过这个 fitness valley
- MAP 的 3 个格子全是 read-only 附近

### 3. Q 有时能找到混合策略

Q2 / Q4：

```text
read 0.9 / rest 0.1
survival 30
final E 39–44
```

Q5：

```text
read 0.533 / rest 0.067 / look 0.4
survival 30
final E 76
```

但它们不是稳定节律，Q1 和 Q3 还是死了。

## 判定

```text
v3 成功杀死了 read-only。
但纯代码没有稳定找到 read/rest 混合策略。
Q：3/5 存活，脆。
GA：0/3。
MAP-Elites：0/3，且没有多样性。
```

按你的触发条件：

> 如果纯代码找不到生存策略，或者策略脆如纸，立刻解冻 4B / Active Inference。

现在属于**“脆如纸”**：

- Q 2/5 死亡
- GA/MAP 全灭
- 没有稳定混合节律
- 没有真正的行为多样性

**触发条件已满足。**

## 4B 终极测试准备

下一步不是直接让 4B 自由发挥，而是：

```text
4B 不知道：
- 每 tick 有 2 点基础代谢
- read 会疲劳
- rest 会疲劳
```

只给它：

```text
动作
观察
energy
```

让它多次濒死，记录：

- 连续 read 次数
- 死亡前最后 5 个动作
- Shadow Cache 是否出现“损耗/代谢/疲劳”的推断
- 是否在第二次/第三次濒死后改变策略

## 不能夸大

- 纯 Python 结果
- 无 4B
- 无 VM
- 3 seeds for GA/MAP
- 没有主观体验证据

## 文件

```text
~/boundary-lab/phase3.py
~/boundary-lab/phase3_result.json
~/boundary-lab/PHASE3_REPORT.md
```
