# Task-007: 评测协调器服务（Coordinator Server）与 /ready 双向就绪握手契约

- **状态**：✅ Completed (2026-10-13)
- **前置任务**：[`task-006-unified-11-capabilities-and-breakdown.md`](task-006-unified-11-capabilities-and-breakdown.md)
- **核心目标**：
  1. **双向就绪心跳服务 (`CoordinatorServer`)**：基于 Python 标准库 `ThreadingHTTPServer` 构建轻量 HTTP 协调器服务，暴露 `POST /ready`、`GET /status`、`GET /tasks` 等标准接口；
  2. **仿 Spring IoC 容器与单例无状态 Bean 注入 (`CoordinatorContext`)**：常驻预初始化好的 `AppConfig`、`FrameworkAnswerReader`、`AnswerEvaluator` 等单例 Bean，请求到来时仅流转纯不可变 DTO，无状态复用；
  3. **异步评测任务调度队列 (`EvaluationTaskQueue`)**：收到被测记忆服务的 `/ready` 握手请求后，立即返回成功应答并将评测作业派发至后台工作线程，全自动执行 Ingest -> Retrieve -> Answer -> Evaluate 流程；
  4. **端到端契约测试与防漂移同步**：编写多服务并发 `/ready` 注册与执行自动化测试，跑通 `uv run pytest -q`，并在 [`docs/architecture.md`](../architecture.md) 与 [`docs/decisions.md`](../decisions.md) 沉淀 `ADR-010`。

---

## 1. 裁剪边界与非目标（Scope & Non-Goals）

- **必须遵守的红线**：
  - 严禁引入 FastAPI / Flask / Celery 等重型依赖，使用 Python 标准库 `http.server` 保持零供应链负担；
  - 协调器对外响应必须严格遵循 `Result[T](code, message, data, latency_ms)` 统一信封格式；
  - 被测记忆系统的内部生命周期与源码严禁侵入，评测协调器仅通过其上报的 `endpoint` 发起标准的 `MemoryProvider.ingest` 与 `retrieve` 请求。

---

## 2. 执行步骤 Checklist

- [x] **Step 1：设计协调器数据载荷与实体 (`ReadyRequest`, `TaskStatus`, `EvaluationTaskInfo`)**
- [x] **Step 2：构建仿 Spring IoC 的无状态单例容器 (`CoordinatorContext`) 与后台任务执行器**
- [x] **Step 3：实现基于 `ThreadingHTTPServer` 的轻量级 `CoordinatorServer`（支持 `/ready`, `/status`, `/tasks`）**
- [x] **Step 4：在 CLI / `__main__.py` 中集成 `--server` 启动模式**
- [x] **Step 5：编写多线程 `/ready` 端到端集成测试，验证 `uv run pytest -q` 全绿并同步 `STATE.md` / `docs/architecture.md` / `docs/decisions.md` (ADR-010)**
