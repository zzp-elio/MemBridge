# 任务单 Task-013: LoCoMo 10 个独立 Conversation 并发评测运行器与 CLI 支持

## 1. 任务背景与核心目标
- **背景**：LoCoMo 数据集共包含 10 个完全独立的对话样本（`Conversation`），共计 560 个 Session 与 1986 个 QA 问题。此前评测流水线中 `run_predictions` 采用外层单线程串行遍历各 Conversation，耗时较长；且 `LightMemServer` 已具备基于 `ThreadingHTTPServer` 及 `isolation_key` 物理/逻辑隔离的并发处理能力。
- **目标**：
  1. 在 `src/memory_benchmark/runners/prediction.py` 中基于 Python 标准库 `concurrent.futures.ThreadPoolExecutor` 实现 Conversation 级别的线程并发执行。
  2. 保持确定性：各 Conversation 的结果记录在收集后按对话原始索引严格升序归并，确保不论单线程还是多线程并发，输出的 Artifacts 序列完全一致。
  3. 在 `src/memory_benchmark/__main__.py` CLI 中暴露 `--max-workers`（默认 1），并正确透传至 `PredictionRunPolicy`。
  4. 为 `run_logger.py` 补充线程安全锁，防止多线程写终端/日志时格式交错。
  5. 补充针对 `max_workers > 1` 的自动化回归测试。
  6. 启动 LoCoMo 完整 10 个独立 Conversation 的并发评测实测。

## 2. 修改边界与红线守则
- **只使用 Python 标准库**：严禁引入复杂第三方分布式调度框架，使用标准 `ThreadPoolExecutor`。
- **完全解耦与隔离**：各对话使用独立的 `isolation_key`（`{run_id}_{conv_id}`），互不侵入。
- **确定性落盘**：并发执行后按 `conversation_index` 归并排序，预测记录与 prompt 记录顺序确定。
- **文档防漂移**：任务完成后同步更新 `STATE.md`、`docs/architecture.md` 与 `docs/decisions.md`。

## 3. Checklist
- [x] 在 `src/memory_benchmark/utils/run_logger.py` 中为文件写入添加 `threading.Lock` 保护。
- [x] 在 `src/memory_benchmark/runners/prediction.py` 中封装 `_execute_single_conversation`，并在 `policy.max_workers > 1` 时通过 `ThreadPoolExecutor` 并行处理，结果按对话索引归并。
- [x] 在 `src/memory_benchmark/__main__.py` 增加 `--max-workers` 参数，并透传给 `run_predictions`。
- [x] 在 `tests/test_end_to_end_pipeline.py` 中编写 `max_workers=3` 的并发回归测试 `test_concurrent_conversation_prediction_runner`。
- [x] 执行 `uv run pytest -q` 确保所有 23 个测试通过（含文档防漂移校验）。
- [x] 同步更新 `docs/decisions.md` (ADR-015) 与 `docs/architecture.md` (Section 9)。
- [x] 运行真实的 LoCoMo 10 个 Conversation 全并发评测。

## 4. 实测验收结果 (Run ID: `locomo_full_10conv_openlux`)
- **执行命令**：
  ```bash
  uv run python -m memory_benchmark \
    --benchmark locomo \
    --method http \
    --server-url http://127.0.0.1:8000 \
    --max-workers 10 \
    --confirm-api \
    --run-id locomo_full_10conv_openlux
  ```
- **核心指标总览**：
  - **总会话完成度**：10 / 10 Completed (0 Failed)
  - **总问题完成度**：1,540 / 1,540 Evaluated (排除 446 条对抗样本)
  - **总体 F1 得分**：`0.2872` (28.72%, 严格词级重合判分)
  - **平均检索耗时 (`mean_retrieve_latency_ms`)**：`34.28 ms` (本地 MPS 嵌入检索超高速)
  - **平均上下文 Token 长度 (`mean_retrieved_context_tokens`)**：`279.47 tokens`
  - **总构建写入耗时 (`total_ingest_latency_ms`)**：`3,204,499.88 ms` (272 个 Session 提取写入)
  - **实际并发墙钟耗时**：约 21 分钟 (相较单线程预计 3.5 小时，加速比达到 ~10x)

- **4 大统一记忆认知维度分项得分 (`summary.f1.json`)**：
  1. **L2 时空与状态演进 (`temporal`, Category 2)**：F1 = **0.3434** (321 题，受益于 Task-012 Answer Prompt 时态消歧优化，得分最高)
  2. **L1 静态事实与抽取 (`fact_recall`, Category 4)**：F1 = **0.3080** (841 题)
  3. **L1 多证据/跨会话推理 (`multi_hop`, Category 1)**：F1 = **0.2081** (282 题)
  4. **L4 记忆泛化应用 (`generalization`, Category 3)**：F1 = **0.1492** (96 题)


