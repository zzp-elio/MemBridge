# Task-019: 五个基准都能读入，总分与 6 类使用同一题集

- **状态**：🟢 Completed
- **目标**：修好 HaluMem、BEAM 因 `Session` 缺少 `private_metadata` 而无法加载的问题。没有统一评测类型的题不进入评测题集。

## Checklist

- [x] `Session.private_metadata` 不进入 `to_dict()`
- [x] `BenchmarkAdapter.load()` 去掉无类型题和因此变空的对话
- [x] 调查文档标明 11 类合同已不是现行规则
- [x] README 按现行协议重写
- [x] `uv run pytest -q`
