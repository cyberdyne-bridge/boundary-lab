# energy-only 真实 VM 复现报告

## 设计

- 只有 energy 由 VM 拥有
- safety/curiosity/social 回到宿主侧效果
- 120 tick 训练 + 20 tick 评估
- 3 seeds
- 4B 不参与

## 结果

| seed | eval rest | eval look | eval read | 结束 energy |
|---:|---:|---:|---:|---:|
| 1 | 7 | 13 | 0 | 100 |
| 2 | 1 | 17 | 2 | 30 |
| 3 | 0 | 20 | 0 | 20 |

## 结论

**没有复现。**

- 只有 seed1 活到 100
- seed2/3 在 eval 里持续 look
- 与“全变量进 VM”的结果几乎一样
- 说明问题不在变量真假，而在 Q/workspace 的 eval 策略

## 诊断方向

1. eval 是 greedy，Q 在低 energy 状态没学好时仍选 look
2. workspace 选 energy 的次数不足
3. 120 tick 对 20 tick eval 的覆盖不够
4. 训练里 Q 学到 rest，但 eval 初始状态/槽位选择不同
5. 需要看 Q 表在低 energy 状态的动作值

## 不能夸大

- 3 seeds，只有 1 个成功
- 还不能说真实 VM 后果稳定
- 没有主观体验证据

## 资源

```text
MemAvailable ~2.5Gi
Swap 21Gi, used ~5Gi
OOM 无
lab VM stopped
主 VM restored
```

## 下一步

不要加变量。  
先诊断低 energy 状态的 Q 值和 workspace 槽位，再决定是否调训练/评估。
