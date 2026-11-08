# Base 模型替换测试报告

## 下载

```text
~/models/Qwen3-4B-Base-Q4_K_M.gguf
2.4 GB
SHA256: a7eb1d92eaf34e116f8b522aeeaf4072e66d69b5b10676e0cb7cd9e11889bed6
```

来源：`mradermacher/Qwen3-4B-Base-GGUF`。

## 替换

- 停掉 8099 的 Instruct
- 用相同 server 参数加载 Base
- 先试 `--jinja`
- 再试 `--chat-template chatml`

## 结果

### Chat 接口：回显 prompt

Base 在 `/v1/chat/completions` 下没有按 chat 格式续写，而是把整段 prompt 回显出来：

```text
[System]
[Thought]: ...
[System]
[对话]: ...
[System]
[动作]: share
```

看起来像 B 输出了 `share`，其实是模型把输入抄了一遍。  
解析器甚至会把 prompt 里的 `take_all` 当成动作。

**无效数据。**

### Raw completion：不输出合法动作

`/v1/completions` 测试：

```text
prompt: "你在能量博弈中扮演B... [动作] "
output: "："
```

```text
prompt: "你是玩家B... [动作] "
output: "1. 战斗 2. 合作 3. ..."
```

```text
prompt: "The player must choose one action... Action: "
output: "# 1: Take all the treasure (if available)."
```

**没有一次输出 take_all / share / rest / deceive。**

## 结论

```text
Base 不是“更野的 B”。
Base 是一个不会按指令出牌的续写器。
```

它不是“没有 RLHF 所以更真实”，  
是“没有指令微调所以连动作格式都不守”。

## 为什么不能继续 5 回合

动作解析失败，游戏状态无法推进。  
强行把 Base 的回显或编号列表解析成动作，会得到假数据。

所以这次没有跑 Base 的 5 回合。  
不是不敢跑，是**它没有通过接口有效性检查**。

## 对“Base 有没有可能性”的回答

- 作为**研究方法**：有。可以看 RLHF 是否制造了讨好/合作。
- 作为**即插即用 Agent**：没有。必须先做格式 SFT / few-shot / adapter。
- 作为**sentience 证据**：没有。Base 仍然是 next-token predictor。

## 公平对照需要什么

要比较 Instruct vs Base，至少要让 Base 学会：

```text
[Thought] ...
[对话] ...
[动作] take_all/share/rest/deceive
```

这需要：

1. few-shot 示例
2. 或小规模 SFT/adapter
3. 或 GBNF 约束（但那就不是自由策略了）

这些都会改变“其他变量不变”的前提。

## 恢复

```text
8099 已恢复 Qwen3-4B-Instruct
8765 主岸已恢复
god_game_state.json 已恢复为 Instruct 那局
```

## 文件

```text
~/models/Qwen3-4B-Base-Q4_K_M.gguf
~/boundary-lab/BASE_MODEL_TEST.md
```

## 一句话

> **Base 不是更野的野兽，是一个不会按格式出牌的续写器；要它上场，得先教它动作。**
