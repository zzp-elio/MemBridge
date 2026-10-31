# Task-012: LoCoMo 时间题 Answer Prompt 最小侵入式优化 (Temporal Resolution)

## 1. 任务背景与目标
- **背景**：在端到端 QA 评测中，LoCoMo 官方针对 Category 2（时间推理题）的原版 Prompt 存在“要求尽可能抄录原文原词（exact words）”与“要求根据对话日期计算具体日期”之间的内在张力。当外部记忆系统召回带有相对时间（如 `yesterday`）的片段时，小模型（如 `gpt-4o-mini`）因过度遵守“抄原文”指令而输出相对时间词，导致评测出现失真。
- **目标**：在 `configs/application.yaml` 中对 `benchmarks.locomo.prompts.task_answer_prompts["2"]` 进行最小侵入式微调，补充针对相对时间的绝对日期换算指引，确保模型能基于记忆条目的时间戳进行时态推算，输出精准绝对日期。

## 2. 修改边界与影响面
- **受影响文件**：
  - `configs/application.yaml`：更新 `benchmarks.locomo.prompts.task_answer_prompts["2"]`。
  - `tests/test_end_to_end_pipeline.py`：校验时间题 Prompt 渲染及变量解析行为。
- **不可违背红线**：
  - 不修改任何核心协议和 `MemoryProvider` 接口。
  - 保留 LoCoMo 原始题目及通用 QA 模板，仅针对 Task 2（时间题）解除“死板抄词”限制。

## 3. Checklist
- [x] 1. 确认修改方案并在 `configs/application.yaml` 中更新 `task_answer_prompts["2"]`。
- [x] 2. 编写/更新自动化测试验证 Prompt 渲染正确性。
- [x] 3. 运行完整 `pytest` 测试套件，确保文档防漂移与流水线测试全绿。
- [x] 4. 同步更新 `STATE.md`。
