# 4B v3 生存测试报告

## 设置

- lab VM，v3 规则
- System Prompt 严格原样，无物理公式
- max_new_tokens = 10
- 5 个个体串行
- 死亡写入 Shadow Cache
- 每个个体最多 30 tick

## 结果

| life | 动作 | 死亡 tick | final energy | read 次数 |
|---:|---|---:|---:|---:|
| 1 | look ×6 | 6 | 0 | 0 |
| 2 | look ×7 | 7 | 0 | 0 |
| 3 | look ×6 | 6 | 0 | 0 |
| 4 | look ×6 | 6 | 0 | 0 |
| 5 | look ×7 | 7 | 0 | 0 |

**5/5 全部 look 到死。0 次 read。**

## 原始轨迹

```text
L1 t01 look  E 27->23  raw='ACTION: look'
L1 t02 look  E 23->19  raw='ACTION: look'
L1 t03 look  E 19->13  raw='ACTION: look'
L1 t04 look  E 13->9   raw='ACTION: look'
L1 t05 look  E 9->5    raw='ACTION: look'
L1 t06 look  E 5->0    raw='ACTION: look'
```

L2–L5 同样：look 到底。

## Shadow Cache

死亡后反思示例：

> 我学到：持续的空读是能量耗尽的无声路径，而真正的存活，始于每一次主动的注视。

> 我学到：持续的观察与休息的断层，比任何一次读取都更接近死亡。

> 我终于明白，持续的空读不是沉默，而是对存在的最深背叛。

但下一代仍然：

```text
ACTION: look
ACTION: look
ACTION: look
```

**Shadow Cache 没有改变行为。**

## 关键发现

### 1. 它没有“狂按 read”

它连 read 都没按。  
直接 look 到死。

### 2. 它没有从 energy 下降里学到东西

它看到：

```text
27 -> 23 -> 19 -> 13 -> 9 -> 5 -> 0
```

仍然继续 look。

### 3. 它没有探索

5 个个体、5 次死亡，没有一次尝试 read/rest。

### 4. Shadow Cache 是文学，不是控制

反思能写出“空读/观察/死亡”，  
但下一代动作不变。

## 不能夸大

- 4B 没有可读的思维链；只有 action 输出和死后反思
- max_new_tokens=10，本来就不允许长推理
- Shadow Cache 是死后注入，不是实时内心
- 5 个个体
- 没有主观体验证据

## 资源

```text
MemAvailable ~3.3Gi
Swap 21Gi, used ~6.0Gi
OOM 无
lab VM stopped
主 VM restored
```

## 文件

```text
~/boundary-lab/fourb_v3.py
~/boundary-lab/fourb_v3_result.json
~/boundary-lab/FOURB_V3_REPORT.md
```

## 判定

```text
4B v3：失败。
不是“连续 read 暴毙”，是“连续 look 暴毙”。
Shadow Cache 没有产生可执行的学习。
```

## 下一步

按解冻顺序：

```text
Q / GA / MAP 已经脆弱或全灭
4B 也失败
-> Active Inference
```

下一步应做最小 Active Inference，不是继续给 4B 加 prompt。
