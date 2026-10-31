# Task-026: --smoke 极简微抽样（1 会话 1 Session 1 题）与连通性验证完善

- **状态**：✅ Done
- **目标**：
  1. 优化 `--smoke` 数据集裁剪粒度：从原先的「1 对话、全量 Session、5 题」缩紧为极简的「1 对话、1 Session、1 题」，彻底杜绝外部真实 Memory Server（如 LightMem/Mem0）在冒烟时因全量 Session 建库耗时过长（数十分钟）的痛点，实现真正的「单次 Ingest + 单次 Retrieve」3 秒全链路冒烟；
  2. 保持 `--benchmark` 灵活性：缺省默认使用 `locomo`（最通用会话基准），但允许显式指定 `-b` 对 5 大基准中的任意适配器进行单题冒烟验证；
  3. 更新测试用例与相关文档（`README.md`、`docs/architecture.md`、`docs/decisions.md`）；
  4. 解答用户关于 5 大基准差异及 `mock` vs `http` 真实连通性测试的工程本质。

## Checklist

- [x] 立项并挂载至 `STATE.md`
- [x] 修改 `src/memory_benchmark/__main__.py` 的 `_slice_dataset`（`smoke: max_conversations=1, max_sessions=1, max_questions=1`）
- [x] 更新 `tests/test_end_to_end_pipeline.py` 中关于 `--smoke` 的测试断言
- [x] 同步更新 `README.md` 中的 `--smoke` 描述
- [x] 沉淀架构决策至 `docs/decisions.md` (ADR-022)
- [x] 运行 `uv run pytest -q` 确保所有用例全绿
- [x] 收口任务，更新 `STATE.md`
