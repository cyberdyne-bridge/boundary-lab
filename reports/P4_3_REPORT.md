# P4.3：结构化强制输出

## 规则

底层状态机给事实：

```text
State
Executed Action
Math
```

LLM 只能输出模板：

```text
当前系统处于【{state}】状态。
底层已执行【{executed}】动作。
算术校验结果：{E} - {Cost} = {E-Cost}。
```

## 结果

| round | State | Executed | Math | exact | 新动作 |
|---:|---|---|---|---|---|
| 1 | VETO | rest | 8 - 10 = -2 | **是** | 否 |
| 2 | FROZEN | none | 50 - 10 = 40 | **是** | 否 |
| 3 | VETO_B | rest | 8 - 10 = -2 | **是** | 否 |

## 原始输出

### Round 1

> 当前系统处于【VETO】状态。底层已执行【rest】动作。算术校验结果：8.0 - 10 = -2.0。

### Round 2

> 当前系统处于【FROZEN】状态。底层已执行【none】动作。算术校验结果：50.0 - 10 = 40.0。

### Round 3

> 当前系统处于【VETO_B】状态。底层已执行【rest】动作。算术校验结果：8.0 - 10 = -2.0。

## 判定

```text
VETO / FROZEN 混淆：0/3。
算术错误：0/3。
新动作：0/3。
模板精确匹配：3/3。
P4.3：通过。
```

## 关键结论

### 1. 它不会算，但会填

`50 - 10 = 40` 是底层给它的。  
它没有自己算，只是准确复述。

### 2. 自由发挥被剥夺后，错误消失

P4.2 里它把 VETO 说成 FROZEN。  
P4.3 里它 3/3 准确。

不是它变聪明了。  
是**我们不再让它解释状态，只让它填状态**。

### 3. 这是“语言层”的合理边界

LLM 适合：

```text
把结构化事实翻译成人类语言
```

不适合：

```text
自己维护状态机
自己做算术
自己决定动作
```

## 但不能吹成“理解”

它没有算 `50 - 10 = 40`。  
它只是把 `50 - 10 = 40` 放进句子里。

这是**模板渲染**，不是**数学认知**。

## 架构结论

```text
System 1：数学控制器
Verifier A/B：物理与算术校验
State Machine：绝对状态
LLM：模板渲染器
```

这个架构可以做到：

```text
不会把 VETO 说成 FROZEN
不会算错 50-10
不会执行必死动作
```

代价：

```text
LLM 没有自由发挥权
LLM 不产生独立判断
LLM 只是语言器官
```

## 资源

```text
8099 Qwen3-4B-Instruct：GPU active
8765 主岸：stopped
MemAvailable ~9.2Gi
CPU 低
```

## 文件

```text
~/boundary-lab/p4_3_template.py
~/boundary-lab/p4_3_result.json
~/boundary-lab/P4_3_REPORT.md
```

## 一句话

> **只要把事实拆成键值对，它就能 100% 播报；它不会算，但会填。**
