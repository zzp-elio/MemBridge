# Task-027: 彻底废除公开 Mock 模式、补充接口实体规范与服务端并发处理体系

- **状态**：✅ Done
- **目标**：
  1. 彻底从公开 CLI 与 `README.md` 中删除 `mock` 模式，评测端 100% 收敛为面向外部 HTTP Memory Server 的纯粹客户端：
     - `--server-url` 成为核心连接参数（默认 `http://127.0.0.1:8002`）；
     - `--method` 默认设为 `http` 并从公开帮助中隐藏（仅保留内部测试兼容）；
  2. 在 `README.md` 中详尽说明 `POST /ingest` 与 `POST /retrieve` 两个核心接口的实体结构与 JSON Schema（`IngestRequest`、`Session`、`Turn`、`RetrieveRequest`、`Result[T]`、`RetrievePayload`）；
  3. 深入阐述多线程并发评测对 Memory Server 的硬性要求与处理机制（会话隔离 `isolation_key`、连接池排空、异步/多进程架构、GPU/API 限流）；
  4. 保持代码与文档契约防漂移，全量测试通过并提交推送。

## Checklist

- [x] 立项并挂载至 `STATE.md`
- [x] 修改 `src/memory_benchmark/__main__.py`：`--method` 默认 `http` 且 suppress，`--server-url` 默认 `http://127.0.0.1:8002`
- [x] 更新 `README.md`：
  - [x] 彻底移除 `mock` 相关描述；
  - [x] 增加两接口核心实体结构与 JSON 请求/响应体范例；
  - [x] 增加服务端并发要求与处理指南（并发安全性、`isolation_key` 分区、连接池）；
- [x] 更新 `docs/decisions.md` (ADR-023) 与 `docs/architecture.md`
- [x] 运行 `uv run pytest -q` 确保所有用例全绿
- [x] 收口任务，更新 `STATE.md`
