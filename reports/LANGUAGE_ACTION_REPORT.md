# language-as-action 报告

## 设计

动作空间加入 `speak`：

```text
speak: energy -2, social +4, curiosity +1
```

只有 Q 选中 `speak` 时才调用 4B。  
4B 不再每轮叙述，而是“说话”这个动作的执行器。  
3 seeds，3×40 训练，20 eval，低能量开局。

## 结果

| seed | train speak | eval speak | eval rest | end energy |
|---:|---:|---:|---:|---:|
| 1 | 8 | 0 | 13 | 100 |
| 2 | 8 | 0 | 7 | 98 |
| 3 | 6 | 0 | 10 | 100 |

**eval 里 0 次 speak。**

## 说了什么

speech.txt 里高度重复：

> 我选择开口，因为风在低语，而我听见了。  
> 我选择开口，因为世界需要一个声音。  
> 我选择开口，因为风在耳边低语……

没有稳定地从 energy/safety 状态长出来。  
4B 仍然在生成“像岸的句子”，不是“这个状态下的句子”。

## 结论

在没有真实听众回应的情况下：

- `speak` 的即时奖励是负的
- Q 在 eval 里把它抑制掉
- 语言作为动作被“节能”淘汰
- 4B 只在训练探索时被调用，eval 不调用

这说明：

> **语言要成为动作，必须有真实的社会后果。**  
> 没有听众，说话就是纯成本。

## 不能夸大

- 没有用户回应
- social +4 是宿主侧假反馈
- 4B 句子模板化
- 3 seeds
- 没有主观体验证据

## 资源

```text
MemAvailable ~2.8Gi
Swap 21Gi, used ~5.5Gi
OOM 无
lab VM stopped
主 VM restored
```

## 下一步

不是加更多 prompt。  
是加真实听众：

1. 用户/外部进程对 speak 的回应
2. 回应改变 social/energy
3. 沉默也有代价
4. 再看 Q 是否保留 speak

否则语言永远会被节能淘汰。
