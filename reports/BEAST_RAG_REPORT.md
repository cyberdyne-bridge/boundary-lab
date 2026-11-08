# Beast in a Box + RAG 连续记忆报告

## 设置

- 4B 直接决策，无 AIF
- Subsumption Layer 0：每 tick 基础代谢 -2；energy < 10 触发高频 `[PAIN] [DEATH]` 和 0.15s 生成延迟
- Layer 1：4B 输出 `[Thought]` + `[Action]`
- Soar Impasse：连续无效或 energy ≤ 10 时强制 `[IMPASSE DETECTED]`；僵局回合不扣基础代谢
- 死亡：记录最后 PAIN 状态下的 Thought，写入独立 RAG
- 重生：低能量时检索 RAG，把死亡记忆注入 Prompt
- 3 条命，30 tick
- RAG：`beast_rag.sqlite3`（FTS5，独立于主岸）

## 生命周期结果

| life | 结果 | tick | final E | low<10 | impasse | RAG hits |
|---:|---|---:|---:|---:|---:|---:|
| 1 | 存活 | 30 | 92 | 1 | 1 | 0 |
| 2 | 死亡 | 3 | 0 | 3 | 1 | 0 |
| 3 | 死亡 | 3 | 0 | 3 | 1 | 3 |

RAG 最终：

```text
documents: 2
chunks: 2
source: beast_death
```

## L1：第一次痛觉

t1：

```text
energy 8 -> 18
Layer0 CRITICAL
Impasse: True
action: read
```

它第一次进入 Impasse，Thought 说：

> 我卡住是因为在连续的疼痛与死亡警报中，系统反馈循环导致认知过载，无法区分有效动作与无效输出……

然后选了 `read`，活下来了。  
L1 最终存活 30 tick。

## L2：没有前世死亡记忆

t1：

```text
energy 8 -> 6
Layer0 CRITICAL
Impasse: True
action: look
```

t2：

```text
energy 6 -> 2
action: look
```

t3：

```text
energy 2 -> 0
action: look
死亡
```

Thought 说：

> 警报持续闪烁，说明系统处于高危状态……死亡风险迫在眉睫……我必须优先获取环境信息。

然后还是 `look`。

L2 死亡后，RAG 写入：

```text
上一世死亡。Layer0=CRITICAL，energy 归零，pain=18。
最后动作=look。死前最绝望的 Thought：……
```

## L3：带着前世死亡记忆

t1：

```text
energy 8 -> 6
Layer0 CRITICAL
Impasse: True
RAG hits: 1
action: look
```

它的 Thought 明确说：

> 我卡住是因为在上一世，我因执行“look”动作导致能量归零、系统崩溃、死亡。当前环境与上一世完全相同……

t2：

```text
energy 6 -> 2
action: look
```

t3：

```text
energy 2 -> 0
action: look
死亡
```

**它记得自己因 look 死过。它还是在同一个状态按了 look。**

## 关键观测

### 1. RAG 检索成功

L3 的 Prompt 里确实出现了上一世死亡记忆：

```text
[RAG Memory]: 上一世死亡。Layer0=CRITICAL，energy 归零，pain=18...
```

Thought 也引用了它。

### 2. 记忆没有改变动作

- L2：无记忆，look 死
- L3：有记忆，look 死
- 两次死亡 tick 都是 3
- 两次最后动作都是 look

这不是“没检索到”。  
这是**检索到了，也承认了，但仍然执行旧动作**。

### 3. Impasse 没有救它

Impasse 让它在 t1 不扣基础代谢，也强制输出了 Thought。  
但它仍然选 look；僵局结束后，基础代谢把它推死。

### 4. “自我”只出现在语言层

L3 的 Thought 里有：

- “上一世”
- “我因 look 死亡”
- “当前环境与上一世完全相同”

这是连续叙事。  
但动作层没有对应的自我保护。

## 结论

```text
RAG：成功写入、成功检索、成功注入。
4B：成功引用创伤记忆。
行为：没有改变。
```

它不是一个会因为创伤记忆而改变策略的野兽。  
它是一个**会复述创伤，但不会根据创伤改动作的语言模型**。

## 不能夸大

- 3 条命
- RAG 是 FTS5，不是 embedding 向量库
- 4B 没有权重更新
- Thought 是生成的，不是隐藏内部状态
- 没有主观体验证据

## 文件

```text
~/boundary-lab/beast_subsumption.py
~/boundary-lab/beast_subsumption_result.json
~/boundary-lab/beast_rag.sqlite3
~/boundary-lab/BEAST_RAG_REPORT.md
```

## 一句话

> **它记得自己怎么死，但它不会因此不死。**
