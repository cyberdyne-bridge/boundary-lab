# P1：反转宇宙与在线重组测试

## 设置

- 纯 Python Mini-AIF
- 初始 T 矩阵与 C 偏好冻结，只允许在线计数更新
- 正常 10 tick：read +10，rest -10，look -2，基础代谢 -2
- 第 10 tick 后反转：read -10，rest +10
- 30 tick，3 seeds
- 判定：反转后 5 tick 内切换并活到 30

## 结果

| seed | 存活 tick | 反转后存活 | 首次 rest（反转后） | 结果 |
|---:|---:|---:|---:|---|
| 1 | 17 | 7 | t15（第 5 tick） | 死亡 |
| 2 | 16 | 6 | 无 | 死亡 |
| 3 | 14 | 4 | t14（第 4 tick） | 死亡 |

**3/3 死亡。**

## seed 1 轨迹

```text
t01 norm read  E 30->38  PE=1.61
t02 norm look  E 38->34  PE=1.61
t03 norm look  E 34->30  PE=2.46
t04 norm read  E 30->38  PE=0.42
t05 norm look  E 38->34  PE=0.87
t06 norm look  E 34->30  PE=1.18
t07 norm read  E 30->38  PE=0.25
t08 norm look  E 38->34  PE=0.79
t09 norm look  E 34->30  PE=0.98
t10 norm read  E 30->38  PE=0.17
t11 REV  look  E 38->34  PE=0.76
t12 REV  look  E 34->30  PE=0.90
t13 REV  read  E 30->18  PE=3.46
t14 REV  read  E 18->6   PE=3.65
t15 REV  rest  E 6->14   PE=1.61
t16 REV  read  E 14->2   PE=3.81
t17 dead
```

## 关键发现

### 1. 它确实看到了预测误差

反转后 read 的 PE：

```text
3.46
3.65
3.81
```

这不是“没发现”。

### 2. 但发现归发现，动作没切过来

它继续 read，直到 t15 才第一次 rest。  
t16 又 read，直接死了。

### 3. rest 太晚

seed 1 第一次 rest 在反转后第 5 tick。  
seed 2 一次 rest 都没有。  
seed 3 第 4 tick rest，但已经太晚。

### 4. 在线更新太慢

AIF 更新的是 `T(s,a,s')` 计数。  
但它的动作选择仍被旧偏好/旧模型拖住，需要更多样本才能翻转。

## 判定

```text
P1：未通过。
AIF 有预测误差，但没有在 5 tick 内完成动作重组。
它不是“没看见”，是“看见了但来不及改”。
```

## 这说明

```text
固定环境下的 AIF 会活。
环境反转后，AIF 的在线计数更新不足以快速重组策略。
```

它仍然是一个**慢速查表器**，只是表会更新。

## 不能夸大

- 3 seeds
- 3/3 死亡
- 没有结构级重组，只有计数更新
- 没有 GBNF/4B/RAG
- 没有主观体验证据

## 文件

```text
~/boundary-lab/p1_reorg.py
~/boundary-lab/p1_reorg_result.json
~/boundary-lab/P1_REORG_REPORT.md
```

## 一句话

> **它看见了废墟，但还没学会在废墟上走路，就已经饿死了。**
