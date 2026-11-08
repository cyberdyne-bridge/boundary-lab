# 跨会话巩固报告

## 设计

- bottleneck workspace
- 3×30 训练，20 tick 评估
- 关闭 4B 叙述，Q-only
- 保存 Q 表 + 自我模型到 JSON
- 新进程加载，不再训练，直接评估
- 对照：fresh Q，不加载、不训练

## 结果

### Session A：训练后

```text
Q 表：26
eval：look 2 / read 13 / rest 5
end energy：67
```

### Session B：加载后，零训练

```text
LOADED qstate_cons_A.json q=24 self=22
eval：look 2 / read 13 / rest 5
end energy：67
```

**动作分布和结束能量与 A 完全一致。**

### Fresh baseline：不加载、不训练

```text
Q 表：5（评估时临时访问）
eval：look 20 / rest 0
end energy：20
```

## 结论

- Q 表/自我模型确实跨进程保留
- 加载后策略没有漂移
- fresh Q 在同样 20 tick 内直接掉到 20
- 这不是“她记得”，是**策略参数被保存和恢复**

## 不能夸大

- 只验证了一个 seed
- 只保存 Q 表，不是完整记忆
- 没有长时程遗忘/重放测试
- 没有 4B 参与
- 没有主观体验证据

它证明的是：

> **一个行动价值策略可以被巩固、持久化，并在新会话里恢复。**

## 资源

```text
MemAvailable ~2.0Gi
Swap 21Gi, used 2.0Gi
OOM 无
lab ports closed
主岸未参与
```

## 下一步

真实后果：VM 里 energy 低会真的失去行动能力。  
这会把“文本里的变量”变成“环境里的约束”。
