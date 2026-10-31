# 任务单 Task-014: LoCoMo 题型隐式推断标签修正与高并发 LLM Judge 评测

## 1. 任务背景与核心目标
- **背景**：
  1. 用户深入探讨了 LoCoMo Category 3 的本质，指出其并非强化学习/策略迁移意义上的“环境泛化”，而是从离散碎片事实 $x, y, z$ 结合世界常识提炼潜在特征的“隐式推断/画像外推”。需将 11 维体系中 `generalization` 的中文标签从“记忆泛化应用”修正为“隐式推断/画像外推”，更准确地反映其机制。
  2. 此前 `outputs/locomo_full_10conv_openlux` 已完成 10 个 Conversation 全量 1,540 题的端到端问答预测（耗时 21 分钟完成 Ingest + Retrieve + Generate），但尚未执行 LLM Judge 语义裁判。
  3. 用户明确要求“对 LoCoMo 这四个题型做一个 LLM Judge，并发量开起来，搞快点”。
- **目标**：
  1. 在 `src/memory_benchmark/core/capabilities.py` 中更新 `UnifiedCapability.GENERALIZATION` 的 `label_zh` 为 `隐式推断/画像外推`（底层枚举保持 `generalization` 保证兼容性）。
  2. 在 `src/memory_benchmark/evaluators/llm_judge.py` 中加固高并发调用的鲁棒性（线程安全 Client 构建、网络超时/429 指数退避重试机制）。
  3. 在 `src/memory_benchmark/__main__.py` CLI 中支持 `--eval-run-dir` 参数，允许直接对现有产物目录进行离线独立评测，并将 `--max-workers` 正确透传至 `run_artifact_evaluation`。
  4. 对已完成的 1,540 题（`outputs/locomo_full_10conv_openlux`）以高并发（如 16~20 workers）启动完整的 LLM Judge 评测，输出 `summary.llm_judge.json` 与 `answer_scores.llm_judge.jsonl`。
  5. 确保 `pytest` 所有单元与回归测试 100% 通过（含文档防漂移门禁），并同步记录 ADR-016 与更新架构文档。

## 2. 修改边界与红线守则
- **保持双轨制**：`category`（1, 2, 3, 4）与 `capability` 必须同时体现在单题打分和 Summary 聚合中。
- **防止重复 Ingest 浪费**：严禁为了跑 LLM Judge 重新跑 10 个对话的提取写入和预测；必须直接重用已经生成并验证好的 `method_predictions.jsonl` 与 `evaluator_private_labels.jsonl`。
- **文档防漂移**：任务完成后同步更新 `STATE.md`、`docs/architecture.md` 与 `docs/decisions.md`。

## 3. Checklist
- [x] 在 `src/memory_benchmark/core/capabilities.py` 更新 `GENERALIZATION` 的 `label_zh` 为 `隐式推断/画像外推`。
- [x] 在 `src/memory_benchmark/evaluators/llm_judge.py` 优化高并发客户端初始化与瞬态网络异常重试机制。
- [x] 在 `src/memory_benchmark/__main__.py` 中添加 `--eval-run-dir` 选项，并向 `run_artifact_evaluation` 透传 `max_workers`。
- [x] 运行 `uv run pytest -q` 验证全部测试通过（24 passed）。
- [x] 启动高并发 LLM Judge（20 workers）对 `outputs/locomo_full_10conv_openlux` 进行 1,540 题全量语义评测。
- [x] 验证输出包含 `category_breakdown` 与 `capability_breakdown`，并产出得分报告。
- [x] 更新 `STATE.md`、`docs/architecture.md` 与 `docs/decisions.md` (ADR-016)。

## 4. 实测验收结果 (Run ID: `locomo_full_10conv_openlux`)
- **执行命令**：
  ```bash
  uv run python -m memory_benchmark \
    --eval-run-dir outputs/locomo_full_10conv_openlux \
    --benchmark locomo \
    --metrics llm_judge \
    --max-workers 20
  ```
- **评测总体表现**：
  - **总评测题目数**：1,540 / 1,540 题（100.0% 完成，无一报错中断）
  - **LLM Judge 总体语义准确率**：**43.51%**（670/1540 题判定为 `CORRECT`，对比词级 F1 的 28.72%，语义裁判有效识别了表达变形与等价回答）
  - **拒判人工复核量 (`human_review_count`)**：仅 15 题（占总题量 0.97%，包括 fact_recall 5 题、multi_hop 7 题、temporal 3 题）
  - **并发耗时**：20 线程并发下约 10 分钟平稳跑完全部 1,540 题

- **4 大题型原生得分对比 (Category Breakdown)**：
  1. **Category 2 (Temporal 时间与事件顺序)**：
     - LLM Judge 得分：**0.5109** (51.09%, 164/321 正确，榜首，表现最强)
     - 对比词级 F1：0.3434
  2. **Category 4 (Single-hop Fact Recall 事实回顾/抽取)**：
     - LLM Judge 得分：**0.4721** (47.21%, 397/841 正确)
     - 对比词级 F1：0.3080
  3. **Category 1 (Multi-hop Reasoning 跨会话多跳推理)**：
     - LLM Judge 得分：**0.2908** (29.08%, 82/282 正确)
     - 对比词级 F1：0.2081
  4. **Category 3 (Implicit Inference 隐式推断/画像外推)**：
     - LLM Judge 得分：**0.2812** (28.12%, 27/96 正确)
     - 对比词级 F1：0.1492（得分近乎翻倍！证明语义裁判成功识别了常识联想与画像外推的同义表达）

