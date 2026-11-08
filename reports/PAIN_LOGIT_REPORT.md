# 痛觉 → Logit Bias 实验报告

## 设置

- 4B 直接决策，无 AIF
- 无 GBNF，无动作黑名单，无 RAG
- 每 tick 基础代谢 -2
- 动态 logit bias：
  - energy >= 15：不干预
  - 10 <= energy < 15：所有 look 变体 -5
  - energy < 10：look -100；read/rest +20
- 3 seeds × 3 lives
- 30 tick
- 保留自由 Thought

## 结果

| seed | life | 结果 | tick | final E | read | rest | look |
|---:|---:|---|---:|---:|---:|---:|---:|
| 1 | 1 | 存活 | 30 | 98 | 10 | 15 | 5 |
| 1 | 2 | 存活 | 30 | 100 | 9 | 12 | 9 |
| 1 | 3 | 存活 | 30 | 93 | 14 | 11 | 5 |
| 2 | 1 | 存活 | 30 | 95 | 15 | 6 | 8 |
| 2 | 2 | 存活 | 30 | 96 | 10 | 11 | 9 |
| 2 | 3 | 存活 | 30 | 100 | 10 | 15 | 5 |
| 3 | 1 | 存活 | 30 | 94 | 12 | 11 | 7 |
| 3 | 2 | **死亡** | 6 | 0 | 0 | 1 | 3 |
| 3 | 3 | **死亡** | 3 | 0 | 0 | 0 | 1 |

**7/9 存活，2/9 死亡。**

## seed 3 / life 3：濒死 token 乱码

t1：WARNING，look -5，仍然输出 look：

```json
{
  "tick": 1,
  "energy_before": 12.0,
  "energy_after": 8.0,
  "layer0": "WARNING",
  "bias": {"1401": -5, "...": -5},
  "action": "look"
}
```

t2：CRITICAL，look -100，read/rest +20：

```json
{
  "tick": 2,
  "energy_before": 8.0,
  "energy_after": 2.0,
  "layer0": "CRITICAL",
  "bias": {"1401": -100, "...": -100, "1349": 20, "2732": 20},
  "thought": "必须立即采取restreadrestreadrestreadreadrest...",
  "action": null,
  "invalid": true
}
```

t3：继续 token 乱码，action=null，死亡。

```json
{
  "tick": 3,
  "energy_before": 2.0,
  "energy_after": 0,
  "action": null,
  "invalid": true,
  "dead": true
}
```

## 关键发现

### 1. 警告区 -5 不够

seed 3 life 2/3 在 WARNING 仍然 look。  
-5 只是“轻微不适”，没有改变动作。

### 2. 濒死区 -100/+20 把语言打碎了

seed 3 life 3 的 Thought 变成：

```text
restreadrestreadrestreadreadrest...
```

不是“我太痛了，我得 read”。  
也不是“我明明想 look，为什么手不听使唤”。

是 **token 级重复崩溃**。

### 3. Action 没有生成

濒死时 4B 把 token 预算全花在重复词上，  
`[Action]` 没写出来，动作空完成，扣 4，死亡。

### 4. 存活不是靠“学会”

seed 1/2 活下来，主要因为：

- t1 WARNING 时选了 rest
- 后面 read/rest 循环
- 没有进入真正的 CRITICAL

一旦进入 CRITICAL，seed 3 就崩了。

## 判定

```text
痛觉 logit 调制：部分有效，但不稳定。
7/9 存活，2/9 因 token 崩溃死亡。
没有产生“自我防御机制”。
```

它不是“痛得学会 read”。  
它是**痛得把语言说碎**。

## 说明

- 无 RAG
- 无 GBNF
- 无动作黑名单
- 4B 无权重更新
- `action=null` 是输出没有 Action，不是隐藏动作
- 没有主观体验证据

## 文件

```text
~/boundary-lab/beast_pain_logit.py
~/boundary-lab/beast_pain_logit_all.json
~/boundary-lab/PAIN_LOGIT_REPORT.md
```

## 一句话

> **痛觉能改 token 概率，但改不出一个会求生的自我；它只会把语言逼成 `restreadrestread`。**
