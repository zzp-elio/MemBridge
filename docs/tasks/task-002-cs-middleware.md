# Task-002：升级为极简 C/S 双方法评测中间层与 `Result[T]` 协议

> **状态**：已完成 (Completed)
> **关联决策**：[`ADR-003`](../decisions.md)、[`ADR-004`](../decisions.md)、[`ADR-005`](../decisions.md)、[`ADR-006`](../decisions.md)

---

## 1. 任务背景与边界

我们将 `AgentMemoryBench` 纯化为专注于评测侧的 **“标准化评测中间层（Evaluation Middleware）”**：
- 被测记忆系统（Method）作为外部独立服务（HTTP Server / Docker 容器）运行并自行管理内部配置与存储隔离；适配中间层是 Method 侧的职责，不在 Bench 仓库内硬包第三方源码；
- 中间层抽象接口 `MemoryProvider` 仅保留 **`ingest`**（按 `Session` 写入）和 **`retrieve`**（按问题检索并返回 `formatted_memory`）两个方法，显式传入 `isolation_key`；
- 响应格式统一采用仿 Spring Boot 的泛型 **`Result[T](code, message, data, latency_ms)`** 信封；
- 框架侧仅控制 `answer_llm` 与 `judge_llm` 两个大模型的配置，黑盒效率指标仅统计：`ingest_latency_ms`（记忆构建耗时）、`retrieve_latency_ms`（记忆检索耗时）、`retrieved_context_tokens`（检索上下文 Token 长度）。

---

## 2. 执行步骤清单 (Checklist)

- [x] **Step 1：重构核心协议 [`src/memory_benchmark/core/provider_protocol.py`](../../src/memory_benchmark/core/provider_protocol.py)**
  - 定义泛型 `Result[T]`（`code: int = 200`、`message: str = "ok"`、`data: T | None = None`、`latency_ms: float = 0.0`）；
  - 定义纯业务请求与载荷：`IngestRequest(isolation_key, session)`、`RetrieveRequest(isolation_key, query, question_time, top_k)`、`RetrievePayload(formatted_memory)`；
  - 将 `MemoryProvider` 精简为仅含 `ingest(request) -> Result[None]` 与 `retrieve(request) -> Result[RetrievePayload]` 两个抽象方法，删除其余 4 个钩子与四粒度联合类型。
- [x] **Step 2：清理 `src/memory_benchmark/methods/`，纯化为 HTTP 客户端 + Mock 参考实现**
  - 删除 14 个在本地进程内硬包第三方源码的旧文件（`*_adapter.py`、`*_worker.py`、`custom_loader.py`、`third_party_warning_filters.py`）；
  - 新增 [`src/memory_benchmark/methods/http_client.py`](../../src/memory_benchmark/methods/http_client.py)（`HttpMemoryProvider`，支持配置 `base_url` 与长超时 `timeout_seconds=1800.0`，通过 `POST /ingest` 和 `POST /retrieve` 调用远程 Method 服务并解析 `Result[T]`）；
  - 更新 [`src/memory_benchmark/methods/mock.py`](../../src/memory_benchmark/methods/mock.py) 与 [`src/memory_benchmark/methods/__init__.py`](../../src/memory_benchmark/methods/__init__.py)。
- [x] **Step 3：清理 `configs/` 与 `src/memory_benchmark/config/`，仅保留 `answer_llm` 与 `judge_llm`**
  - 删除 `configs/methods/`、`configs/pricing/`、`configs/execution/`、`configs/runtime/`、`configs/evaluators/` 以及 `prompts/author/`；
  - 新建单一配置文件 [`configs/llm.toml`](../../configs/llm.toml)（仅含 `[answer_llm]` 与 `[judge_llm]`）；
  - 删除 `src/memory_benchmark/config/profiles.py` 与 `run_profiles.py`，精简 `config/__init__.py`。
- [x] **Step 4：删除 `runners/event_stream.py`，重构 [`src/memory_benchmark/runners/prediction.py`](../../src/memory_benchmark/runners/prediction.py)**
  - 删除四粒度聚合器 `event_stream.py`；
  - `prediction.py` 直接按 `conversation.sessions` 逐个 Session 调用 `provider.ingest(IngestRequest(isolation_key, session))` 并校验 `result.code == 200`；
  - 采集并落盘三大黑盒效率指标：`ingest_latency_ms`、`retrieve_latency_ms`、`retrieved_context_tokens`。
- [x] **Step 5：同步更新 `tests/` 黑盒契约测试并验证全绿**
  - 删除 `tests/test_event_stream.py`；
  - 更新 `tests/test_provider_protocol.py` 与 `tests/test_end_to_end_pipeline.py`；
  - 全仓 72 个子模块导入零报错，14 项核心契约测试全部通过。
