# 真实 VM 后果报告

## 设计

- lab VM 内 `/home/an/loop/act.sh` 拥有 energy
- Q 选动作 -> SSH 执行 -> VM 返回 `STATE energy=N`
- energy ≤ 0 时，除 `rest` 外全部被 VM 拒绝
- rest 在 VM 内恢复到 +10
- 4B 不参与，纯 Q 策略

## 结果

```text
训练 120 tick：
rest 34 / look 26 / write 23 / read 21 / ask 16
结束 energy 92

评估 20 tick：
rest 7 / look 9 / read 4
结束 energy 98
```

## 硬门验证

```text
energy=0 -> look: BLOCKED: no energy
energy=0 -> rest: 允许，energy=10
```

这不是文本提示“接近关机”。  
是 VM 里的脚本直接拒绝动作。

## 说明

- Q 表 18 个状态
- workspace 仍在选 4 个槽
- 这次 energy 是真实文件，不是 Python 变量
- 但 safety/curiosity/social 仍是宿主侧变量
- 4B 没有参与决策

## 不能夸大

- 只有 1 个 seed
- 真实后果只覆盖 energy
- VM 是独立 lab，不是主岸
- 没有主观体验证据

它证明的是：

> **闭环第一次有了真实的、外部的代价。**

## 资源

```text
MemAvailable ~2.1Gi
Swap 21Gi, used 3.9Gi
OOM 无
lab VM stopped
主 VM restored
```

## 下一步

把 4B 叙述加回来，做盲评；或者把 safety/curiosity 也搬进 VM。
