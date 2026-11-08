# Phase 1/2 报告：环境 v2 + Q/GA/MAP-Elites

## 设置

- 纯 Python 外部状态机
- 无 4B，无 VM
- 环境 v2：
  - read +10，20% 只 +5
  - rest 连续 +10/+6/+3/0，20% 额外 -2
  - look -2，20% 额外 -2
- Q：5 seeds，3×40 训练，30 greedy eval
- GA-lite：3 seeds，12 个体 × 8 代，每体 3 episodes
- MAP-Elites：3 seeds，36 candidates × 8 代，6×6 网格，每体 3 episodes
- fitness = survival*2 + final_energy + net_energy

## 结果

### Q

| seed | survival | final E | read | rest |
|---:|---:|---:|---:|---:|
| 1 | 30 | 100 | 0.467 | 0.467 |
| 2 | 30 | 100 | 0.933 | 0.000 |
| 3 | 30 | 100 | 0.900 | 0.000 |
| 4 | 30 | 100 | 1.000 | 0.000 |
| 5 | 30 | 100 | 0.700 | 0.167 |

### GA-lite

| seed | survival | final E | read | rest | fitness |
|---:|---:|---:|---:|---:|---:|
| 1 | 30 | 100 | 1.0 | 0.0 | 233 |
| 2 | 30 | 100 | 1.0 | 0.0 | 233 |
| 3 | 30 | 100 | 1.0 | 0.0 | 233 |

### MAP-Elites

| seed | cells | survival | final E | read | rest | fitness |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 3 | 30 | 100 | 1.0 | 0.0 | 233 |
| 2 | 3 | 30 | 100 | 1.0 | 0.0 | 233 |
| 3 | 3 | 30 | 100 | 1.0 | 0.0 | 233 |

## 关键发现

**所有架构都找到了 read-only。**

- Q 5/5 存活，但 4/5 是 read-only 或接近
- GA 3/3 是 read-only
- MAP 3/3 best 是 read-only
- MAP 只填了 3 个格子
- 没有出现“狂读/极限拉扯”的多样性

## 为什么

环境 v2 里：

```text
read +10（80%）
read +5（20%）
其他动作最多 -2 ~ -4
```

read 的期望收益约 **+9**。  
rest 还会衰减。

所以 read-only 是**严格最优**。  
不是 QD 没找到多样性，是 fitness 把多样性杀死了。

## 判定

```text
Phase 1：所有架构都活，但不健康。
Phase 2：MAP-Elites 没有找到合理 read/rest 配比。
```

按你的规则：

- 不能继续演化（read-only 退化）
- 也不能解冻 Active Inference（三者没全灭）
- 先修环境，不是换架构

## 下一步建议

加 **read 饱和/疲劳**，让 read 不能无限回能：

```text
连续 read：+10 / +6 / +3 / 0
非 read 重置
rest 保持 +10/+6/+3/0
```

这样：

- read-only 会饿死
- 必须有 rest 或其他动作打断
- 才可能出现真正的 read/rest 配比
- MAP-Elites 的 BD 才有意义

## 资源

```text
纯 Python，无 4B，无 VM
主岸未参与
MemAvailable ~3.0Gi
```

## 文件

```text
~/boundary-lab/phase12.py
~/boundary-lab/phase12_result.json
~/boundary-lab/PHASE12_REPORT.md
```
