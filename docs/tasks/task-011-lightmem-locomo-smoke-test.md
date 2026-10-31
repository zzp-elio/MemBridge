# Task-011: LightMem 在 LoCoMo 上的极小粒度冒烟测试（1 会话 / 10 轮次 / 1 题目）

- **状态**：🟢 Completed (2026-10-14)
- **前置任务**：[`task-010-benchmark-task-prompts-and-safe-formatting.md`](task-010-benchmark-task-prompts-and-safe-formatting.md)
- **核心目标**：
  1. **支持超细粒度切片参数（Fine-Grained Slicing）**：
     - 在 [`src/memory_benchmark/__main__.py`](../../src/memory_benchmark/__main__.py) 的 `_slice_dataset` 与 CLI 解析器中扩充 `--max-sessions-per-conversation` 与 `--max-turns-per-session`，使评测中间层支持单会话内截取指定数量的 Session 与 Turn；
  2. **端到端微型联调（Micro Smoke Test）**：
     - 数据集选定 LoCoMo 第 1 个 Conversation 的 Session 0 前 10 条 Turn（Turn 0 ~ Turn 9，涵盖 2023-05-08 昨天参加 LGBTQ 支持小组的完整事实证据）；
     - 题目选定 Question 0（"When did Caroline go to the LGBTQ support group?"，标准答案 "7 May 2023"）；
  3. **C/S 架构联调跑通**：
     - 启动 LightMem Server（`third_party/methods/LightMem/docker/server.py`，配置真实 Embedding 与 Qdrant 索引）；
     - 评测端通过 `HttpMemoryProvider` 发起 `POST /ingest` 写入 10 条对话，发起 `POST /retrieve` 检索相关记忆；
     - `FrameworkAnswerReader` 调用 Answer LLM 生成预测答案，`LLMJudgeEvaluator` 执行结构化判定；
  4. **客观指标与产物验货**：
     - 验证产生完整的 `predictions.jsonl` 与 `evaluation_summary.json`；
     - 校验黑盒效率指标（`ingest_latency_ms`、`retrieve_latency_ms`、`retrieved_context_tokens`）。

---

## 1. 裁剪边界与非目标（Scope & Non-Goals）

- **必须遵守的红线**：
  - 本任务仅针对 1 对话、10 轮次、1 题目的微型冒烟，不发起全量大批量压测；
  - 维持中间层黑盒协议纯洁性，不修改 `MemoryProvider` 契约；
  - `STATE.md` 严格 $\le 30$ 行、`AGENTS.md` 严格 $\le 50$ 行。

---

## 2. 执行步骤 Checklist

- [x] **Step 1：在 `__main__.py` 中补齐 `--max-sessions-per-conversation` 与 `--max-turns-per-session` 参数与切片逻辑**
- [x] **Step 2：配置并后台启动 LightMem HTTP Server（端口 8002）**
- [x] **Step 3：执行端到端微型冒烟测试命令并记录执行日志**
- [x] **Step 4：核验产物文件、Answer 回答内容、Judge 打分结果与 3 大客观效率指标**
- [x] **Step 5：关闭临时 Server，更新 `STATE.md`、`task-011.md` 归档**
