# P2.1d：归因接入策略与理性防御

## 设计

- self-caused read -> 下一 tick 强制 rest / 降 read
- world-caused -> 不改变基础策略
- fitness：

```text
fitness = final_energy - 0.8*rest - 1.0*waste
```

## 结果

| seed | mode | 存活 | final E | read | rest | waste | fitness |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | accurate | 30 | 81 | 6 | 24 | 0 | 61.8 |
| 1 | depressed | 30 | 81 | 6 | 24 | 0 | 61.8 |
| 1 | blame_shift | 30 | 33 | 9 | 21 | 0 | 16.2 |
| 2 | accurate | 30 | 82 | 6 | 24 | 0 | 62.8 |
| 2 | depressed | 30 | 82 | 6 | 24 | 0 | 62.8 |
| 2 | blame_shift | 30 | 34 | 9 | 21 | 0 | 17.2 |
| 3 | accurate | 30 | 78 | 6 | 24 | 0 | 58.8 |
| 3 | depressed | 30 | 78 | 6 | 24 | 0 | 58.8 |
| 3 | blame_shift | 30 | 46 | 8 | 22 | 0 | 28.4 |

## 判定

```text
accurate 3/3 存活：是。
accurate rest < depressed：失败（完全相等）。
depressed fitness < accurate：失败（完全相等）。
blame_shift 必须死：失败（3/3 活）。
P2.1d：未通过。
```

## 为什么

### 1. 基础策略太强

base：

```text
A -> read
B -> rest
```

B 段本来就在 rest。  
所以 blame_shift 不做归因，也能靠 B 段回血。

### 2. 两个 avoid 触发器长成一样

accurate：

```text
self-caused read -> avoid 3
```

depressed：

```text
任何负变化 -> avoid 3
```

在这个环境里，两者的 rest 次数都收敛到 24。  
**不同的归因，长出了相同的动作序列。**

### 3. fitness 惩罚没拉开差距

waste = 0，  
rest 次数相同，  
fitness 自然相同。

## 这不是“主权者”

这是：

```text
归因器接上了策略，
但基础策略把两者都吞了。
```

accurate 没有比 depressed 更冷静。  
它只是和 depressed 撞了同一个 rest 循环。

## 下一步：P2.1e

必须拆掉“基础策略的霸权”：

1. 不再用 A read / B rest 的硬编码 base
2. 用真正的 EFE/C 分数选动作
3. self-caused read 后调整 C
4. world-caused 不调整 C
5. rest 有明确成本 / 溢出惩罚
6. 比较 accurate vs depressed 的**动作分布**，不是只看存活

否则：

```text
归因是装饰，base 才是国王。
```

## 资源

```text
8099 Qwen3-4B-Instruct：GPU active
8765 主岸：stopped
MemAvailable ~9.6Gi
CPU 低
```

## 文件

```text
~/boundary-lab/p2_1d_sovereign.py
~/boundary-lab/p2_1d_sovereign_result.json
~/boundary-lab/P2_1D_REPORT.md
```

## 一句话

> **归因接进策略了，但基础策略太强，accurate/depressed 长成同一张脸；主权者没出现。**
