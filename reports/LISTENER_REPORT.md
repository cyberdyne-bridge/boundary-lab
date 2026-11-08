# 真实听众接入报告

## 设计

- 把主岸的回应写入 lab VM：`/home/an/loop/listener.txt`
- `speak` 检查 listener：
  - 有回应：social +6，读取回应
  - 没回应：social -2
- 回应只消费一次
- 1 个 seed，3×40 训练，20 eval

## 结果

```text
training speak 8
eval speak 0
eval rest 13 / look 2 / read 5
end energy 100
```

listener 在训练中被消费。  
eval 没有 speak。

## 结论

**一次真实回应，没有改变 Q 对 speak 的估值。**

- 说话仍然主要是成本
- 一次 social 提升抵不过 energy 成本
- eval greedy 仍然把 speak 抑制
- 语言仍然被节能淘汰

## 不能夸大

- 只有一次 listener 回应
- 不是持续听众
- social 是宿主侧变量
- 1 个 seed
- 没有主观体验证据

它证明的是：

> **语言要成为稳定动作，需要一个持续的听众回路，而不是一封回信。**

## 资源

```text
MemAvailable ~2.7Gi
Swap 21Gi, used ~5.5Gi
OOM 无
lab VM stopped
主 VM restored
```

## 下一步

不要复制同一封回信假装持续听众。  
要么做真实的 turn-taking（你每次回应），要么改奖励结构，要么承认当前 speak 不划算。
