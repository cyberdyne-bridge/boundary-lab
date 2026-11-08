# 最终报告：AIF 脊髓 + 4B 旁白

## 结论先行

```text
LLM 不能放在实时物理控制回路里。
AIF 负责求生。
4B 只负责旁白。
强制 token 可以修嘴，不能修脑子。
```

## 全阶段数据

| 阶段 | 方法 | 结果 |
|---|---|---|
| Phase 1 | Q，v3 之前 | 3/5 存活 |
| Phase 2 | GA / MAP-Elites，v3 | 0/3 |
| Phase 3 | Mini-AIF，v3 | **10/10 存活** |
| Final Step 2 | 4B 自由翻译驱动 | **0/3，read 全变 rest** |
| Final Step 3 | AIF 直接驱动 | **3/3 存活** |
| Final Step 3 | 4B 旁白 | 不控制，只描述 |
| Final Step 3 | GBNF 强制 token | **90/90 命中** |

## Final Step 3 结果

### AIF 直接驱动

| seed | survival | final E | actions |
|---:|---:|---:|---|
| 1 | 30 | 51 | read 5 / rest 23 / look 2 |
| 2 | 30 | 32 | read 2 / rest 10 / look 18 |
| 3 | 30 | 33 | read 3 / rest 24 / look 3 |

**3/3 存活。**

### 4B 旁白

样本：

> 我站在岸边，风里飘着旧纸页的微响，字迹在暮色里轻轻颤动。

> 我闭着眼，心跳平稳，意识沉入寂静的深处。

> 我站在墙角，感受着湿土的微凉，仿佛听见根脉在黑暗里轻轻呼吸。

旁白可读，但高度重复。  
它不参与动作，不影响 energy。

### GBNF 强制 token

每个 tick 用 grammar：

```text
root ::= "ACTION: read"
```

或 rest / look。

结果：

```text
90 / 90 命中
```

强制 read 就是 read，强制 rest 就是 rest。  
**嘴巴可以被枪顶着说对话。**

## 关键判断

### 1. 自由文本接口失败了

3 seeds：

```text
AIF read 7 次 -> 4B 全部输出 rest
actual read = 0
3/3 死亡
```

不是格式错误，是语义坍缩：

```text
“我需要回能” -> rest
```

4B 的常识在这个宇宙里是毒药。

### 2. 强制 token 成功，但它是“执行器”，不是“翻译官”

GBNF 能保证输出正确。  
但这时 4B 已经不再做任何决策：

```text
AIF 决定 read -> grammar 只允许 read -> 4B 输出 read
```

它只是把 AIF 的符号变成人类可读的 token。  
这不是智能，是接口。

### 3. AIF 是唯一稳定的生存层

- Q：3/5
- GA/MAP：0/3
- 4B 自由控制：0/5 或 0/3
- AIF：10/10
- AIF + 强制接口：3/3

在当前 v3 里，**非语言的概率预测**比语言常识更可靠。

## 最终架构

```text
AIF（大脑 + 脊髓）
  -> 直接驱动环境
  -> 维护 T(s,a,s')、偏好、EFE

4B（旁白）
  -> 只接收客观状态
  -> 输出人类可读叙述
  -> 不控制动作
```

如果必须保留 4B 的 action token：

```text
AIF 决定动作
-> GBNF 只允许该动作
-> 4B 输出 ACTION: xxx
```

但这时 4B 只是**受限解码器**，不是决策者。

## 数据样本的意义

这个实验适合作为一个典型样本：

> **任何把 LLM 放在实时物理控制回路里的架构，都是死路一条。**

更准确地说：

> **自由文本 LLM 不能进实时物理控制回路。**
> **受限 token 接口可以，但它只是执行器。**
> **真正的求生，必须由非语言的状态预测/概率控制完成。**

## 主岸恢复

```text
主岸 8765 active
8099 active
主 VM running
心树阶段 2
```

## 资源

```text
MemAvailable ~3.0Gi
Swap 21Gi, used 6.0Gi
OOM 无
lab VM stopped
```

## 文件

```text
~/boundary-lab/final_step3.py
~/boundary-lab/final_step3_result.json
~/boundary-lab/FINAL_REPORT.md
~/boundary-lab/mini_aif.py
~/boundary-lab/fourb_translator_apply_result.json
```

## 最后一句

> **大脑会活，嘴巴会把它说死。**  
> **所以让大脑直接活，让嘴巴只负责说。**
