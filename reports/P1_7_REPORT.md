# P1.7：解冻 C + 偏好重塑

## 修正

- Layer 0：`energy <= 10` 强制 rest
- C 改成按动作分开的 `C[a][s]`
- 任何动作 PE > 3.0，下调该动作对应能量格的偏好
- 环境仍第 10 tick 反转

## 结果

| seed | 存活 | final E | 强制 rest | 放权后 read/rest/look | C(read) |
|---:|---:|---:|---:|---|---|
| 1 | 22 | 0 | 4 | 5 / 1 / 2 | [-14, -6.5, -1, 3.5, 7] |
| 2 | 30 | 10 | 7 | 7 / 2 / 4 | [-12.5, -5.5, 0.5, 4, 7] |
| 3 | 30 | 14 | 5 | 7 / 5 / 3 | [-12.5, -5.5, 0.5, 4, 7] |

**2/3 存活。**

## C 确实被重塑

初始 read 的 C：

```text
[-12, -4, 1, 4, 7]
```

被 read 的强 PE 毒打后：

```text
seed1: [-14, -6.5, -1, 3.5, 7]
seed2: [-12.5, -5.5, 0.5, 4, 7]
seed3: [-12.5, -5.5, 0.5, 4, 7]
```

中低能量格的偏好被压低了。  
这是真正的“情感更新”：read 不再只是“预测错”，而是“结果变差”。

## 但“害怕 read”还不够

放权后仍然大量 read：

```text
seed1: read 5 / rest 1 / look 2
seed2: read 7 / rest 2 / look 4
seed3: read 7 / rest 5 / look 3
```

C 降了，但没有降到压过 T/EFE 的惯性。  
它“知道 read 不好”，但动作仍经常选 read。

## seed 1 的死：新边界

```text
t20 read E 26->14
t21 read E 14->2   PE=4.07，C(read) 再降
t22 E 2 - 2(基础代谢) = 0，死亡
```

Layer 0 在 t21 已经触发，但 t22 **基础代谢先扣**，rest 还没执行就死了。

这是代谢时序 bug，不是策略失败。

## 判定

```text
C 解冻：成功。
read 偏好下降：成功。
放权后不选 read：失败。
存活：2/3。
P1.7：未完全通过。
```

比 P1.6 好：1/3 → 2/3。  
但还没到“情感上讨厌 read 到不碰它”。

## 还差什么

1. **代谢前反射**：Layer 0 在扣基础代谢前就判断 `energy - 2 <= 10`，或者先执行反射再扣代谢。
2. **C 更新更强/更全局**：不只更新 outcome bin，还要把 read 的整体期望拉低。
3. **动作偏好直接进策略**：C 更新后，softmax 仍可能被 T/EFE 拉回 read。

## 资源

```text
8099 Qwen3-4B-Instruct：GPU active
8765 主岸：stopped
MemAvailable ~9.9Gi
CPU 低
```

## 文件

```text
~/boundary-lab/p1_7_preference.py
~/boundary-lab/p1_7_preference_result.json
~/boundary-lab/P1_7_REPORT.md
```

## 一句话

> **C 被毒打后确实开始怕 read，但脊髓又漏了代谢前的一拍，皮层还是没完全长记性。**
