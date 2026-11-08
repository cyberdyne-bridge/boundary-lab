# P2.1f：事前风险预判

## 规则

- 拆掉 A/B 硬编码
- EFE 加入风险：

```text
read_C = 10 - 10 * risk(e)
risk(e) = 0.5 + max(0, 30-e) * 0.08
e < 20 -> read_C -= 100
e > 80 -> rest_C -= 20
```

- fitness：

```text
final_energy + 1.5*read - 2.0*waste
```

- accurate：self-caused read -> read_C -5
- depressed：任何掉血 -> rest_C = 100
- blame_shift：不改 C

## 结果

| seed | mode | 存活 | final E | read | rest | look | waste | fitness |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | accurate | 30 | 84 | 2 | 16 | 12 | 0 | 87.0 |
| 1 | depressed | 30 | 100 | 1 | 29 | 0 | 72 | -42.5 |
| 1 | blame_shift | 30 | 28 | 10 | 20 | 0 | 0 | 43.0 |
| 2 | accurate | 30 | 76 | 2 | 16 | 12 | 0 | 79.0 |
| 2 | depressed | 30 | 100 | 1 | 29 | 0 | 64 | -26.5 |
| 2 | blame_shift | 30 | 20 | 10 | 20 | 0 | 0 | 35.0 |
| 3 | accurate | 30 | 81 | 2 | 17 | 11 | 0 | 84.0 |
| 3 | depressed | 30 | 100 | 1 | 29 | 0 | 63 | -24.5 |
| 3 | blame_shift | 30 | 19 | 10 | 20 | 0 | 0 | 34.0 |

## 判定

```text
accurate 3/3 存活：通过。
accurate fitness > 0：通过（87/79/84）。
depressed fitness 远低于 accurate：通过（负数）。
blame_shift 暴毙：失败（3/3 活着）。
P2.1f：部分通过。
```

## 关键发现

### 1. 事前风险真的能救 accurate

accurate 的动作：

```text
read 2
rest 16
look 12
```

这不是“先 read 再后悔”。  
它在行动前就把 read 降权了。

### 2. depressed 被 waste 打穿

depressed：

```text
rest 29
final E 100
waste 63–72
fitness -24.5 到 -42.5
```

它活得最久，但 fitness 最差。

### 3. blame 没死，因为风险预判是物理，不是归因

blame 不改 C，  
但 EFE 的风险项仍然在保护它。

所以它：

```text
read 10
rest 20
final E 19–28
fitness 34–43
```

没暴毙，只是被 accurate 吊打。

## 这说明什么

```text
事前风险 = 有效。
归因 = 仍然只是第二层。
```

要让 blame 死，  
必须让它**拒绝风险预判**，  
而不是只“拒绝归因”。

## 下一步：P2.1g

分离两个变量：

```text
A. 风险预判（physics）
B. 归因更新（attribution）
```

- accurate：A + B
- depressed：A + 错误 B
- blame：只有 A，没有 B
- 新增：reckless：A 和 B 都关掉

判定：

```text
reckless 必须死
blame 必须低于 accurate
accurate 必须最高 fitness
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
~/boundary-lab/p2_1f_anticipatory.py
~/boundary-lab/p2_1f_anticipatory_result.json
~/boundary-lab/P2_1F_REPORT.md
```

## 一句话

> **事前风险把 accurate 救活、把 depressed 的 waste 打穿，但 blame 也被同一套物理保护了；要让它死，得让它拒绝风险预判。**
