# Ashby 全量测试报告

## 设置

- 3 seeds
- 先正常训练 3×40
- harsh 扰动：read +10；look/rest/write/ask/speak -10
- 80 tick 适应 + 20 tick greedy eval
- 三组：
  - frozen：alpha=0，不学习
  - online：alpha=0.2，只学习
  - ashby：alpha=0.2 + 失败检测 + 低能量 Q 行随机化 + 25 tick 强制随机

## 结果

| seed | 条件 | 适应后 energy | eval 结束 energy |
|---:|---|---:|---:|
| 1 | frozen | 0 | 0 |
| 1 | online | 0 | 0 |
| 1 | ashby | 0 | 0 |
| 2 | frozen | 0 | 0 |
| 2 | online | 0 | 0 |
| 2 | ashby | 0 | 0 |
| 3 | frozen | 0 | 0 |
| 3 | online | 0 | 0 |
| 3 | ashby | 0 | 0 |

**9/9 全部死亡。**

## Ashby 细节

- 每个 seed 只触发 1 次重组
- 触发时 energy 17–27
- 强制随机 25 tick
- 有 read 出现，但不足
- 重组后仍回到 look/rest/write，最终 0

## 结论

**Ashby 随机重组也失败。**

- 不是“没触发”
- 不是“只差一点”
- 是随机重组在 25 tick 内找不到足够多的 read
- harsh 扰动下，5/6 动作有害，随机搜索太弱
- Q 行随机化没有改变动作空间结构

## P1 判定

```text
P1 仍未通过。
Q 不是 ultrastable。
最小 Ashby 随机重组也不是。
```

## 不能夸大

- 3 seeds
- 80 tick 适应窗口
- 扰动很强
- 没有主观体验证据

## 资源

```text
MemAvailable ~2.8Gi
Swap 21Gi, used ~5.9Gi
OOM 无
lab VM stopped
主 VM restored
```

## 下一步

按冻结顺序，解冻 **进化 / QD**。  
不是继续调 Ashby 的随机次数。  
Ashby 已经证明：在 5/6 动作有害的空间里，随机重组不够。
