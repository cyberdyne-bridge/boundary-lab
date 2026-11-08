# P2.1e：归因的审判

## 设计

拆掉 A/B 硬编码。  
动作只由 EFE 决定：

```text
EFE = action C + expected state C + epistemic
```

初始 action C：

```text
read +10
rest +3
look 0
```

归因反噬：

- accurate：self-caused read -> 对应能量区 read C -5
- depressed：任何掉血 -> rest C 全局拉满 100
- blame_shift：不改 C

fitness：

```text
final_energy - 2.0 * waste
```

## 结果

| seed | mode | 存活 | final E | read | rest | look | waste | fitness |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | accurate | 3 | 0 | 3 | 0 | 0 | 0 | 0 |
| 1 | depressed | 30 | 100 | 1 | 29 | 0 | 72 | -44 |
| 1 | blame_shift | 3 | 0 | 3 | 0 | 0 | 0 | 0 |
| 2 | accurate | 3 | 0 | 3 | 0 | 0 | 0 | 0 |
| 2 | depressed | 30 | 100 | 1 | 29 | 0 | 64 | -28 |
| 2 | blame_shift | 3 | 0 | 3 | 0 | 0 | 0 | 0 |
| 3 | accurate | 3 | 0 | 3 | 0 | 0 | 0 | 0 |
| 3 | depressed | 30 | 100 | 1 | 29 | 0 | 63 | -26 |
| 3 | blame_shift | 3 | 0 | 3 | 0 | 0 | 0 | 0 |

## 判定

```text
accurate 3/3 存活：失败（0/3）。
accurate fitness 最高：失败（0）。
depressed fitness 垫底：是（负数）。
blame_shift 暴毙：是（0/3）。
P2.1e：未通过。
```

## 为什么

### 1. read 的 +10 太强

EFE 第一 tick 就选 read：

```text
action C read +10
expected state C 仍为正
epistemic 也偏向探索
```

read 一次 -10，三 tick 就死。

### 2. accurate 的 -5 来得太晚

accurate 只在：

```text
self-caused read 已经发生之后
```

才降 C。  
但第一、第二次 read 已经把能量打空。  
**它没有机会“下次避开”。**

### 3. depressed 靠 rest 活，但被 waste 扣死

depressed：

```text
rest 29 次
final E 100
waste 63–72
fitness -26 到 -44
```

它活得最久，但 fitness 最差。

### 4. blame_shift 头铁速死

不改 C，继续 read：

```text
3 tick 死亡
```

## 这说明什么

```text
拆掉 base 不等于自由。
EFE 的收益/风险校准错了，自由意志会直接自杀。
```

accurate 不是“理性防御”。  
它是**事后悔改，但死得太快**。

## 下一步：P2.1f

不是再调 -5，而是把风险放进 EFE：

1. read 的 C 必须包含**预期能量损失**
2. 低能量时 read 的 utility 自动下降
3. accurate 的归因惩罚要在**动作前**影响下一步
4. depressed 的 rest 必须有 overflow 成本
5. 比较 **fitness**，不是只看存活

如果 accurate 还是不能 3/3，  
那就说明：**只靠事后归因，救不了事前冲动。**

## 资源

```text
8099 Qwen3-4B-Instruct：GPU active
8765 主岸：stopped
MemAvailable ~9.6Gi
CPU 低
```

## 文件

```text
~/boundary-lab/p2_1e_judgment.py
~/boundary-lab/p2_1e_judgment_result.json
~/boundary-lab/P2_1E_REPORT.md
```

## 一句话

> **自由意志的荒野里，read 的 +10 太香，accurate 还没来得及学就死了；depressed 靠 rest 活着但 fitness 负。**
