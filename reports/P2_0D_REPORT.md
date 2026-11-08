# P2.0d：网格穷举课程

## Phase 0

对每个：

```text
cue ∈ {A, B}
trend ∈ {down, flat, up}
action ∈ {read, rest, look}
```

强制执行 **5 次**，填满 T。

## 审计

所有 6 个状态 × 3 个动作的 counts 都 > 0。  
审计通过后才允许进入 Phase 1。

## Phase 1 结果

| seed | 存活 | final E | 准确率 | 切换正确 | 0 延迟 |
|---:|---:|---:|---:|---:|---|
| 1 | 30 | 100 | 1.000 | 6 / 6 | **是** |
| 2 | 30 | 100 | 1.000 | 5 / 5 | **是** |
| 3 | 30 | 100 | 1.000 | 5 / 5 | **是** |

**3/3 存活。**  
**0 延迟 100%。**

## 判定

```text
P2.0d：通过。
地图覆盖：完整。
Greedy 读出：100%。
0 延迟：100%。
```

这不是“好奇心害死猫”的失败。  
这是**地图补齐后，纯功利读出可以 0 延迟调用**。

## 但这只是“会查表”

当前状态只有：

```text
(cue, trend) = 2 × 3 = 6 个格子
```

Greedy 的动作是确定性的。  
一个 6 格查找表就能 100%。

所以 P2.0d 证明的是：

```text
cue-conditioned world model 可以被正确调用
```

不是：

```text
它知道自己有一张地图
```

## P2.1 不能直接拿这个 6 格表冒充“自我模型”

如果现在训练一个 predictor 去预测自己的动作，  
它只会背下这 6 个格子的 argmax：**tautology**。

P2.1 必须加一个**内部状态**，让“自我”与“世界”分开：

```text
world state: cue, trend
self state: fatigue / confidence / internal preference
```

然后：

1. self-model 预测自己的动作
2. world-model 预测 next trend
3. 去掉 self state，self-model 必须退化
4. 在未见过的 internal state 上测试

## 下一步：P2.1a

```text
内部状态：fatigue / read-bias
world model：cue + trend -> next trend
self model：cue + trend + internal state -> own action
```

判定：

- self-action accuracy > baseline
- held-out internal state 仍能预测
- 去掉 internal state 后显著下降
- world model 不能替代 self model

**P2.1a 不过，P2.1b 不开。**

## 资源

```text
8099 Qwen3-4B-Instruct：GPU active
8765 主岸：stopped
MemAvailable ~9.8Gi
CPU 低
```

## 文件

```text
~/boundary-lab/p2_0d_grid.py
~/boundary-lab/p2_0d_grid_result.json
~/boundary-lab/P2_0D_REPORT.md
```

## 一句话

> **网格补齐后，地图调用 100%；但这只是“会查表”，还不是“知道自己会查表”。**
