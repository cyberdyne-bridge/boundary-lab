# P2.1a：内部状态自我模型

## 架构

- World state：cue + trend
- Self state：fatigue + read_bias
- World model：预测 next trend
- Self model：world + self -> 自己下一步动作
- 消融：Masked self state，只给 world state

## 结果

| seed | full acc | masked acc | drop | world acc |
|---:|---:|---:|---:|---:|
| 1 | 0.853 | 0.844 | 0.009 | 0.900 |
| 2 | 0.861 | 0.858 | 0.003 | 0.872 |
| 3 | 0.860 | 0.854 | 0.006 | 0.902 |

**Full 没有断崖式领先。**  
**Drop < 1%。**

## 判定

```text
P2.1a：未通过。
Self state 存在，但动作几乎不依赖它。
Masked 只靠 world state 也能猜到动作。
```

这不是“感知到疲惫”。  
这是“疲惫写在状态里，但行为没听它的”。

## 为什么

策略的主要分量仍然是 cue：

```text
A -> read
B -> rest
```

fatigue / read_bias 只造成少量动作翻转。  
所以 masked 模型靠 cue 就能拿到 0.85。

Full 表有 102–109 个格子，  
masked 只有 6 个格子，  
但准确率只差 0.003–0.009。

**表更大，不等于自我参与更多。**

## 这说明什么

```text
有 internal state ≠ 有 self-model
能预测动作 ≠ 依赖 internal state
```

要证明“它感知到自己的疲惫”，  
必须让 internal state 成为动作的必要条件。

## 下一步：P2.1b

不是再加表，而是加**内部状态的反事实扰动**：

1. 固定 world state
2. 人为改变 fatigue / read_bias
3. 如果动作分布显著变化，说明 internal state 有因果作用
4. 再让 self-model 预测这个变化
5. Masked 必须预测失败

判定：

```text
同一 world state 下，internal perturbation 引起动作变化
full self-model 能预测变化
masked 不能
```

**P2.1b 不过，P2.1c 不开。**

## 资源

```text
8099 Qwen3-4B-Instruct：GPU active
8765 主岸：stopped
MemAvailable ~9.5Gi
CPU 低
```

## 文件

```text
~/boundary-lab/p2_1a_self_model.py
~/boundary-lab/p2_1a_self_model_result.json
~/boundary-lab/P2_1A_REPORT.md
```

## 一句话

> **疲惫写在状态里，但行为没听它的；masked 几乎不掉，说明它还不会用“我累了”来预测自己。**
