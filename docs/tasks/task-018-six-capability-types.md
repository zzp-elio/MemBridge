# Task-018: 11 类能力图谱收成 6 类评测类型

- **状态**：🟢 Completed
- **目标**：按已确认的题目聚合，把 `UnifiedCapability` 从 11 类改为 6 类，不能并进的原题不再贴上这 6 类标签。

## 6 类

事实回忆、多证据综合、时间与顺序、记忆更新、拒答、个性化。

## 不进入

LoCoMo 对抗题与开放域；BEAM 内部矛盾、指令遵循、长期总结；MemBench 再加工、带噪、推断偏好和情绪；HaluMem 错误前提纠正与新情境应用。

## Checklist

- [x] 收紧 `src/memory_benchmark/core/capabilities.py`
- [x] 更新映射测试
- [x] 同步 `docs/architecture.md` 与 `docs/decisions.md`
- [x] `uv run pytest -q`
