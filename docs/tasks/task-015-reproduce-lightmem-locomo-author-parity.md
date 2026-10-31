# 任务单 Task-015: LightMem LoCoMo 72% 作者满血配置复现实验

## 1. 任务背景与核心目标
- **背景**：
  此前通用评测在默认 `top_k=10`（平均召回仅 279 Tokens）条件下跑出了 43.51% 的基线成绩。经取证，LightMem 原论文报告的 71.95% 建立在 **Top-60 深度召回（2,600+ Tokens 丰富上下文）** 与 **时间戳自动换算专属指令** 之上。用户要求直接启动该复现实验，验证满血状态下的准确率。
- **目标**：
  1. 在 `PredictionRunPolicy` 与 CLI 中支持 `--top-k`（默认 10，支持传入 60）。
  2. 支持 `--skip-ingest` 与 `--reuse-ingest-run-id`（复用已有持久化 Qdrant 向量库，避免重复耗费 20 分钟重新写入 272 个 Session）。
  3. 优化 `configs/application.yaml` 中的 `locomo` Answer Prompt，注入作者同款“基于记忆时间戳自动换算相对日期”与“精炼回答（5~6词）”的指令体系。
  4. 启动 LoCoMo 全量 10 个 Conversation、1,540 题的 Top-60 满血端到端回答生成与 LLM Judge 评测（Run ID: `locomo_author_parity_top60`）。
  5. 记录复现数据对比、分析结论并同步更新 `STATE.md`、`docs/architecture.md` 与 `docs/decisions.md` (ADR-017)。

## 2. 修改边界与红线守则
- **复用优先**：优先利用本地已持久化的 10 个对话 Qdrant 向量集合（`locomo_full_10conv_openlux_conv-*`），避免重复调用 Embedding 与 Ingest API。
- **配置与代码解耦**：Prompt 优化严格放在 `configs/application.yaml` 中，严禁在 Python 业务代码里硬编码提示词。
- **文档防漂移**：任务完成后同步更新 `STATE.md`、`docs/architecture.md` 与 `docs/decisions.md`。

## 3. Checklist
- [x] 在 `src/memory_benchmark/runners/prediction.py` 中为 `PredictionRunPolicy` 增加 `top_k`、`skip_ingest` 与 `isolation_prefix` 字段，并在执行时生效。
- [x] 在 `src/memory_benchmark/__main__.py` CLI 中暴露 `--top-k`、`--skip-ingest` 与 `--reuse-ingest-run-id` 参数。
- [x] 在 `configs/application.yaml` 中优化 LoCoMo 的 Answer Prompt（对齐作者的 Top-60 记忆分析与时间戳解析指令）。
- [x] 执行 `uv run pytest -q` 确保所有测试 100% 通过。
- [x] 启动全并发 Top-60 满血实验（Run ID: `locomo_author_parity_top60`）。
- [x] 运行 10 线程并发 LLM Judge 语义评测并分析最终准确率。
- [x] 更新 `STATE.md`、`docs/architecture.md` 与 `docs/decisions.md` (ADR-017)。
