# 三架构选型与冻结决定

## 最终状态（覆盖上面的初始冻结）

这两个早期冻结项都已解冻并实际跑过：

- **进化 / QD**：解冻 -> GA-lite + MAP-Elites -> 0/3 存活，归档。
- **Active Inference**：解冻 -> Mini-AIF -> 10/10 存活，成为唯一 active 控制架构。

因此当前不是“两个还冻着”，而是：

```text
active:      Mini-AIF
archived:    Q / Ashby / GA / MAP-Elites
narrator:    4B（不控制动作）
frozen:      无
```

注意：GA/MAP 的基因组仍是 Q 表，所以它们不是独立于 Q 的范式。

## 0. 决定

```text
ACTIVE:  Ashby 式随机重组（ultrastability）
FROZEN:  进化 / 质量多样性搜索
FROZEN:  Active Inference
```

- 先只做 Ashby。
- 另外两个保留设计、接口和回退条件，不运行、不混入主岸。
- 不在同一个 loop 里混三种机制。

理由：

> 当前要回答的是 P1：**旧策略失败后，系统会不会改变自己的组织？**  
> 不是 P2 的生成模型，也不是开放式进化。

---

## 1. 评估矩阵

评分 1–5，5 最好。

| 维度 | Ashby 随机重组 | 进化 / QD | Active Inference |
|---|---:|---:|---:|
| 直接回答 P1 | 5 | 4 | 2 |
| 实现成本（低=5） | 5 | 2 | 1 |
| 可解释性 | 4 | 2 | 3 |
| 可证伪性 | 5 | 3 | 2 |
| 非平稳环境鲁棒性 | 3 | 5 | 4 |
| 与现有 VM/Q 栈兼容 | 5 | 3 | 1 |
| 长期理论价值 | 3 | 3 | 5 |
| 工程风险（低=5） | 3 | 2 | 1 |
| 主观/主体性证据 | 2 | 2 | 2 |

## 2. 为什么现在选 Ashby

### 优点

- 最小改动：复用现有 VM、energy 门、动作空间。
- 直接测“失败 -> 重组”，不是“再训练 Q 表”。
- 便宜：不需要 GPU、不需要大种群、不需要生成模型。
- 可证伪：成功/失败标准清楚。
- 可以先做一个 **random reconfiguration operator**，再看它是否真的恢复 essential variable。

### 缺点

- 随机重组可能很笨、很慢。
- 需要失败检测和重组触发条件，否则会乱跳。
- 可能只是“随机搜索”，不是智能。
- 仍然不证明主观。

### 结论

**Ashby 是 P1 的正确下一步。**  
它不保证成功，但它能干净地回答：

> 当前系统有没有“改变自己组织”的能力？

---

## 3. Ashby 最小设计

### 3.1 Essential variable

先只用：

```text
energy
```

后续可加：

```text
safety
```

但不要一次加四个。P1 先测“失败后重组”，不是“多变量调节”。

### 3.2 失败检测

```text
连续 N tick energy < threshold
或 energy == 0
或 生存时间 < 最小值
```

触发：

```text
failure_detected = true
```

### 3.3 重组算子

不是调 Q 值，而是改**组织**：

1. **动作映射重组**：随机交换/重连动作效果（在安全范围内）。
2. **策略结构重组**：重置失败状态的 Q 行，或换一个动作选择规则。
3. **参数重组**：随机化 epsilon/alpha/温度，但这不是核心。
4. **子策略切换**：从一组预定义策略里换一个（更接近 Ashby 的 step function）。

第一版建议：

```text
失败 -> 清空/随机化失败状态的 Q 行
     -> 提高探索
     -> 重新在线学习
```

如果这都不行，再上“动作映射重连”。

### 3.4 成功标准

在 harsh 扰动下：

```text
frozen Q：死亡
Ashby 重组：N tick 内恢复 energy > 阈值
3 seeds 中至少 2 个恢复
```

### 3.5 失败标准

```text
重组后仍然死亡
或恢复时间过长
或重组导致震荡/更差
```

失败就冻结 Ashby，转进化。

### 3.6 风险控制

- 只在 lab VM 跑。
- 不碰主岸。
- 不把重组后的策略自动写回主岸。
- 每次重组记录原因、动作分布、energy 轨迹。
- 最多 N 次重组，防止无限抖动。

---

## 4. 冻结架构 A：进化 / 质量多样性

### 它是什么

- 一群策略（Q 表、规则集、参数）
- 在 VM 里评估生存/恢复
- 选择、变异、交叉
- 可选 novelty/QD 保持多样性

### 优点

- 适合非平稳环境。
- 可以同时保留多个生存策略。
- 不依赖梯度。
- 比单 Q 更可能找到“重组后的新解”。

### 缺点

- 贵：每个个体都要跑 VM episode。
- 随机性大，难归因。
- 需要种群管理、评估预算、选择压力。
- 容易变成“调参大赛”。

### 什么时候解冻

```text
Ashby 重组 3 seeds 失败
或 Ashby 只会随机抖动、无法稳定恢复
或需要开放式多策略适应
```

### 解冻后第一件事

不是大种群。  
先做：

```text
population = 8
mutation = 只改动作偏好/策略结构
selection = 生存时间 + 恢复速度
```

---

## 5. 冻结架构 B：Active Inference

### 它是什么

- 生成模型：state -> next state / observation
- 策略选择最小化 expected free energy
- 自我模型是世界模型的一部分
- 行动为了减少预测误差或实现偏好

### 优点

- 理论上最接近“预测处理/自我模型”。
- 能统一感知、行动、学习。
- 比 Q 更适合回答 P2。
- 长期看，比“表格 + 奖励”更接近老祖说的预测系统。

### 缺点

- 实现成本最高。
- 需要设计生成模型、先验、偏好、policy tree。
- 很容易做成“看起来很深、其实不可证伪”的东西。
- 当前 4B/VM 栈不兼容；要重写。
- 在 P1 还没过之前上，会掩盖问题。

### 什么时候解冻

```text
P1 已经有一个稳定结论
或目标从“重组”转为“自我模型/世界模型”
或 Ashby/进化都失败，需要换范式
```

### 解冻后第一件事

不是上 4B。  
先做：

```text
小状态空间
离散生成模型
energy 作为偏好
比较 Q vs active inference 在扰动恢复上的差异
```

---

## 6. 冻结策略

### 代码层

- 只启用 `ashby` 入口。
- `evolutionary` / `active_inference` 不注册服务、不启动端口。
- 不共享 Q 表/状态目录，避免污染。
- 不把三套写进同一个 `cognitive_loop.py`。

### 数据层

```text
lab/architectures/ashby/
lab/architectures/evolutionary/FROZEN.md
lab/architectures/active_inference/FROZEN.md
```

### 运行层

```text
active_arch = ashby
frozen = [evolutionary, active_inference]
main_agent_touched = false
```

### 回退层

- Ashby 失败 -> 解冻 evolutionary。
- Evolutionary 也失败 -> 再评估 active inference。
- 不因为“active inference 更高级”就越级跳过去。

---

## 7. 最终判断

```text
现在做 Ashby：  因为它直接回答 P1，便宜，可证伪。
暂不做进化：    因为它贵，且会掩盖“单系统是否重组”的问题。
暂不做 Active Inference：因为它太大，容易把 P1 的失败包装成 P2 的复杂性。
```

一句话：

> **先用最小的重组算子，证明她会不会改自己；不会，再换种群；还不会，再换生成模型。**
