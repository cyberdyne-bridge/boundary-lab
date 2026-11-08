# P1.5：恐慌阈值 + 突触重置

## 机制

- 环境仍第 10 tick 反转：read +10 / rest -10 → read -10 / rest +10
- 正常 10 tick 后，监控滚动 2-tick PE 和
- PE 和 > 3.0：触发 panic
- panic 后：
  - 清空全部 T(s,a,s') 计数
  - 5 tick 盲目探索，动作均匀随机
- 3 seeds，30 tick

## 结果

| seed | panic tick | panic 时 E | 首次 rest | 存活 tick | 结果 |
|---:|---:|---:|---:|---:|---|
| 1 | 13 | 18 | t15 | 19 | 死亡 |
| 2 | 14 | 6 | t15 | 20 | 死亡 |
| 3 | 12 | 6 | 无 | 14 | 死亡 |

**3/3 死亡。**

## seed 1

```text
t13 REV read E 30->18 PE=3.46 sum2=4.36 panic=True
t14 REV read E 18->6  PE=1.61 blind=True
t15 REV rest E 6->14  PE=1.61 blind=True
t16 REV rest E 14->22 PE=1.61 blind=True
t17 REV read E 22->10 PE=0.42 blind=True
t18 REV look E 10->6  PE=1.61 blind=True
t19 REV read E 6->0   PE=1.61
```

它 trigger 了，也 rest 了两次，  
但盲目探索又抽到 read/look，最后死。

## seed 2

```text
t14 REV read E 18->6 PE=3.65 sum2=5.06 panic=True
t15 REV rest E 6->14
t16 REV look E 14->10
t17 REV rest E 10->18
t18 REV look E 18->14
t19 REV read E 14->2
t20 dead
```

它找到了 rest，但 blind 阶段仍在随机 read/look。

## seed 3

```text
t12 REV read E 18->6 PE=3.94 sum2=5.09 panic=True
t13 REV look E 6->2
t14 dead
```

它 panic 后第一次 blind 抽到 look，直接死。

## 关键发现

### 1. 恐慌检测有效

反转后 PE 和迅速超过 3.0：

```text
seed1 4.36
seed2 5.06
seed3 5.09
```

### 2. 突触重置有效

T 被清零，旧模型惯性被打断。

### 3. 但“重置 + 随机”不是应激反射

随机探索不等同于求生。  
低能量时，随机动作的方差会杀人。

### 4. 它没有把 rest 变成反射

seed1/2 找到了 rest，但之后又随机回 read/look。  
seed3 连 rest 都没抽到。

## 判定

```text
P1.5：未通过。
恐慌触发：成功。
旧模型清除：成功。
盲目探索：失败。
存活：0/3。
```

这不是“自创生”。  
这是**自毁成功，重建失败**。

## 为什么

“清空 T + 均匀随机”只解决了**旧模型惯性**，  
没有解决**低能量下的动作安全**。

在 energy 6 时，随机三选一：

```text
rest  -> 活
read  -> 更接近死
look  -> 更接近死
```

它没有“必须 rest”的应激反射。

## 下一步如果要继续

不是再加随机，而是加：

- 能量感知的 panic policy
- panic 后强制 rest 的 safety prior
- 或保留一个“生存反射”不被重置

但那已经是**硬编码反射**，不再是纯粹重组。

## 资源

```text
8099 Qwen3-4B-Instruct：GPU active
8765 主岸：stopped
MemAvailable ~9.8Gi
CPU 低
```

## 文件

```text
~/boundary-lab/p1_5_reorg.py
~/boundary-lab/p1_5_reorg_result.json
~/boundary-lab/P1_5_REPORT.md
```

## 一句话

> **它成功自毁了旧自我，却在废墟上随机走进了坟墓。**
