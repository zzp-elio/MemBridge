# Task-010: 各 Benchmark 差异化题型 Prompt 矩阵、完整变量格式化与 Judge 超参调优

- **状态**：🟢 Completed (2026-10-13)
- **前置任务**：[`task-009-dual-schema-llm-judge.md`](task-009-dual-schema-llm-judge.md)
- **核心目标**：
  1. **Prompt 变量严格完整填充（Zero Unfilled Variables）**：
     - 构建通用健壮的模板格式化引擎（`format_prompt_template`），将记忆上下文、问题文本、时间锚点、标准答案、预测答案、选择题选项、细分题型等完整注入，确保 Answer LLM 与 Judge LLM 接收到的 Prompt 是 100% 渲染完成的终态文本，绝无残留未赋值 `{...}` 占位符；
  2. **细粒度题型级 Prompt 动态派发（Task-Level Prompt Dispatching）**：
     - 在 [`PromptProperties`](../../src/memory_benchmark/core/config.py) 中支持 `task_answer_prompts` 与 `task_judge_prompts` 映射表及 `get_answer_user(category)` / `get_judge_system(category)` 派发；
     - 在 [`configs/application.yaml`](../../configs/application.yaml) 中完整接入 5 大基准（LoCoMo、LongMemEval、BEAM、MemBench、HaluMem）及其原生题型（如 LoCoMo category 2 时间后缀、LongMemEval 4 类原生裁判、BEAM 3 档量规等）的真实提示词；
  3. **Judge 模型推理超参调优**：
     - 将 Judge LLM `max_tokens` 提升至 `4096`（彻底杜绝 CoT 推理截断），`temperature: 0.0`（纯确定性打分）；若 `max_tokens <= 0` 则解除限制；
  4. **完备验证与文档同步**：
     - 编写单测验证所有变量完整替换（无残留变量）、题型针对性提示词生效；
     - 同步更新 [`docs/decisions.md`](../decisions.md) (ADR-013)、[`docs/architecture.md`](../architecture.md) 与 [`STATE.md`](../../STATE.md)。

---

## 1. 裁剪边界与非目标（Scope & Non-Goals）

- **必须遵守的红线**：
  - 核心架构不引入第三方重型模板引擎（如 Jinja2），基于标准库轻量实现；
  - 维持 C/S 中间层黑盒原则与三大通用评测器架构不变；
  - `STATE.md` 严格 $\le 30$ 行、`AGENTS.md` 严格 $\le 50$ 行。

---

## 2. 执行步骤 Checklist

- [x] **Step 1：在 `src/memory_benchmark/core/` 中实现通用安全模板填充函数 `format_prompt_template`**
- [x] **Step 2：在 `PromptProperties` 中增加题型级动态派发支持，并在 `FrameworkAnswerReader` 与 `LLMJudgeEvaluator` 中接入**
- [x] **Step 3：在 `configs/application.yaml` 中配置放宽 `max_tokens: 4096`，并完整录入 5 大基准细分题型官方提示词**
- [x] **Step 4：编写测试验证变量 100% 完整填充无残留、题型针对性 Prompt 生效，全量 pytest 绿灯**
- [x] **Step 5：同步 `docs/decisions.md` (ADR-013)、`docs/architecture.md` 与 `STATE.md`**
