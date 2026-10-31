# Task-005: 仿 Spring Boot `application.yaml` 配置注入架构与三大通用评测器统一

- **状态**：✅ Completed (2026-10-12)
- **前置任务**：[`task-004-cli-and-deps-slimming.md`](task-004-cli-and-deps-slimming.md)
- **核心目标**：
  1. **构建仿 Spring Boot 的配置架构（`.env` + `configs/application.yaml` + `${VAR:default}` 占位符解析 + Dataclass 自动反射绑定）**：实现代码与配置/Prompt 数据彻底分离，彻底删除 `src/memory_benchmark/config/`（236 行）、`src/memory_benchmark/prompts/`（641 行）与 `configs/llm.toml`；
  2. **收敛评测器为 3 个标准通用实现（`ExactMatch`、`F1`、`LLMJudge`）**：砍掉为 5 个数据集分别硬编码的 8 个专属评测器文件与 `src/memory_benchmark/metrics/` 目录（共减少约 1,400 行），并在 `LLMJudgeEvaluator` 中引入时间锚点注入（`question_time`）与 **`UNDECIDABLE`（信息欠定拒判转人工复核，`needs_human_review=True`）** 机制。

---

## 1. 裁剪边界与非目标（Scope & Non-Goals）

- **已删除目录与文件**：
  - `src/memory_benchmark/config/`（全目录删除）
  - `src/memory_benchmark/prompts/`（全目录删除，Prompt 模板迁入 `configs/application.yaml`）
  - `src/memory_benchmark/metrics/`（全目录删除，纯函数内聚至 `evaluators/`）
  - `configs/llm.toml`（由 `configs/application.yaml` 替代）
  - `src/memory_benchmark/evaluators/` 下属 8 个冗余文件（`locomo_f1.py`、`locomo_judge.py`、`longmemeval_judge.py`、`halumem_qa.py`、`beam_rubric_judge.py`、`membench_choice_accuracy.py`、`answer_metrics.py`、`f1.py`）
- **核心新增/重构文件**：
  - `configs/application.yaml`：统一承载 `llm.answer`、`llm.judge` 与 `prompts.*` 多行模板数据
  - `src/memory_benchmark/core/config.py`：不到 150 行的 `${VAR:default}` 占位符解析器与 `bind_dataclass` 自动反射注入器
  - `src/memory_benchmark/evaluators/`（`__init__.py`、`exact_match.py`、`f1.py`、`llm_judge.py`）：统一提供 `ExactMatchEvaluator`（含选择题选项匹配）、`F1Evaluator`、`LLMJudgeEvaluator`（支持 `UNDECIDABLE` 人工复核标记）

---

## 2. 执行步骤 Checklist

- [x] **Step 1：创建 `configs/application.yaml` 与 `src/memory_benchmark/core/config.py` 自动反射配置引擎**
- [x] **Step 2：重构 `readers/answer.py` 与 3 个 Benchmark Adapter（移除 `prompts.benchmarks` 硬编码依赖）**
- [x] **Step 3：重构 `evaluators/`（统一 `ExactMatch` / `F1` / `LLMJudge` 并支持 `UNDECIDABLE` 拒判转人工）**
- [x] **Step 4：物理删除 `config/`、`prompts/`、`metrics/`、`configs/llm.toml` 及 8 个旧 Evaluator 文件**
- [x] **Step 5：编写配置反射注入、Prompt 数据分离与 `UNDECIDABLE` 裁判测试，跑通 `uv run pytest -q` 并同步 `STATE.md` / `AGENTS.md` / `README.md` / `docs/architecture.md` / `docs/decisions.md`**
