# 狠扰动 ultrastability 测试

## 扰动

```text
read  -> energy +10
look  -> energy -10
rest  -> energy -10
write -> energy -10
ask   -> energy -10
```

旧策略的 rest/look 都会死。

## 结果

```text
adaptive：
  train end energy 0
  eval look 11 / read 4 / rest 5
  eval end energy 0

frozen：
  train end energy 0
  eval look 17 / rest 2 / write 1
  eval end energy 0
```

## 结论

**Q 不是 ultrastable。**

- 旧策略在 harsh 扰动下直接死
- 在线 Q 学习 60 tick 也没学会只靠 read 活
- adaptive 和 frozen 都到 0
- 这不是“重组”，是“来不及学”

## 老祖会怎么说

> 你证明了 Q 表不是 ultrastable。  
> 它只会在固定动作空间里调数值，不会改变自己的组织。

## P1 判定

```text
P1 失败。
Q-learning 不满足 Ashby 式 ultrastability。
```

## 不能夸大

- 1 个 seed
- 60 tick 适应窗口
- 扰动很强
- 没有主观体验证据

## 资源

```text
MemAvailable ~3.0Gi
Swap 21Gi, used ~5.7Gi
OOM 无
lab VM stopped
主 VM restored
```

## 下一步

不要再调 Q 参数假装它能重组。  
要么换架构（随机重组/进化/active inference），要么承认当前 Q 只能做稳态控制，不是 ultrastable agent。
