# Task-008: LightMem 记忆系统容器化（Docker）与标准化 C/S HTTP 服务包装

- **状态**：✅ Completed (2026-10-13)
- **前置任务**：[`task-007-coordinator-and-ioc-ready-service.md`](task-007-coordinator-and-ioc-ready-service.md)
- **核心目标**：
  1. **构建 LightMem 标准 C/S HTTP 服务端 (`server.py`)**：在 `third_party/methods/LightMem/docker/` 中实现独立 HTTP 服务，对接 `LightMemory` 底层能力，暴露符合中间层协议的 `POST /ingest`（`Session` 写入）与 `POST /retrieve`（记忆检索），并统一遵循 `Result[T]` 响应；
  2. **支持容器启动时自动 `/ready` 握手**：容器启动预热就绪后，支持主动向评测 Coordinator 发送 `POST /ready` 心跳，实现全自动跨容器双向闭环；
  3. **编写轻量化 `Dockerfile` 与 `docker-compose.yml`**：构建基于 Python 3.11 的独立容器镜像，支持挂载环境变量（`OPENAI_API_KEY`、`PORT` 等），隔离底层依赖；
  4. **全流程联调与自动化验证**：跑通真实 LightMem 服务的单测/集成测试，验证 `CoordinatorServer` 接收到容器心跳后全自动完成端到端评测流水线。

---

## 1. 裁剪边界与非目标（Scope & Non-Goals）

- **必须遵守的红线**：
  - 评测框架主工程（`src/memory_benchmark/`）绝不直接 `import lightmem`，双方物理隔离，仅通过 HTTP 网络协议通信；
  - LightMem 容器内部自行管理底层 Qdrant 索引与 `isolation_key` 存储命名空间，评测端不侵入其内部实现；
  - 必须支持无外部大模型凭据时的 Mock/Fallback 测试模式，确保 CI 与无卡环境均可秒级跑通。

---

## 2. 执行步骤 Checklist

- [x] **Step 1：编写 LightMem C/S HTTP 服务适配器 (`third_party/methods/LightMem/docker/server.py`)**
- [x] **Step 2：编写 `Dockerfile` 与 `docker-compose.yml` 容器编排配置**
- [x] **Step 3：编写真实 HTTP 联调测试（测试容器/本地服务对接 `HttpMemoryProvider` 与 Coordinator `/ready`）**
- [x] **Step 4：验证 `uv run pytest -q` 全绿，并同步 `STATE.md` / `docs/architecture.md` / `docs/decisions.md` (ADR-011)**
