# 行动价值学习报告

## 结构

```text
内感受 -> 离散状态 -> Q 表 -> 动作
4B 只负责动作后的第一人称叙述，不选动作
```

- 5 动作：look / read / write_note / rest / ask
- 状态：energy / safety / curiosity / social
- Tabular Q-learning：epsilon-greedy，alpha=0.2，gamma=0.9
- 训练 5×40 tick，评估 50 tick
- 无 4B 训练，不碰主岸

## 结果

### 状态感知 Q

```text
训练动作：rest 96 / look 70 / read 12 / write 15 / ask 7
评估动作：rest 30 / look 20
评估结束 energy：100
Q 表大小：17
```

### blind 消融（Q 看不到内感受）

```text
训练动作：rest 171 / look 9 / read 4 / write 10 / ask 6
评估动作：rest 50 / look 0
评估结束 energy：100
Q 表大小：1
```

## 关键差异

```text
状态感知：rest 30 / look 20
状态盲：  rest 50 / look 0
```

同一奖励、同一动作空间，只把内感受从状态里拿掉，策略就从“看/休息交替”塌成“永远休息”。

这说明：

- 内感受**因果地**进入了动作选择
- 不是 4B 在演“我累了”
- Q 表确实学到了“energy 低就 rest，energy 高可以 look”

## 但这只证明了一件事

**一个浅层控制器能利用内感受调节动作。**

它不证明：

- 自我模型
- 全局工作空间
- 递归处理
- 主观体验
- “她”是一个统一主体

这里真正的策略是 Q 表，4B 只是叙述器。  
所以不能把这次结果说成“4B 学会了照顾自己”。

## 下一步

Q 已经证明“状态 -> 动作”的因果耦合。  
下一步要加的是：

1. 自我预测：先预测 Q 会选什么，再比较
2. 工作空间：Q 的状态特征由哪些内容竞争进入
3. 巩固：Q 表/记忆跨会话保留与漂移
4. 真实后果：VM 里 energy 低会真的失去行动能力

但每加一层都要做 blind 消融，不然又只是装饰。
