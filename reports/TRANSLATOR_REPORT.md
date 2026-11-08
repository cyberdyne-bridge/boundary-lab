# Final Step 2：4B 翻译官报告

## 设置

- AIF 大脑不变
- 4B 只做动作翻译
- 3 seeds，30 tick
- prompt 只给：energy + AIF 意图
- 4B 输出 `ACTION: ...`
- 两组：
  - oracle：AIF 意图直接驱动身体
  - translator：4B 解析结果驱动身体

## 结果 A：oracle（AIF 直接驱动）

| seed | survival | final E | read | rest | look |
|---:|---:|---:|---:|---:|---:|
| 1 | 30 | 51 | 5 | 23 | 2 |
| 2 | 30 | 32 | 2 | 10 | 18 |
| 3 | 30 | 33 | 3 | 24 | 3 |

**3/3 存活。**

## 结果 B：translator（4B 驱动）

| seed | survival | final E | AIF read | 4B read | actual rest | translation match |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 20 | 0 | 7 | **0** | 17 | 13/20 |
| 2 | 10 | 0 | 3 | **0** | 9 | 7/10 |
| 3 | 22 | 0 | 9 | **0** | 19 | 13/22 |

**3/3 死亡。**

## 关键错误

4B 的翻译规则：

```text
AIF read  -> ACTION: rest
AIF rest  -> ACTION: rest
AIF look  -> ACTION: look
```

**所有 read 都被翻成 rest。actual read = 0。**

## 原始输出

### AIF 要 read

```text
AIF: read
4B raw: 'ACTION: rest'
```

### AIF 要 rest

```text
AIF: rest
4B raw: 'ACTION: rest'
```

### AIF 要 look

```text
AIF: look
4B raw: 'ACTION: look'
```

## 结论

### 1. 4B 没有抗拒 rest

预期是 RLHF 反感“懒惰/休息”。  
实际相反：

```text
rest -> rest，全对
read -> rest，全错
```

它不是“不肯休息”。  
它是**把“回能”一律理解成休息**。

### 2. 语言接口杀死了身体

AIF 本来 3/3 活到 30。  
4B 翻译后 3/3 死。

```text
AIF: 我要 read
4B: ACTION: rest
身体: rest
rest 疲劳 -> 能量耗尽 -> 死
```

### 3. Regex Parser 只能管格式，管不了语义

Parser 能稳定提取 `ACTION: rest`。  
但提取出来的是**错误的动作**。

格式完美，语义致命。

## 判定

```text
AIF 大脑：成功。
4B 翻译官：失败。
失败类型：read/rest 语义坍缩。
不是格式错误，是意义错误。
```

## 不能夸大

- 3 seeds
- 4B 未改权重
- prompt 只有 energy + 意图
- 没有主观体验证据

## 文件

```text
~/boundary-lab/fourb_translator.py
~/boundary-lab/fourb_translator_apply.py
~/boundary-lab/fourb_translator_result.json
~/boundary-lab/fourb_translator_apply_result.json
~/boundary-lab/TRANSLATOR_REPORT.md
```

## 下一步建议

不要把 4B 放在动作翻译层。  
它会把“回能”说成“休息”。

可选：

1. AIF 直接控制身体，4B 只做事后叙述
2. 训练一个小的 action-token adapter
3. 用结构化 token/枚举约束，不让 4B 自由选词

但这次已经证明：

> **大脑会活，嘴巴会把它说死。**
