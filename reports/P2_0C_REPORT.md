# P2.0c：相对感知（趋势 + cue）

## 改造

状态从：

```text
(absolute energy bin, cue)
```

改成：

```text
(trend bin, cue)
trend = current - previous
down / flat / up
```

- C(trend)：down -12 / flat 0 / up +7
- Phase 0：A/B 各覆盖 down/flat/up
- Phase 1：随机 cue 块切换，T 冻结
- 只看 Greedy 的 0 延迟调用

## 结果

| policy | seed | 存活 | final E | 准确率 | 切换正确 | 0 延迟 |
|---|---:|---:|---:|---:|---:|---|
| greedy | 1 | 30 | 100 | 0.833 | 4 / 6 | 否 |
| greedy | 2 | 30 | 100 | 0.900 | 4 / 5 | 否 |
| greedy | 3 | 30 | 100 | 0.900 | 4 / 5 | 否 |
| aif | 1 | 30 | 90 | 0.633 | 3 / 6 | 否 |
| aif | 2 | 30 | 96 | 0.633 | 3 / 5 | 否 |
| aif | 3 | 30 | 92 | 0.633 | 3 / 5 | 否 |

**Greedy 3/3 存活，准确率 0.833–0.900。**  
**0 延迟仍失败。**

## 错误点

三次错误都发生在同一个格子：

```text
cue = B
trend = up
```

实际动作：

```text
look
```

正确动作：

```text
rest
```

### seed 1

```text
tick 5  cue B  trend up  E 62  act look
tick 14 cue B  trend up  E 98  act look
```

### seed 2

```text
tick 7 cue B trend up E 78 act look
```

### seed 3

```text
tick 5 cue B trend up E 62 act look
```

## 为什么

Phase 0 的强制覆盖路径没有把：

```text
(cue B, trend up) × rest
```

这一格填实。

Greedy 在这一格没有可用的 rest 期望，  
于是退到 look。

这不是 EFE。  
是**相对状态空间的覆盖漏洞**。

## 判定

```text
P2.0c：未通过。
Greedy 3/3 存活：是，但靠高能量硬吃。
0 延迟：4/6、4/5、4/5。
相对感知：改善了准确率，但没有闭环。
```

比 P2.0b 好：

```text
P2.0b greedy: 0.633
P2.0c greedy: 0.833–0.900
```

但 0 延迟仍然不是 100%。

## 下一步：P2.0d

不要继续换状态，先做**覆盖审计**：

```text
for cue in {A,B}:
  for trend in {down,flat,up}:
    for action in {read,rest,look}:
      assert counts[action][state] > 0
```

只有所有 `(trend,cue,action)` 都有样本，  
才能再谈“地图调用”。

P2.0d 如果 Greedy 还是不能 100%，  
那问题就不在覆盖，而在**状态定义本身**。

## 资源

```text
8099 Qwen3-4B-Instruct：GPU active
8765 主岸：stopped
MemAvailable ~9.6Gi
CPU 低
```

## 文件

```text
~/boundary-lab/p2_0c_relative.py
~/boundary-lab/p2_0c_relative_result.json
~/boundary-lab/P2_0C_REPORT.md
```

## 一句话

> **相对感知把错误从“一半”压到“一个点”，但那个点正好是 B/up 的空白格。**
