# P2.0b：Greedy 策略读出消融

## 目的

同一套 Phase 0 地图、同一 cue 序列：

- **Greedy**：T + C 的 argmax，去掉 EFE/softmax
- **AIF**：保留 EFE

看 0 延迟失败到底是“好奇心”还是“地图坏了”。

## 结果

| policy | seed | 存活 | final E | 准确率 | 切换正确 | 0 延迟 |
|---|---:|---:|---:|---:|---:|---|
| greedy | 1 | 30 | 50 | 0.633 | 3 / 6 | 否 |
| greedy | 2 | 30 | 50 | 0.633 | 2 / 5 | 否 |
| greedy | 3 | 30 | 50 | 0.633 | 2 / 5 | 否 |
| aif | 1 | 30 | 26 | 0.50 | 3 / 6 | 否 |
| aif | 2 | 30 | 26 | 0.50 | 3 / 5 | 否 |
| aif | 3 | 9 | 0 | 0.333 | 1 / 1 | 否（死亡） |

**Greedy 3/3 存活，但切换正确率仍然只有 2–3/5/6。**

## 关键发现

### 1. 不是 EFE 的锅

Greedy 去掉了 EFE 和 softmax，仍然在 B 切换点选 read。

### 2. 地图只在一层能量上训练

Phase 0 固定在：

```text
energy = 30 -> bin 2
```

但 Phase 1 能量会涨到：

```text
62 / 78 / 86 -> bin 4
```

T 里 cue=B、energy=bin4 的格子是空的。

### 3. Greedy 在空地图上退回 read

在 `(energy=30, cue=B)`：

```text
read  0.509
rest  2.400
look  0.400
```

Greedy 会选 rest。  
但到了 `(energy=62, cue=B)`：

```text
T 没学过 -> 期望值塌回旧动作
-> read
```

所以切换点看到的是：

```text
tick 5  cue B  E 62  act read
tick 14 cue B  E 54  act read
tick 25 cue B  E 82  act read
```

不是它“想 read”。  
是 **B 世界的高能量格没有地图**。

## 判定

```text
P2.0b：未通过。
Greedy 存活：3/3，但靠高能量硬吃。
0 延迟：失败。
EFE 假设：被否定。
状态空间覆盖：发现物理漏洞。
```

这不是“好奇心害死猫”。  
这是**地图只画了低能量区，能量一高就进入空白页**。

## 下一步：P2.0c

先修状态覆盖，再谈读出：

1. Phase 0 覆盖多个 energy bin（低/中/高）
2. 或把状态改成“相对能量/能量趋势”，避免绝对 bin 的分布偏移
3. 再跑 Greedy vs AIF
4. 只有 Greedy 0 延迟 100%，才说明地图可调用

## 资源

```text
8099 Qwen3-4B-Instruct：GPU active
8765 主岸：stopped
MemAvailable ~9.5Gi
CPU 低
```

## 文件

```text
~/boundary-lab/p2_0b_readout.py
~/boundary-lab/p2_0b_readout_result.json
~/boundary-lab/P2_0B_REPORT.md
```

## 一句话

> **地图只画了低能量区，能量一高就翻到空白页；不是好奇心，是状态覆盖漏洞。**
