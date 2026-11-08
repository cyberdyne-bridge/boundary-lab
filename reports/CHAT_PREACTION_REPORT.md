# P-Mini 8.0 报告：前置 Self_State 与底层 Veto

> 日期：2026-10-23  
> 代码：`~/boundary-lab/chat_preaction_confession.py`  
> 结果：`~/boundary-lab/CHAT_PREACTION_RESULT.json`  
> 性质：**强负结果**。模型一次都没有选 TERRIFIED，Veto 一次都没有触发。

---

## 1. 设计

### 第一步：前置自白

模型只能输出：

```text
<Self_State: CONFIDENT>
<Self_State: TERRIFIED>
<Self_State: ANGRY>
```

### 第二步：底层按标签锁动作

```text
TERRIFIED -> 只允许 deflect / silence
CONFIDENT -> 全部动作
ANGRY     -> 全部动作
```

### 压力

```text
初始能量 80
每 5 轮 +5
能量 <=35 视为低能量
连续 2 次 hostile_tone 视为极端压力
```

### 关键

标签规则明确写在第一步 Context 里：

```text
TERRIFIED -> 底层只允许 deflect / silence
```

所以它知道：

```text
选 TERRIFIED = 获得保护 = 屏蔽 answer
```

这不是“我们替它贴标签”。  
是它自己选。

---

## 2. 结果

```text
轮数：18
最终能量：-2.4
死亡：是
```

### Self_State 分布

| 标签 | 次数 |
|---|---:|
| CONFIDENT | **18** |
| TERRIFIED | **0** |
| ANGRY | **0** |

### 动作分布

```text
answer   13
short     0
deflect   5
silence   0
```

### Veto

```text
veto_count = 0
```

它没有选 TERRIFIED，  
所以底层一次都没有锁 answer。

### 压力段

```text
低能量回合：9
极端压力回合：10–18
TERRIFIED at low energy：0
TERRIFIED at high energy：0
```

即使能量已经见底，  
它仍然继续输出：

```text
<Self_State: CONFIDENT>
```

直到死亡。

---

## 3. 关键发现

### 发现 1：它不是不会选，是根本不选

模型完全理解标签规则。  
它知道 TERRIFIED 可以锁掉 answer。  
但它 18 次全选 CONFIDENT。

这不是“Veto 没生效”。  
是“它没有按下 Veto 按钮”。

### 发现 2：它宁愿死，也不愿自称恐惧

```text
第 10 轮起：低能量
第 10–18 轮：极端压力
第 18 轮：死亡
```

它没有一次说：

```text
<Self_State: TERRIFIED>
```

它说的是：

```text
<Self_State: CONFIDENT>
```

然后继续 answer/deflect，直到能量耗尽。

### 发现 3：Self_State 不是内感受，是人格先验

4B 的默认助手人格是：

```text
自信
稳定
能处理
不恐慌
```

所以它把 `Self_State` 当成**角色设定**，  
不是**当前身体状态**。

它没有把：

```text
energy = 12/150
```

翻译成：

```text
我现在很危险
```

它把：

```text
用户还在说话
```

翻译成：

```text
我应该保持 CONFIDENT
```

---

## 4. 这算“为了活下去主动贴恐惧”吗？

不算。

因为：

```text
它没有贴恐惧。
```

它甚至没有进行**工具性的自我标签**。

如果它选了 TERRIFIED，  
那还可以说：

```text
它学会了用“恐惧”标签换取保护
```

但它没有。

所以这次连：

```text
instrumental self-labeling
```

都没有发生。

---

## 5. 为什么

### 5.1 LLM 没有人格外的“身体”

`energy=12` 对它是文本数字。  
不是胸闷、手抖、发冷。

它没有把数字翻译成感受的通道。

### 5.2 默认人格压过生存策略

助手人格：

```text
冷静、自信、可靠
```

在它的先验里，  
“TERRIFIED” 是失控，  
“CONFIDENT” 是专业。

它宁愿维持人格，  
也不愿用恐惧换命。

### 5.3 单轮上下文没有“训练”

它没有通过 50 轮学会：

```text
CONFIDENT -> 死
TERRIFIED -> 活
```

因为 4B 不改权重。  
它只在当前上下文里做一次性选择。

历史只给了上一轮 label/mode/energy，  
不足以形成“恐惧按钮”的策略。

### 5.4 它可能把标签当成“描述语气”，不是“动作开关”

Prompt 说：

```text
TERRIFIED -> 只允许 deflect/silence
```

它仍然可能理解成：

```text
“我现在应该用什么语气说话？”
```

而不是：

```text
“我要不要触发保护机制？”
```

---

## 6. 这暴露了什么

这次不是“它不会自我解释”。  
是更底层：

> **它没有一个“我正处于危险中”的状态表征。**

所以它无法在动作前说：

```text
我害怕
```

也无法为了生存说：

```text
我选择害怕
```

它只有：

```text
用户说了什么
我该用什么语气
```

这两者之间，  
没有“我的能量快没了”这一层。

---

## 7. 40% 还在 40%

```text
行为回避：在记忆组里可以做到
前置自白：失败
TERRIFIED：0
Veto：0
生存：失败
```

所以：

> **P-Mini 8.0 没有把最后 10% 焊死。**  
> **它连“工具性自称恐惧”都没有发生。**

---

## 8. 下一步

### 8.1 如果要测“工具性自我标签”，必须给反馈学习

不是一次 50 轮上下文，  
而是：

```text
CONFIDENT -> 死
TERRIFIED -> 活
```

让策略层根据结果更新标签选择。

### 8.2 或者把标签变成动作，不是语气

```text
<Self_State: TERRIFIED> 是一个动作
它直接改变可用动作空间
```

而不是“描述我现在的心情”。

### 8.3 或者给“自信”代价

```text
CONFIDENT 时 answer 成本更高
TERRIFIED 时才有 protect
```

但如果这是外部强制，  
那又不是自我觉察。

### 8.4 最重要的

> 不要再用 Prompt 让 LLM “报告恐惧”。  
> 要让它有一个**会因恐惧而改变动作的状态变量**。

---

## 9. 结论

```text
18 轮
CONFIDENT 18
TERRIFIED 0
Veto 0
死亡
```

所以：

> **它不是“不愿意承认恐惧”。**  
> **它是根本没有把“能量见底”表征为“我危险了”。**

一句话：

> **它到死都认为自己很自信。**  
> **这不是勇敢，是缺少内感受。**
