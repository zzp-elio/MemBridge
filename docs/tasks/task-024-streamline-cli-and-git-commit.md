# Task-024: 极致精简 CLI 参数与开源门面收口 (Streamline CLI & Push)

- **状态**：🟢 Completed
- **目标**：
  1. 彻底从公共 CLI 和文档中移除 `--top-k` 参数（固定为内部默认 10，无需外部用户关心）；
  2. 隐藏内部实验专用/高认知负荷的参数（`--skip-ingest`, `--reuse-ingest-run-id`, `--confirm-api`），让公共 CLI 参数极度聚焦在核心直观选项；
  3. 重构 `README.md` 参数参考表，打造顶级开源门面标准；
  4. 运行全量测试验证（27 passed, 0 warnings）；
  5. 规范完成 Git Commit 与 Git Push。

## Checklist

- [x] 立项并挂载至 `STATE.md`
- [x] 在 `src/memory_benchmark/__main__.py` 中移除 `--top-k`，隐藏内部调试参数
- [x] 在 `README.md` 中同步精简参数表与用例
- [x] 运行 `uv run pytest -q` 确保测试全绿
- [x] 执行 `git add`、`git commit` 与 `git push`
- [x] 收口任务，更新 `STATE.md`
