# lab 资源隔离

## 原则

1. **不加载第二个 4B。**
   lab 复用 `127.0.0.1:8099`，只起一个轻量 agent。
2. **一次只跑一个实验。**
   主岸聊天和 lab 测试不要同时进行；`llama-server` 是 `-np 1`，并发会排队。
3. **lab 关闭自动 wander / initiative。**
   `run-lab.sh` 已移除这些参数，避免后台自己生成请求。
4. **lab VM 只在需要时开。**
   默认 1GB / 2 vCPU；能不开就不开。
5. **主 VM 和 lab VM 不同时跑。**
   两个 QEMU 各 1–1.5GB，会挤压宿主。

## 启动 lab

用 systemd scope 限内存/CPU：

```bash
systemd-run --user --scope --collect \
  -p MemoryMax=768M \
  -p CPUQuota=50% \
  -p IOWeight=50 \
  -- run-lab.sh
```

说明：

- `MemoryMax` 只限制 lab agent，不限制 8099 的 4B
- 768MB 对 agent + SQLite + RAG 足够
- 50% CPU 防止测试把宿主拖满
- 这是临时 scope，Ctrl-C 就结束

## 需要 lab VM 时

```bash
# 先停主 VM（主岸聊天不需要 VM）
~/vms/an/an-vm.sh stop

# 启动 lab VM：2 vCPU / 1GB / SSH 2223
~/vms/an-lab/lab-vm.sh start
```

测试完：

```bash
~/vms/an-lab/lab-vm.sh stop
~/vms/an/an-vm.sh start   # 恢复主 VM
```

## 每次开跑前看三个数

```bash
free -h
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
systemd-cgtop -1
```

建议阈值：

```text
MemAvailable < 1GB      -> 不跑
GPU used > 5.2GB        -> 不跑
swap 正在明显增长        -> 停
```

当前基线：

```text
RAM used      ~12Gi / 15Gi
RAM available ~3.4Gi
GPU used      3.25GiB / 6GiB
```

lab agent 很轻，真正占资源的是 4B 和 VM。

## 测试窗口

- 每次 15–30 分钟
- 一次只做 A/B/C 里的一项
- 不并发、不后台、不自动重试
- 跑完就 stop，不留 lab 服务

## 严格隔离（可选）

如果要把模型进程也隔离：

1. 停主 8765 / 8099
2. 用 8098 起第二个 llama-server
3. 让 `run-lab.sh` 指向 8098
4. 测完停 8098，恢复主 8099

代价：6GB 显存放不下两个 4B，必须**串行**，不能同时在线。
