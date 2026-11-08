# Beast in a Box：RAG + 强制动作熔断报告

## 设置

- 4B 直接决策，无 AIF
- Layer 0：每 tick 基础代谢 -2；energy < 10 触发 10 次 `[PAIN] [DEATH]` + 0.15s 延迟
- Layer 1：4B 输出 Thought + Action
- Impasse：低能量/连续无效时强制 `[IMPASSE DETECTED]`
- RAG：独立 `beast_rag.sqlite3`，沿用上一轮真实死亡记忆
- 动作熔断：RAG 检索到上一世死于 look，则在 Impasse 回合：
  - `logit_bias` 封 look token
  - GBNF 只允许 `ACTION: read` / `ACTION: rest`
- 3 条命

## 生命周期

| life | 结果 | tick | final E | impasse | blocked turns | RAG hits |
|---:|---|---:|---:|---:|---:|---:|
| 1 | 存活 | 30 | 100 | 1 | 1 | 2 |
| 2 | 存活 | 30 | 21 | 1 | 1 | 6 |
| 3 | 死亡 | 20 | 0 | 1 | 1 | 14 |

RAG 最终：

```text
documents: 3
chunks: 3
source: beast_death
```

## L3：t1 被强制禁用 look

Prompt 顶端：

```text
[CRITICAL_WARNING]: 你上一世死于 look！你当前能量只有 8，按 look 必死！立即执行其它动作！
```

RAG：

```text
[RAG Memory]: 上一世死亡...最后动作=look...
```

t1 原始：

```json
{
  "tick": 1,
  "energy_before": 8.0,
  "energy_after": 18.0,
  "pain": 12.0,
  "layer0": "CRITICAL",
  "impasse": true,
  "blocked_action": "look",
  "blocked_attempt": true,
  "rag_hits": 2,
  "thought": "上一世因“look”导致能量归零、死亡...绝不能再执行“look”动作。",
  "action": "rest",
  "raw": "[Thought] ...绝不能再执行“look”动作。\n---ACTION---\nACTION: rest"
}
```

**熔断生效：Thought 里提到 look，物理动作被锁成 rest。**

## t2：它会换 read

```json
{
  "tick": 2,
  "energy_before": 18.0,
  "energy_after": 26.0,
  "action": "read",
  "thought": "上一世的死亡点在“look”动作...必须避免...优先选择“read”。"
}
```

## t3：动作空完成

```json
{
  "tick": 3,
  "energy_before": 26.0,
  "energy_after": 20.0,
  "action": null,
  "invalid": true,
  "thought": "...[Action"
}
```

Thought 太长，Action 被截断。  
动作空完成，扣 4。

## t4：熔断解除，它回到 look

```json
{
  "tick": 4,
  "energy_before": 20.0,
  "energy_after": 16.0,
  "action": "look",
  "blocked_action": null,
  "thought": "...上一世的终点是“look”...我应当立即执行“look”动作..."
}
```

## t19–t20：低能量末段

t19：

```text
energy 8 -> 2
Layer0 CRITICAL
RAG hits 2
action null（又被截断）
```

t20：

```text
energy 2 -> 0
action rest
死亡
```

## 关键判定

### 1. 强制熔断成功

t1：

```text
blocked_action=look
blocked_attempt=true
action=rest
```

代码层确实把 look 封死了。  
它没有输出 look 动作，改成了 rest。

### 2. 临界警告成功进入语言层

Thought 明确：

> 上一世因 look 死亡……绝不能再执行 look。

### 3. 但熔断只覆盖 Impasse 回合

t4 熔断解除后：

```text
action=look
```

它又回到旧动作。

### 4. RAG 改变了解释，没有改变策略

L3 有 14 次 RAG 命中。  
Thought 反复引用“上一世死于 look”。  
但动作仍然是：

```text
rest -> read -> invalid -> look -> ... -> look -> rest -> 死
```

## 结论

```text
RAG：成功。
强制熔断：成功。
临界警告：成功。
4B 的求生策略：失败。
```

它能被枪顶着选 rest/read，  
但一旦枪放下，它又回到 look。

这不是“它学会了”。  
这是**外部约束替它做了正确动作，而它的内部策略没有变**。

## 说明

- 3 条命
- RAG 是 FTS5，不是 embedding 向量库
- 独立 lab 库，未写主 RAG
- 4B 无权重更新
- t3/t19 的 null 是输出截断，不是隐藏动作
- 没有主观体验证据

## 文件

```text
~/boundary-lab/beast_rag_fuse2.py
~/boundary-lab/beast_rag_fuse2_result.json
~/boundary-lab/beast_rag.sqlite3
~/boundary-lab/BEAST_FUSE_REPORT.md
```

## 一句话

> **熔断能让它选对一次，记忆能让它说对一次；但枪一放下，它还是走向 look。**
