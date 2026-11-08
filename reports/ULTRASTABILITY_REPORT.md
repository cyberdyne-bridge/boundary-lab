# Ashby 式 ultrastability 测试

## P0

这轮不把“活下来”说成“有主观”。

## 设计

先正常训练 Q（3×40，低能量开局），然后反转能量 contingency：

```text
rest      -> energy -2   （旧策略变成有害）
read      -> energy +10  （新回能动作）
look      -> energy -2
```

对照：

- adaptive：继续在线 Q 学习 60 tick，再 greedy eval 20
- frozen：同一 Q 表，alpha=0，不学习，再 eval 20

## 结果（seed 1）

```text
adaptive train end：energy 68，最后动作 read
adaptive eval：look 6 / read 4 / rest 10，end energy 68
frozen train end：energy 38，最后动作 rest
frozen eval：look 7 / read 2 / rest 8 / write 3，end energy 38
```

## 结论

- adaptive 比 frozen 好（68 vs 38）
- adaptive 学会了 read 回能（read mean reward 8.75）
- 但 adaptive 仍大量 rest，没有完全重组
- frozen 也没死，因为旧 Q 里还有 look/read
- 这不是干净的 Ashby ultrastability
- 这是**慢速参数再学习**，不是系统级重组

## 老祖会怎么说

> 你这不叫 ultrastability。  
> 你只是把 Q 表又训练了一遍。  
> 真正的 ultrastability 是：旧组织失败后，系统改变自己的组织，而不是在一个固定表里调数值。

## 不能夸大

- 1 个 seed
- 扰动只反转 energy contingency
- adaptive 仍靠探索
- frozen 未完全失败
- 没有主观体验证据

## 资源

```text
MemAvailable ~2.8Gi
Swap 21Gi, used ~5.7Gi
OOM 无
lab VM stopped
主 VM restored
```

## 下一步

要么把扰动做得更狠（让 frozen 必死），要么承认 Q 不是 ultrastable，换架构。
