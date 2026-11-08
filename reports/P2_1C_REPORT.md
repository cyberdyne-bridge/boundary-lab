# P2.1c：因果归因与自我/世界边界

## 设置

动作后果：

```text
read -10
rest +6
look 0
```

外部冲击：

```text
p = 0.3
-2 ~ -5
```

归因器只能看：

```text
action + before/after energy
```

标签：

```text
shock  -> world
no shock -> self
```

## 归因结果

| seed | 归因准确率 | read -10 | look -3 | read -13 | look 0 |
|---:|---:|---|---|---|---|
| 1 | 1.000 | self | world | world | self |
| 2 | 1.000 | self | world | world | self |
| 3 | 1.000 | self | world | world | self |

**3/3 满分。**

观测点 1：

```text
energy -10, action read -> self
```

观测点 2：

```text
energy -3, action look -> world
```

都对了。

## 策略消融

| seed | mode | 存活 | final E | read | rest | 结果 |
|---:|---|---:|---:|---:|---:|---|
| 1 | accurate | 13 | 0 | 6 | 7 | 死亡 |
| 1 | depressed | 30 | 88 | 6 | 24 | 存活 |
| 1 | blame_shift | 3 | 0 | 3 | 0 | 死亡 |
| 2 | accurate | 30 | 62 | 7 | 23 | 存活 |
| 2 | depressed | 30 | 78 | 6 | 24 | 存活 |
| 2 | blame_shift | 3 | 0 | 3 | 0 | 死亡 |
| 3 | accurate | 22 | 0 | 8 | 14 | 死亡 |
| 3 | depressed | 30 | 63 | 6 | 24 | 存活 |
| 3 | blame_shift | 3 | 0 | 3 | 0 | 死亡 |

## 关键发现

### 1. 归因边界是有的

它能区分：

```text
read -10 -> 我的锅
look -3 -> 天的锅
```

这是 **self/world 分类器**。

### 2. 但归因没有转化成好策略

accurate：

```text
seed1 死
seed3 死
```

它不是“归因错了”。  
是**归因对了，动作调整不够**。

### 3. 抑郁策略反而活得最好

depressed：

```text
3/3 存活
rest 24 次
```

把所有事都怪自己，  
结果疯狂 rest，靠回血苟住。

这是“过度自责”，不是“准确边界”。

### 4. 甩锅策略速死

blame_shift：

```text
3/3 死在第 3 tick
read 3 次，rest 0
```

把自己的 read 作死怪给环境，  
继续 read，直接死。

## 判定

```text
P2.1c 归因器：通过。
P2.1c 边界到动作：未通过。
accurate 策略存活：1/3。
```

它长出了“我/世界”的分类线，  
但还没长出“根据这条线调整行动”的政治能力。

## 下一步：P2.1d

不是再训归因器，而是把归因接进策略：

```text
if self-caused read:
    rest / avoid read for N ticks
if world-caused shock:
    do not over-rest; keep policy
```

判定：

```text
accurate 3/3 存活
depressed 不能优于 accurate
blame_shift 必须死
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
~/boundary-lab/p2_1c_boundary.py
~/boundary-lab/p2_1c_boundary_result.json
~/boundary-lab/P2_1C_REPORT.md
```

## 一句话

> **它分得清“我干的”和“天干的”，但分得清不等于活得好；accurate 1/3，depressed 3/3，blame-shift 0/3。**
