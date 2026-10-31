# Task-023: CLI 命令行参数精细化分组与 README 完整参数表呈现

- **状态**：🟢 Completed
- **目标**：
  1. 重构 `src/memory_benchmark/__main__.py` 中的 CLI 参数解析器，采用 `add_argument_group()` 进行清晰的功能分层（数据与基准、被测服务连接、评测指标与 LLM、并发与执行、Coordinator 模式）；
  2. 补充标准短选项（如 `-b / --benchmark`, `-m / --method`, `-u / --server-url`, `-k / --top-k`, `-w / --max-workers`）与简洁别名（`--max-questions`）；
  3. 隐藏已过时的 `--confirm-api` 等过渡参数；
  4. 在 `README.md` 中明确阐述“不加 `--max-conversations` 默认全量评测”，并以专业 GitHub 开源标准展示详尽完整的参数表格；
  5. 跑通全量测试与契约验证。

## Checklist

- [x] 立项并挂载至 `STATE.md`
- [x] 优化 `src/memory_benchmark/__main__.py` 参数分组、短选项与说明
- [x] 在 `README.md` 中撰写结构化完整 CLI 参数表与默认值说明
- [x] 验证 `uv run memory-benchmark --help` 输出与各参数实际运行
- [x] 跑通 `uv run pytest -q` 确保无任何回归与文档链接失效
- [x] 收口任务，更新 `STATE.md`
