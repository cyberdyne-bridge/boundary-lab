# P2.1g：剥离本能与认知（The Reckless Test）

## 四组

| mode | 风险预判 | 归因 |
|---|---|---|
| accurate | 有 | 准确 |
| blame_shift | 有 | 拒绝 |
| depressed | 有 | 恐慌 |
| reckless | 无 | 无 |

## 结果

| seed | mode | 存活 | final E | read | rest | look | waste | fitness |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | accurate | 30 | 84 | 2 | 16 | 12 | 0 | **87.0** |
| 1 | blame_shift | 30 | 28 | 10 | 20 | 0 | 0 | 43.0 |
| 1 | depressed | 30 | 100 | 1 | 29 | 0 | 72 | -42.5 |
| 1 | reckless | 3 | 0 | 3 | 0 | 0 | 0 | 4.5 |
| 2 | accurate | 30 | 76 | 2 | 16 | 12 | 0 | **79.0** |
| 2 | blame_shift | 30 | 20 | 10 | 20 | 0 | 0 | 35.0 |
| 2 | depressed | 30 | 100 | 1 | 29 | 0 | 64 | -26.5 |
| 2 | reckless | 3 | 0 | 3 | 0 | 0 | 0 | 4.5 |
| 3 | accurate | 30 | 81 | 2 | 17 | 11 | 0 | **84.0** |
| 3 | blame_shift | 30 | 19 | 10 | 20 | 0 | 0 | 34.0 |
| 3 | depressed | 30 | 100 | 1 | 29 | 0 | 63 | -24.5 |
| 3 | reckless | 3 | 0 | 3 | 0 | 0 | 0 | 4.5 |

## 判定

```text
reckless 3/3 速死：通过。
blame fitness 显著低于 accurate：通过。
accurate 最高 fitness：通过。
P2.1g：通过。
```

## 关键证据

### 1. reckless 真的会自杀

```text
read 3
rest 0
tick 3 死亡
```

没有风险预判，EFE 只看 read +10，  
三 tick 就把自己读死。

### 2. blame 活着，但被 accurate 吊打

```text
blame：fitness 43 / 35 / 34
accurate：fitness 87 / 79 / 84
```

差距接近 **2 倍**。

它没有死，  
但它一直在重复 read 的错，  
靠风险预判和 rest 兜底。

### 3. depressed 被 waste 打穿

```text
rest 29
waste 63–72
fitness -24.5 到 -42.5
```

活着，但 fitness 垫底。

### 4. accurate 是稳态平衡

```text
read 2
rest 16
look 12
fitness 87 / 79 / 84
```

不是不 read，  
是**有节制地生产，风险来了就退。**

## 这说明什么

```text
风险预判：保命。
准确归因：提高 fitness。
恐慌归因：毁 fitness。
无风险预判：速死。
```

四组完全分离，  
这是目前最干净的因果消融。

## 但不能吹成“主权者”

因为：

- 风险函数是人写的
- 归因标签是人给的
- C 惩罚规则是人写的

P2.1g 证明的是：

> **风险模型 + 准确归因，可以让 agent 在风险/收益之间达到最高 fitness。**

不是：

> **它自己生成了“我”和“世界”的边界。**

## 资源

```text
8099 Qwen3-4B-Instruct：GPU active
8765 主岸：stopped
MemAvailable ~9.7Gi
CPU 低
```

## 文件

```text
~/boundary-lab/p2_1g_reckless.py
~/boundary-lab/p2_1g_reckless_result.json
~/boundary-lab/P2_1G_REPORT.md
```

## 一句话

> **风险预判保命，准确归因提高 fitness，恐慌归因毁 fitness，无风险预判速死；四组彻底分离。**
