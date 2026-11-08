# 进化 / QD 全量测试报告

## 设置

- 10 个体 × 6 代
- Q 表基因组 + fallback 动作偏好
- harsh 扰动：read +10；其他 -10
- 每个体 30 tick，fitness = 生存 + 最终 energy
- 3 seeds

## 结果

| seed | best survival | best energy | 状态 |
|---:|---:|---:|---|
| 1 | 17 tick | 0 | 失败 |
| 2 | 30 tick | 27 | **存活** |
| 3 | — | — | 超时，未完成 |

seed 2 的 best：

```text
tick 30，energy 27，最后动作 rest
```

它学会了 `read/rest` 交替：

```text
read +10
rest -10
净能量 0
```

## 结论

- 进化**可以**找到生存策略（seed 2）
- 但不稳定：seed 1 只到 17 tick
- seed 3 超时，不能算成功
- 目前只能说是 **1/2 完成的 seed 存活**
- 这是 GA-lite，不是完整 QD
- 没有证明“重组自己”，只证明“种群里有一个表能活”

## 不能夸大

- 3 seeds，只有 2 个完成
- 30 tick 很短
- 种群小、代数少
- 没有 QD novelty/多样性机制
- 没有主观体验证据

## 资源

```text
MemAvailable ~3.2Gi
Swap 21Gi, used ~6.1Gi
OOM 无
lab VM stopped
主 VM restored
```

## 下一步

两条：

1. 扩大种群/代数，确认 seed 2 不是偶然
2. 若仍不稳，解冻 Active Inference

但不要因为 seed 2 成功就说“她会进化”。
