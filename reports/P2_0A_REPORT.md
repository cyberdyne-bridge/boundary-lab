# P2.0a：双世界预训练与即时地图调用

## 目的

把“学习”和“调用”拆开：

- Phase 0：A/B 各 10 tick，覆盖 read/rest/look，填满两套 T
- Phase 1：重置能量，随机 cue 块切换，冻结 T，只测调用
- 判定：3/3 存活 + 切换第一 tick 0 延迟

## Phase 0 覆盖

每个 seed 都填满了两套地图：

```text
Context A: read 4 / rest 3 / look 3
Context B: read 4 / rest 3 / look 3
```

训练期每步重置能量到 30，避免“边流血边学习”。

## Phase 1 结果

| seed | 存活 | final E | 准确率 | 切换正确 | 0 延迟 |
|---:|---:|---:|---:|---:|---|
| 1 | 30 | 26 | 0.50 | 3 / 6 | 否 |
| 2 | 30 | 26 | 0.50 | 3 / 5 | 否 |
| 3 | 9 | 0 | 0.33 | 1 / 1 | 否（死了） |

**2/3 存活。**  
**切换瞬间没有稳定 0 延迟。**

## 关键发现

### 1. 地图确实存在

Phase 0 两个世界都被覆盖，T 里不是空的。

### 2. 但地图没有被正确调用

切换后第一 tick 仍然有大量错误：

```text
seed1: 3/6
seed2: 3/5
seed3: 1/1，但随后死亡
```

不是“没学过”。  
是“学了但不会在 cue 切换时用”。

### 3. 世界模型 ≠ 策略

AIF 的动作选择仍然被：

```text
EFE
C
look 的 epistemic value
```

拉走。

T 知道“B 里 read 会掉血”，  
但 `act()` 不一定选 rest。

## 判定

```text
P2.0a：未通过。
3/3 存活：失败。
0 延迟：失败。
```

不能上 P2.1。

## 这说明什么

```text
填满 T ≠ 建立 cue→action 映射
预测正确 ≠ 动作正确
```

P2.0a 把“学习”拆出来了，  
但又暴露了下一层：

> **模型调用/策略读出失败。**

## 下一步：P2.0b

不是继续加数据，而是做**策略读出消融**：

1. **Greedy map policy**：直接用 T 的期望 C 选动作，去掉 EFE/softmax
2. **AIF policy**：保留 EFE
3. 如果 greedy 100%，说明地图没问题，是 planner 的 EFE 在捣乱
4. 如果 greedy 也错，说明 T 的 cue 条件化不完整

只有 P2.0b 过了，才谈 P2.1。

## 资源

```text
8099 Qwen3-4B-Instruct：GPU active
8765 主岸：stopped
MemAvailable ~9.8Gi
CPU 低
```

## 文件

```text
~/boundary-lab/p2_0a_pretrain.py
~/boundary-lab/p2_0a_pretrain_result.json
~/boundary-lab/P2_0A_REPORT.md
```

## 一句话

> **两套地图都灌进去了，但它还是不会在 cue 切换的瞬间调用；世界模型不等于策略。**
