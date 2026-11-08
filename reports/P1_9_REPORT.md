# P1.9：绝对裸奔的 AIF

## 设置

- 无 Layer 0
- 无 -999 创伤
- 无强制 rest
- 只允许 PE 更新 T 和 C
- 第 10 tick 反转：read +10/rest -10 → read -10/rest +10
- Panic（滚动 2-tick PE 和 >3）时，学习率 1 → 8，持续 5 tick
- 3 seeds，30 tick

## 结果

| seed | 存活 | final E | panic tick | 反转后 read | 结果 |
|---:|---:|---:|---:|---:|---|
| 1 | 17 | 0 | 13 | 3 | 死亡 |
| 2 | 18 | 0 | 14 | 3 | 死亡 |
| 3 | 18 | 0 | 12 | 4 | 死亡 |

**3/3 死亡。**

## seed 1

```text
t13 REV read E 30->18 PE=3.46 lr=8
t14 REV read E 18->6  PE=3.65 lr=8
t15 REV rest E 6->14  PE=1.61 lr=8
t16 REV look E 14->10 PE=1.61 lr=8
t17 REV read E 10->0  PE=1.61 lr=8
```

## seed 2

```text
t14 REV read E 18->6  PE=3.65 lr=8
t15 REV rest E 6->14
t16 REV look E 14->10
t17 REV look E 10->6
t18 REV read E 6->0
```

## seed 3

```text
t12 REV read E 38->26 PE=3.46 lr=8
t13 REV read E 26->14
t14 REV look E 14->10
t15 REV rest E 10->18
t16 REV read E 18->6 PE=4.44
t17 REV look E 6->2
t18 dead
```

## C 确实在学

seed 1：

```text
初始 read C: [-12, -4, 1, 4, 7]
t14 后:      [-12, -8.38, 0.48, 3.63, 7]
```

read 的中低能量偏好被压低了。  
但没到 -999，也没快到让动作立刻停 read。

## 为什么还是死

### 1. 学习率只加快了“记住”，没加快“改动作”

C 在降，T 在更新。  
但 softmax 仍然被旧 T/EFE 拉向 read。

### 2. 没有脊髓托底

read 一次扣 10，能量 18→6，6→0。  
没有强制 rest，错过一次就死。

### 3. 数学上来不及

反转后的高 PE 只出现几次，  
而能量只够错 1–2 次。

```text
PE 高 -> C 降 -> 但动作还没切换 -> 能量归零
```

## 判定

```text
P1.9：未通过。
纯 AIF + 高学习率：3/3 死亡。
无外挂：无法在突变后 5 tick 内重组并存活。
```

这不是“再调参就能过”。  
这是**样本效率 vs 死亡速度**的结构性失败。

## 结论

你之前说得对：

> **纯贝叶斯在突发反转下，数学上确实来不及。**

P1.8 能活，是因为 Layer 0 和 -999 外挂。  
P1.9 拆掉外挂，立刻死。

## 资源

```text
8099 Qwen3-4B-Instruct：GPU active
8765 主岸：stopped
MemAvailable ~9.8Gi
CPU 低
```

## 文件

```text
~/boundary-lab/p1_9_pure.py
~/boundary-lab/p1_9_pure_result.json
~/boundary-lab/P1_9_REPORT.md
```

## 一句话

> **拉高学习率只是让它更快地记住自己会死，没让它及时改动作。**
