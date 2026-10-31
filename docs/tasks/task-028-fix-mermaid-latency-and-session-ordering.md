# Task-028: 修复 Mermaid 渲染错误、明确客户端防作弊耗时度量与同会话顺序传递保证

- **状态**：✅ Done
- **目标**：
  1. 修复 `README.md` 中 Mermaid 流程图因连线标签未加引号引发的 GitHub 解析渲染乱码（Parse error on line 12）；
  2. 详述 `latency_ms` 的度量哲学：被测系统无需且不应自报耗时（防作弊），评测端始终使用客户端 `time.perf_counter()` 采集端到端 Wall-Clock 耗时，并在 Localhost/Docker 环回网络（RTT ~0.05ms）下保证绝对客观公正；
  3. 详述会话时序保证：评测端对同一个 `isolation_key` 下的 Session 严格保证同步顺序递交（In-Order Delivery），仅在跨 Conversation 间并发；
  4. 详述 `speaker` 的取值谱系（角色标识 vs 真实人名）与 `turn_time` / `session_time` 的分层降级消费策略。

## Checklist

- [x] 立项并挂载至 `STATE.md`
- [x] 修复 `README.md` 中的 Mermaid 语法错误
- [x] 在 `README.md` 中完善 `speaker`、`turn_time`、`latency_ms` 与 Session 顺序递交说明
- [x] 沉淀架构决策至 `docs/decisions.md` (ADR-024)
- [x] 运行 `uv run pytest -q` 确保所有用例全绿
- [x] 收口任务，更新 `STATE.md`
