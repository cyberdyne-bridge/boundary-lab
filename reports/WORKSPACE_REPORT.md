# 工作空间瓶颈报告

## 结构

7 个候选内容竞争 4 个槽位：

```text
E energy / S safety / C curiosity / O social
P percept / M memory / X surprise
```

- bottleneck：按显著性选 top-4
- off：7 个全部进入
- shuffle：随机 4 个
- Q 只看到进槽的内容

训练 3×30，评估 20。  
4B 只叙述，不选动作。

## 结果

| 模式 | Q 表 | 训练动作 | eval 动作 | 结束 energy |
|---|---:|---|---|---:|
| bottleneck | 21 | rest 19 / look 28 / read 15 / write 18 / ask 10 | rest 19 / look 1 | 100 |
| off | 58 | rest 13 / look 33 / read 18 / write 16 / ask 10 | rest 1 / look 9 / read 10 | 22 |
| shuffle | 141 | rest 7 / look 54 / read 13 / write 8 / ask 8 | look 17 / read 3 | 17 |

## 槽位统计（bottleneck）

```text
S safety     200/200
M memory     198/200
C curiosity  154/200
X surprise   124/200
E energy      83/200
O social      39/200
P percept      2/200
```

## 关键差异

```text
bottleneck: rest 19 / look 1  -> energy 100
off:        rest 1  / look 9 / read 10 -> energy 22
shuffle:    look 17 / read 3 -> energy 17
```

同一个 Q 学习器、同一个奖励，只改“哪些内容进入状态”：

- 瓶颈版学会休息，活下來
- 全量版状态空间太大，20 tick 评估里几乎不休息
- 随机 4 槽更糟，直接掉到 17

## 这说明

- 工作空间瓶颈**因果地**影响策略和生存
- 不是加了个 UI 面板
- 状态压缩不是“信息越少越好”，而是“选对内容”
- 但这也可能只是样本效率差异：小 Q 表更容易学

## 不能夸大

这不是 global workspace 意识。

- 显著性规则是我们写的
- Q 是 tabular
- 评估只有 20 tick、单 seed
- 4B 只是叙述器
- 没有主观体验证据

它证明的是：

> **在有限样本下，选对 4 个内容比塞进 7 个更能形成可生存的策略。**

## 资源

```text
MemAvailable ~2.5Gi
Swap 21Gi, used 1.4Gi
OOM 无
lab ports closed
主岸未参与
```

## 下一步

1. 复制多 seed，确认不是偶然
2. 巩固：Q/自我模型跨会话保留与漂移
3. 真实后果：VM 里 energy 低会真的失去行动能力

下一步先做多 seed 复现，不然 19/1 可能只是运气。
