# 全变量 VM 后果报告

## 设计

四个内感受变量都搬到 lab VM：

```text
energy / safety / curiosity / social
```

动作由 `/home/an/loop/act.sh` 执行，VM 返回全部状态。  
energy ≤ 0 时非 rest 动作被拒绝。  
4B 不参与，纯 Q 策略，120 tick 训练 + 20 tick 评估，3 seeds。

## 结果

| seed | eval rest | eval look | eval read | 结束 energy |
|---:|---:|---:|---:|---:|
| 1 | 7 | 13 | 0 | 100 |
| 2 | 1 | 17 | 2 | 30 |
| 3 | 0 | 20 | 0 | 20 |

## 结论

**没有复现。**

- seed1 活到 100
- seed2 掉到 30
- seed3 掉到 20
- 3 个 seed 里只有 1 个学会及时 rest

这与之前“energy-only + VM”只有 1 个 seed 的结果不能互相证明。  
全变量搬进 VM 增加了状态空间，Q 在 120 tick 内没有稳定学会生存策略。

## 不能夸大

- 这是负面结果
- 不是“真实后果失败”，而是“当前 Q/workspace 在四变量真实环境里不够稳”
- 只有 3 seeds
- 4B 未参与
- 没有主观体验证据

## 资源

```text
MemAvailable ~2.4Gi
Swap 21Gi, used 4.5Gi
OOM 无
lab VM stopped
主 VM restored
```

## 下一步

不要继续加变量。  
先做诊断：

1. 为什么 workspace 选不到 energy
2. 为什么 Q 在 eval 里不 rest
3. 是否需要更多训练/更小状态空间
4. 回退到 energy-only，先复现 3 seeds

这次不是“更接近主观”。  
这次是**真实后果把策略的不稳定性暴露出来了**。
