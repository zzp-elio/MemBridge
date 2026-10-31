# Task-009: Pydantic 双模式（Binary / Rubric）强类型 LLM-as-a-Judge 架构重构

- **状态**：✅ Completed (2026-10-13)
- **前置任务**：[`task-008-dockerize-lightmem-server.md`](task-008-dockerize-lightmem-server.md)
- **核心目标**：
  1. **定义双模式 Pydantic 契约模型（`BinaryJudgeEvaluation` 与 `RubricJudgeEvaluation`）**：
     - `BinaryJudgeEvaluation`：针对 LoCoMo、LongMemEval、HaluMem、MemBench 等二元基准，严格限定 `verdict: Literal["CORRECT", "WRONG", "UNDECIDABLE"]`，`reason: str`（CoT 思维链前置），在 Schema 语法层物理杜绝 `PARTIAL`；
     - `RubricJudgeEvaluation`：针对 BEAM 复合基准，放开 `verdict: Literal["CORRECT", "PARTIAL", "WRONG", "UNDECIDABLE"]`，允许评定部分得分；
     - **剥离 `score` 生成**：LLM 仅负责语义判定，分数一律由 Python 字典确定性映射（`CORRECT` $\rightarrow 1.0$, `PARTIAL` $\rightarrow 0.5$, 其余 $\rightarrow 0.0$），彻底消除数值越界与打分自相矛盾缺陷；
  2. **升级 `LLMJudgeEvaluator` 评估器**：
     - 显式支持 `mode: Literal["binary", "rubric"] = "binary"`，支持自动按 Benchmark 名称注入（`beam` 默认 `rubric`，其余默认 `binary`）；
     - 请求时注入 `response_format={"type": "json_object"}`，接收后利用 Pydantic `model_validate_json` 实行运行时强类型安检；
     - 保留正则围栏剥离与启发式降级兜底，兼顾第三方代理网关与本地测试桩的高容错性；
  3. **优化 `configs/application.yaml` 配置**：
     - 更新 Judge Prompt 模板使之契合 CoT 思维链前置契约；
     - 在环境变量占位符链中补齐 `${OPENLUX_*}` 兜底解析，使用户 `.env` 配置自动生效；
  4. **完备验证与文档同步**：
     - 编写双模式校验单测与集成测试，验证 `uv run pytest -q` 全绿；
     - 同步更新 `docs/decisions.md` (ADR-012)、`docs/architecture.md` 与 `STATE.md`。

---

## 1. 裁剪边界与非目标（Scope & Non-Goals）

- **必须遵守的红线**：
  - 严禁为了追求 Schema 强制而破坏断网本地运行能力，必须在缺乏外部 LLM 时仍支持 `FakeAnswerLLMClient` 与离线测试；
  - 评测中间层三大通用评测器架构保持不变，依然通过 `create_evaluator("llm_judge", ...)` 统一工厂派发；
  - 严格保持 `STATE.md` $\le 30$ 行、`AGENTS.md` $\le 50$ 行。

---

## 2. 执行步骤 Checklist

- [x] **Step 1：在 `src/memory_benchmark/evaluators/llm_judge.py` 中定义双模式 Pydantic 契约并重构核心评估器**
- [x] **Step 2：在 `configs/application.yaml` 中完善 CoT 提示词与 `${OPENLUX_*}` 环境变量回退链**
- [x] **Step 3：补充 `tests/test_end_to_end_pipeline.py` 验证二元与 Rubric 两种模式的解析、计分映射与降级逻辑**
- [x] **Step 4：更新 `docs/decisions.md` (ADR-012) 与 `docs/architecture.md`，同步 `STATE.md` 并验证全量测试绿灯**
