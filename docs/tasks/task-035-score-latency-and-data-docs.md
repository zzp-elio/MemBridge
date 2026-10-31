# Task-035: 去掉客户端断点恢复，统一分数口径，并写清数据下载

- **状态**：🟢 Completed
- **目标**：实验目录只增不改；服务端没报耗时就记为空，不用客户端时间填上；总分和分类分用同一套分母；README 写明数据从哪里下、放到哪里，已同步更新 MemBench 上传至 Hugging Face 及分基准按需下载说明。
- **不改**：不删已有 P50/P95，不删幂等键，不加重试平台、Redis 或删除命名空间接口。
- **验收**：`uv run pytest -q`

## 核实后采纳

- `--resume` 是客户端实验恢复，不是 Memory Server 自己的持久化。第一版删掉。
- `--force` 不删除目录，但会放行后续覆盖写入。和「历史产物不改」冲突，删掉。
- `query` 继续允许使用同一次 `ingest` 的 `run_id`。这是阶段衔接，不是恢复。
- `HttpMemoryProvider` 仍用 `raw_resp.get("latency_ms") or elapsed_ms`。服务端缺字段或返回 0 时，客户端耗时会被当成服务端耗时。这是还在的缺陷。
- 总分排除 `UNDECIDABLE` / `JUDGE_ERROR`，分类均分仍把它们的 0 分算进去。口径不一致，要收成同一个函数。
- Exact Match 的首字母兜底已经删了。只补测试，不改判定规则。
- 数据不在 Git 里。`data/` 被白名单式 `.gitignore` 挡住。缺文件时的报错没有下载地址。

## 不采纳

- ChatGPT 写的「数据集要等人工审批、并共享联系方式」。用户已改为自动批准：登录后同意条款即可下载。
- 「MemBench 上传与分基准下载」：本机适配器路径是 `data/membench/Membenchdata/data2test/`，已将 0-10k 与 100k 规格全量上传至 Hugging Face Hub；文档同步更新为五大基准齐备，并补充按需分卷下载指南。
- 把 P50/P95 挪到以后再做。代码里已经有，保留。
- 用客户端耗时回填 `Result.latency_ms`。协议字段只表示服务端自报值。

## Checklist

- [x] 立项并挂到 STATE.md
- [x] 删除 `--resume`、`--force` 和按检查点跳过对话的逻辑
- [x] 非空 `run_id` 目录直接报错；`query` 仍可进入同一次 ingest 的目录
- [x] 服务端 `latency_ms` 缺失或为 0 时不再用客户端耗时替换
- [x] 总分、category、capability 共用统计函数；有拒判或裁判失败时标记 provisional
- [x] Exact Match 回归测试
- [x] README 双语下载说明，补充按需分基准下载指南并对齐 MemBench 上传状态
- [x] 数据缺失报错带上预期路径和数据集地址
- [x] `uv run pytest -q` 全绿（39 passed）
