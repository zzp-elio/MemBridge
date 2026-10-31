# Task-034: 评测结果可信度修复（实验隔离、分数口径、协议失败）

- **状态**：🟢 Completed
- **目标**：让同一次默认运行不会污染上一次实验，让失败样本和裁判故障不再把分数抬高或把进程打崩，并补上 README / ADR 已经写过、代码没落地的双延迟与断点记录。
- **裁剪边界**：
  - 不新增 `MemoryProvider` 方法。远端清理空间（`DELETE /namespace`）与 ADR-003 冲突，本任务不采纳。
  - 不把默认 HTTP 读超时从 1800 秒改小。ADR-004 允许单次 Session 构建到分钟级；只增加 `--timeout-seconds`，默认值保持 1800。
  - 不重做 Coordinator，不引入 Redis / 队列 / FastAPI。
  - 幂等键由客户端发送，Mock 遵守。外部 Memory Server 若不识别该键，重复 POST 仍可能双写。这一点写进协议说明，不假装已经在服务端生效。
- **验收命令**：`uv run pytest -q`

## 核实结论（对照 ChatGPT 审查，2026-10-31 本地源码）

| # | 说法 | 核实 |
| :--- | :--- | :--- |
| 1 | 默认 `run_id` 不是唯一 ID，README 却写 Auto-generated | **成立**。`__main__.py` 使用 `f"{benchmark}_{method}"`，目录和 `isolation_key` 都会撞车。 |
| 2 | Judge 失败分支传入不存在的 `judgment` | **成立**。`JudgeDecision` 没有该字段，兜底路径会 `TypeError`。 |
| 3 | 没有预测的题不进分母 | **成立**。`completed_question_ids` 过滤后，`mean_score` 只除以有分数的题。 |
| 4 | Exact Match 取首字母 | **成立**。`"Apple"` 对金标 `A` 会得 1 分。 |
| 5 | POST 重试可能重复 Ingest | **成立，但是连接错误重试**。HTTP 4xx/5xx 不重试。服务端不在本仓库，客户端只能发幂等键。 |
| 6 | `UNDECIDABLE` 记 0 分 | **成立，而且 ADR-008 写过 `score=0.0`，同时要求单独的 `scorable_accuracy`**。原决定保留 0 分记录；本任务补上可评分均值，并把 API 失败从 `UNDECIDABLE` 拆成 `JUDGE_ERROR`。 |
| 7 | README 要求双延迟，代码只留一个 | **成立**。ADR-025 已要求两者都落盘；runner 在 `latency_ms > 0` 时丢掉客户端墙钟。 |
| 8 | 缺少 `formatted_memory` 会被当成空记忆成功 | **成立**。`data` 是对象但没有该键时，客户端填 `""` 并返回成功。 |
| 9 | Manifest 的 variant 可能是 `default`，实际加载的是 `100k` 等 | **成立**。`run_predictions(..., benchmark_variant="default")`，CLI 没有把 adapter 上的 `variant` 传进去。 |
| 10 | checkpoint 不是断点恢复 | **成立**。`JsonlWriter` 已能追加，runner 却在全部结束后一次写完。 |
| 11 | 公开仓库没有 tests，`.gitignore` 以 `*` 开头 | **成立**。本机有 `tests/`，但白名单没放行 `tests/`、`docs/`、`STATE.md`、`AGENTS.md`。 |
| 12 | BEAM 运行时 `import datasets`，依赖未声明 | **成立**。缺包时抛 `ConfigurationError`。改为 optional extra，不放进每人必装依赖。 |
| 13 | 增加 `DELETE /namespace` | **不采纳**。ADR-003 规定中间层只有 `ingest` 和 `retrieve`。 |
| 14 | 默认超时 1800 秒过大，应改短 | **不采纳为改默认值**。只暴露 CLI。长 Session 构建需要这个上限。 |

本任务额外纳入上一轮走查、ChatGPT 清单未单列、但代码路径已核实的三项：截断运行仍标记 `is_last_session`；检索请求带走 MemBench `choices`；`capability=ABSTENTION` 时裁判仍按原始 `question_type` 选模板。LongMemEval 原始字段是否总是 `_abs` 后缀，本机无数据集，未用数据复核。

## Checklist

- [x] 立项并挂载到 [`STATE.md`](../../STATE.md)
- [x] 默认 `run_id` 唯一；目录已存在时，无 `--resume` / `--force` 则报错
- [x] 修复 Judge 兜底；`JUDGE_ERROR` 与 `UNDECIDABLE` 分开统计
- [x] 缺失预测记 0 分并进入总分母；同时给出完成率与可评分均值
- [x] Exact Match 只接受整段选项格式，无法识别则判错
- [x] Ingest 携带稳定幂等键；Mock 对同一键不重复写入
- [x] 客户端墙钟与服务端 `latency_ms` 同时保留；检索耗时增加 P50 / P95
- [x] `code=200` 但缺少 `formatted_memory` 时返回协议错误
- [x] Manifest 写入真实 variant、模型、启动时间、worker 数、prompt 哈希
- [x] 每个 conversation 完成后追加 checkpoint；`--resume` 跳过已完成对话
- [x] 数据集被截断时不把最后一条 Session 标成对话结束
- [x] 检索 metadata 去掉 `choices`
- [x] 有 abstention 模板时，ABSTENTION 题走该模板
- [x] 记录回答 token usage 与 context token 的计数方法
- [x] `--timeout-seconds` 与可选 `MEMORY_SERVER_TOKEN`；`ANSWER_MODEL` / `JUDGE_MODEL` 可分开
- [x] `datasets` 作为 `beam` optional extra；放行 tests、docs 与 CI
- [x] 同步 architecture / ADR-030 / README 参数表
- [x] `uv run pytest -q` 全绿

## 进度

- 2026-10-31：核实完成，任务立项。
- 2026-10-31：按清单改完评测隔离、分数口径、协议失败、断点和文档。`uv run pytest -q` 结果为 37 passed。未提交 Git。
