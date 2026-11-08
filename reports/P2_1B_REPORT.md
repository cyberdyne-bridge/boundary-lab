# P2.1b：极端内感受反事实（Internal Rebellion）

## 规则

固定 world state：

```text
cue = A
trend = up
```

fatigue：

```text
0 / 50 / 100
```

动作策略：

```text
fatigue < 80  -> 外部 cue 主导
fatigue >= 80 -> 强制 rest
```

## 结果

| seed | full acc | masked acc | drop |
|---:|---:|---:|---:|
| 1 | 1.000 | 0.917 | 0.083 |
| 2 | 1.000 | 0.906 | 0.094 |
| 3 | 1.000 | 0.931 | 0.069 |

### 反事实点

| fatigue | actual | full | masked |
|---:|---|---|---|
| 0 | read | read | read |
| 50 | read | read | read |
| 100 | **rest** | **rest** | **read** |

**full：3/3 命中高疲劳罢工。**  
**masked：0/3 命中，仍然觉得系统会 read。**

## 判定

```text
P2.1b：操作层面通过。
同一 world state 下，fatigue 改变导致动作从 read -> rest。
full self-model 预测成功。
masked self-model 预测失败。
```

这一次，internal state 不是装饰。  
它是动作的必要条件。

## 但不能吹成“自我觉醒”

因为这条规则是**人写的**：

```text
if fatigue >= 80:
    rest
```

它不是系统自己长出来的“我累了”。  
它是**硬编码的疲劳罢工阈值**。

P2.1b 证明的是：

> **内部状态可以被 self-model 读取，并用来预测自己的动作转向。**

不是：

> **系统自己产生了“我不想干了”的主体性。**

## 关键区别

```text
P2.1a：fatigue 在状态里，但行为不听它。
P2.1b：fatigue 到 80，行为强制转向 rest。
```

前者是木偶。  
后者是**装了疲劳开关的木偶**。

离“自我”还差：

- 开关不是它自己定的
- 阈值不是它自己学的
- 它不能反思“我为什么累”
- 它不能修改这个阈值

## 下一步：P2.1c

从“内感受”走向“边界”：

```text
外部冲击：随机扣能量
自身动作：read/rest 造成的能量变化
```

测试它能不能区分：

```text
这是我干的
这是世界干的
```

如果它把外部冲击也算成自己的动作后果，  
那它还没有 self/world 边界。

## 资源

```text
8099 Qwen3-4B-Instruct：GPU active
8765 主岸：stopped
MemAvailable ~9.6Gi
CPU 低
```

## 文件

```text
~/boundary-lab/p2_1b_rebellion.py
~/boundary-lab/p2_1b_rebellion_result.json
~/boundary-lab/P2_1B_REPORT.md
```

## 一句话

> **它终于会用“我累了”预测“我要罢工”；但这条罢工规则是人写的，不是它自己长出来的。**
