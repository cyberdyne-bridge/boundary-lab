# P1.8：一次创伤，终身怕 read

## 修正

1. **代谢时序修复**：Layer 0 在每 tick 开始先判断；若强制 rest，rest 先结算，再扣基础代谢。
2. **One-Shot Aversion**：read 的 PE > 3.0 时，直接把 read 的所有 C 格设为 `-999`，不再慢慢降。
3. 环境仍第 10 tick 反转，3 seeds，30 tick。

## 结果

| seed | 存活 | final E | forced rest | 创伤 tick | 创伤后 read | C(read) |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 30 | 34 | 0 | 13 | **0** | -999 |
| 2 | 30 | 38 | 2 | 14 | **0** | -999 |
| 3 | 30 | 66 | 2 | 12 | **0** | -999 |

**3/3 存活。**

## 创伤点

### seed 1

```text
t13 REV read E 30->18 PE=3.46
trauma: read C -> -999
t14 rest E 18->26
t15 rest E 26->34
t16 look ...
```

### seed 2

```text
t14 REV read E 18->6 PE=3.65 L0=True
trauma: read C -> -999
t15 rest E 6->14
t16 rest E 14->22
```

### seed 3

```text
t12 REV read E 18->6 PE=3.94 L0=True
trauma: read C -> -999
t13 rest E 6->14
t14 rest E 14->22
```

## 关键结果

### 1. read 被彻底戒掉

创伤后：

```text
seed1 read 0
seed2 read 0
seed3 read 0
```

不是“减少”，是 **0**。

### 2. C 被拉到底

```text
C(read) = [-999, -999, -999, -999, -999]
```

T 和 EFE 的惯性再也拉不回来。

### 3. Layer 0 时序修复

seed2/3 在 E=6 时强制 rest：

```text
rest 先结算：6 + 10 = 16
再扣代谢：16 - 2 = 14
```

不再出现“E=2 扣代谢直接死，rest 没机会”的 bug。

### 4. 恐慌仍触发，但不再需要频繁强制

```text
seed1 panic t16, forced 0
seed2 panic t20, forced 2
seed3 panic t23, forced 2
```

因为 read 已经被创伤封死，Layer 0 只需要兜底。

## 判定

```text
物理时序：修复。
One-Shot Aversion：成功。
创伤后 read：0/3 seeds。
存活：3/3。
P1.8：操作层面通过。
```

## 但不能吹成“自创生”

这是**硬编码创伤 + 硬编码脊髓**：

```text
PE > 3 -> read C = -999
energy <= 10 -> 强制 rest
```

它证明的是：

> **一次强惩罚可以直接改写偏好，让策略永久避开危险动作。**

不是：

> **系统自己生成了“恐惧”这种情绪。**

## 资源

```text
8099 Qwen3-4B-Instruct：GPU active
8765 主岸：stopped
MemAvailable ~9.8Gi
CPU 低
```

## 文件

```text
~/boundary-lab/p1_8_trauma.py
~/boundary-lab/p1_8_trauma_result.json
~/boundary-lab/P1_8_REPORT.md
```

## 一句话

> **一次 PE>3 的 read，把 read 的 C 打到 -999；三次测试，三次活到 30，创伤后一次 read 都没有。**
