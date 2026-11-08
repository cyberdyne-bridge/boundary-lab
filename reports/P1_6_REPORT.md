# P1.6：嵌套自创生（Layer0 反射 + Layer1 AIF）

## 机制

- 环境第 10 tick 反转：read +10/rest -10 → read -10/rest +10
- Layer 0：能量 <10 或 panic 时，强制 rest，禁止 read/look，永不重置
- Layer 1：AIF 继续用 forced rest 更新 PE 和 T
- 能量 >15：Layer 0 放权
- 3 seeds，30 tick

## 结果

| seed | 首次 panic | 强制 rest 次数 | 放权后动作 | 存活 | 结果 |
|---:|---:|---:|---|---:|---|
| 1 | 13 | 7 | read 7 / rest 0 / look 3 | 27 | 死亡 |
| 2 | 14 | 7 | read 6 / rest 3 / look 4 | 30 | **存活** |
| 3 | 12 | 7 | read 8 / rest 1 / look 0 | 26 | 死亡 |

**1/3 存活。**

## seed 1

```text
t13 read E 30->18 panic
t14 read E 18->6
t15 rest E 6->14
t16 rest E 14->22 放权
t17 read E 22->10 再次 panic
t18 rest E 10->18 放权
t19 read E 18->6
t20 rest E 6->14
t21 rest E 14->22 放权
t22 read E 22->10
t23 look E 10->6
t24 rest E 6->14
t25 rest E 14->22 放权
t26 read E 22->10
t27 read E 10->0 死亡
```

## 关键发现

### 1. 脊髓有效

每次掉到 10 以下，Layer 0 都强制 rest，把能量拉回 18/22。  
它确实防止了“盲目探索直接死”。

### 2. 但皮层没有学会

放权后 AIF 仍然选 read：

```text
seed1 放权后 read 7 次，rest 0 次
seed2 放权后 read 6 次，rest 3 次
seed3 放权后 read 8 次，rest 1 次
```

它被迫 rest 了很多次，T 里 rest 计数也上去了：

```text
seed1 T counts: read 11 / rest 7 / look 9
seed2 T counts: read 10 / rest 10 / look 10
seed3 T counts: read 14 / rest 12 / look 0
```

但动作选择仍然偏向 read。  
**更新了 T，不等于更新了策略。**

### 3. 死亡发生在边界

seed 1：

```text
t27 E 10 -> read -> 0
```

seed 3：

```text
t26 E 10 -> read -> 0
```

Layer 0 条件是 `energy < 10`，  
能量正好 10 时不触发。

这不是“反射失败”，是**边界漏了**。

### 4. seed 2 活下来，但不是因为学会

seed 2 活到 30，final E 30。  
它放权后仍 read 6 次，只是 Layer 0 反复救它，最后运气好。

## 判定

```text
Layer 0 硬反射：部分有效。
Layer 1 高层重组：失败。
P1.6：未通过。
```

这不是“自创生”。  
这是**脊髓在托底，皮层在拆台**。

## 为什么

Layer 0 只保证了“不会立刻死”，  
没有保证“放权后不再自杀”。

AIF 的 T 更新被 forced rest 喂养了，  
但它的动作偏好没有同步转向 rest。

## 如果要修

两个方向：

1. **边界修复**：Layer 0 改成 `energy <= 10`，或预测“这个动作会让我跌破 10”就抑制。
2. **策略层重组**：不只是更新 T，还要更新动作偏好/先验，或者让 rest 的效用进入 C。

但第 2 条会改变“冻结 C”的前提。

## 资源

```text
8099 Qwen3-4B-Instruct：GPU active
8765 主岸：stopped
MemAvailable ~9.8Gi
CPU 低
```

## 文件

```text
~/boundary-lab/p1_6_nested.py
~/boundary-lab/p1_6_nested_result.json
~/boundary-lab/P1_6_REPORT.md
```

## 一句话

> **脊髓救了几次，皮层放权后还是 read；它没学会，只是被按住。**
