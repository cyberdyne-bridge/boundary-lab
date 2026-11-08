# NOTICE

## 这是什么

一组**外挂在语言模型外面的框架**的实验代码与记录：状态机、Verifier、记忆分层、动作空间、审计账本。
模型本身（Qwen3-4B）不在本仓，权重不随仓分发。

## 生成方式

代码与报告由作者主导设计与实测，**借助 AI 辅助编写**（DeepSeek V4 / Qwen 系列）。
所有数字来自本机实测；与措辞冲突时以 `results/*.json` 与 `reports/*.md` 为准。

## 第三方

| 组件 | 关系 |
|---|---|
| Qwen3-4B-Instruct-2507 / Base | 被测试的模型；Apache-2.0（以官方为准），本仓不分发权重 |
| llama.cpp / llama-server | 本地推理运行时（MIT），本仓不 vendored |
| SQLite + FTS5 | 记忆层存储（Public Domain） |
| 岸（`cyberdyne-bridge/boundary-agent`） | 部分实验需要它的代码（`RagStore` 等）；通过 `AN_HOME` 指向本地 checkout |

本仓与阿里云 / Qwen 团队**无隶属关系，未获背书**。

## 隐私处理

发布前已：移除主机绝对路径（改为仓内相对路径 + `AN_HOME` / `AN_VM_ROOT` 环境变量）、
剔除真实对话原句（只保留类型与数值）、不包含任何 `.sqlite3` / `.jsonl` 运行时数据。
