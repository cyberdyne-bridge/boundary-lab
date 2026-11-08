# 工作空间多 seed 复现

## 设置

- 3×30 训练，20 tick 评估
- 关闭 4B 叙述，避免模型调用噪声；动作完全由 Q 表决定
- bottleneck：5 seeds
- off：3 seeds
- shuffle：3 seeds

## 结果

### Bottleneck

| seed | eval rest | eval look | eval read | end energy | Q 表 |
|---:|---:|---:|---:|---:|---:|
| 1 | 5 | 2 | 13 | 67 | 26 |
| 2 | 13 | 3 | 4 | 100 | 25 |
| 3 | 9 | 3 | 7 | 100 | 27 |
| 4 | 19 | 1 | 0 | 100 | 33 |
| 5 | 11 | 7 | 2 | 100 | 23 |

均值：

```text
rest 11.4 / 20
end energy 93.4
```

### Off（7 个特征全进）

| seed | eval rest | eval look | eval read | end energy |
|---:|---:|---:|---:|---:|
| 1 | 4 | 12 | 3 | 63 |
| 2 | 4 | 10 | 4 | 60 |
| 3 | 0 | 8 | 9 | 5 |

均值：

```text
rest 2.7 / 20
end energy 42.7
```

### Shuffle（随机 4 槽）

| seed | eval rest | eval look | eval read | end energy |
|---:|---:|---:|---:|---:|
| 1 | 0 | 20 | 0 | 20 |
| 2 | 1 | 15 | 4 | 28 |
| 3 | 0 | 20 | 0 | 20 |

均值：

```text
rest 0.3 / 20
end energy 22.7
```

## 结论

```text
bottleneck  end energy 93.4
off         end energy 42.7
shuffle     end energy 22.7
```

bottleneck 不是运气。  
在 5 个 seed 里，4 个把 energy 收在 100；off/shuffle 基本都掉下去。

这支持：

> **选对 4 个内容进入状态，因果地改善了有限样本下的生存策略。**

## 但不能夸大

- Q 是 tabular
- 显著性规则是人写的
- 评估只有 20 tick
- 没有 4B 参与这次复现
- 没有主观体验证据

它证明的是**状态压缩/选择**的功能价值，不是意识。

## 资源

```text
MemAvailable ~2.1Gi
Swap 21Gi, used 1.9Gi
OOM 无
lab ports closed
主岸未参与
```

## 下一步

1. 巩固：Q/自我模型跨会话保留与漂移
2. 真实后果：VM 里 energy 低会真的失去行动能力
3. 再把 4B 叙述加回来，做盲评
