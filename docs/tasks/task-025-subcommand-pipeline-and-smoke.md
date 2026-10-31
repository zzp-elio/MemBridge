# Task-025: 子命令流水线解耦、--smoke 极简封装与参数耦合消除

- **状态**：✅ Done
- **目标**：
  1. 解除参数耦合，将全流程拆分为直观的子命令架构：
     - `run`：一站式全流程（Ingest -> Query -> Eval）；
     - `ingest`：阶段一（仅写入记忆）；
     - `query`：阶段二（仅检索答题）；
     - `eval`：阶段三（仅离线打分，强绑定 `--metrics`）；
  2. 封装一键式 `--smoke` 参数，统一管理微抽样，隐藏底层的 `max-conversations` / `max-sessions` / `max-questions` 等容易配错的零碎参数；
  3. 彻底删除 `--server` / `--host` / `--port` 监听模式参数；
  4. 彻底取消 `top_k` 参数；
  5. 在回答中通透讲解 `-m mock` 的执行机理与 `--max-workers` 线程池与 Conversation 不匹配时的运行规律；
  6. 全量测试通过并更新文档。

## Checklist

- [x] 立项并挂载至 `STATE.md`
- [x] 重构 `src/memory_benchmark/__main__.py` 实现清晰的子命令架构（`run`, `ingest`, `query`, `eval`）与 `--smoke` 封装
- [x] 彻底移除 `--server` 及 `--top-k` 相关参数
- [x] 优化 `runners/prediction.py` 支持单独的 Ingest 阶段与 Query 阶段调度
- [x] 更新 `README.md` 与参数参考表
- [x] 运行 `uv run pytest -q` 确保所有用例全绿
- [x] 收口任务，更新 `STATE.md`
