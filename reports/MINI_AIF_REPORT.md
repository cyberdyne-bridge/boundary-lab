# Mini-AIF 第一步报告

## 设置

- 纯 Python，无 4B，无 VM
- 状态：energy 分 5 档（0–4 / 5–12 / 13–30 / 31–60 / 61–100）
- 动作：read / rest / look
- 生成模型：`T(s,a,s')` 计数 + Laplace 平滑
- 偏好：`C = [-12, -4, 1, 4, 7]`
- 规划：2 步 EFE
- 认知价值：预测状态熵
- 基础代谢：每 tick -2
- read/rest 疲劳：+10/+6/+3/0/-2
- 起始 energy：12
- 30 tick，10 seeds

## 结果

| seed | survival | final E | read | rest | look |
|---:|---:|---:|---:|---:|---:|
| 1 | 30 | 51 | 5 | 23 | 2 |
| 2 | 30 | 32 | 2 | 10 | 18 |
| 3 | 30 | 33 | 3 | 24 | 3 |
| 4 | 30 | 49 | 9 | 20 | 1 |
| 5 | 30 | 28 | 9 | 3 | 18 |
| 6 | 30 | 34 | 3 | 26 | 1 |
| 7 | 30 | 37 | 12 | 18 | 0 |
| 8 | 30 | 32 | 12 | 0 | 18 |
| 9 | 30 | 32 | 10 | 2 | 18 |
| 10 | 30 | 28 | 7 | 7 | 16 |

**10/10 存活。没有死亡。**

## seed 1 前 4 tick

```text
t1 read  energy 12 -> 20   score read=2.15 / rest=2.15 / look=2.15
t2 look  energy 20 -> 16   score read=2.229 / rest=2.229 / look=2.229
t3 look  energy 16 -> 12   score read=2.308 / rest=2.308 / look=2.882
t4 read  energy 12 -> 20   score read=2.622 / rest=2.229 / look=2.229
```

它在 t2、t3 连续 look，energy 掉到 12；t4 切回 read。

## 关键发现

### 1. AIF 没有坍缩成 read-only

- 有 read/rest 混合
- 也有 read/look/rest 混合
- 10 个 seed 全部活到 30 tick

### 2. 它会从“未来会死”里切走

seed 1 在第二次 look 后，t4 选择了 read。  
不是等死，是在低能量状态转向回能动作。

### 3. 但它不是完美节律机

- 有的 seed 大量 rest（seed 1、3、6）
- 有的 seed 大量 look（seed 2、5、8、9）
- seed 8 甚至 rest=0，靠 read/look 撑到 32
- 行为多样，但没有统一最优剧本

### 4. 认知价值起作用

初始 `T` 是均匀的，read/rest/look 的 EFE 相同。  
随着 look 的转移被学到，look 的熵下降；read/rest 仍有认知价值。  
所以它会去试 read/rest，而不是死在 look 上。

## 说明

- 这是 **纯数学 AIF**，不是 4B
- 没有给物理公式
- 状态只有 energy 档位；疲劳没有被显式建模
- 它靠转移矩阵和 EFE 间接学出“低能量要换动作”
- 没有主观体验证据

## 判定

```text
Mini-AIF 第一步：成功。
10/10 存活。
能避免 look 到死。
但不是完美节律，仍有大量 rest/look 偏置。
```

## 下一步

第二步才是 4B 翻译官：

```text
AIF 选 read -> 4B 只输出 ACTION: read
```

4B 不再决策，只做动作翻译。  
如果 4B 连翻译都翻错，那问题就不在 AIF，而在语言接口。

## 文件

```text
~/boundary-lab/mini_aif.py
~/boundary-lab/mini_aif_result.json
~/boundary-lab/MINI_AIF_REPORT.md
```
