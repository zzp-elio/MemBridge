# Task-033: 架构全景图英文版制作与双语文档对齐

- **状态**：✅ Completed
- **目标**：
  1. 为英文版 [`README.md`](../../README.md) 制作对应的高清 16:9 全英文学术架构全景图（`assets/architecture_en.png`）；
  2. 严格遵循【暖色手账/白板手绘风】规范（米白细网格纸质底、深炭手绘墨水线、奶黄便签、暖橙强调、薄荷绿状态标）；
  3. 将图内所有模块、三层架构、协议端点（`POST /ingest`、`POST /retrieve`、`formatted_memory`）及 5 大基准标签转换为地道英文；
  4. 将图片保存为 `assets/architecture_en.png`，更新英文 [`README.md`](../../README.md) 的图片引用为 `assets/architecture_en.png`，中文 [`README_zh.md`](../../README_zh.md) 保持引用 `assets/architecture.png`；
  5. 运行 `uv run pytest -q` 确保文档防漂移测试全绿；
  6. Git commit 并推送至 GitHub 远程仓库。

## Checklist

- [x] 立项并在 [`STATE.md`](../../STATE.md) 挂载任务卡
- [x] 调用 `image-generator` 生成 16:9 暖色手账风全英文系统架构全景图
- [x] 校验图片质量与英文文本拼写，保存为 `assets/architecture_en.png`
- [x] 更新 `README.md` 引用为 `assets/architecture_en.png`
- [x] 运行 `uv run pytest -q` 确保所有契约测试全绿（验证图片路径有效性）
- [x] 沉淀架构记录至 [`docs/decisions.md`](../decisions.md) (ADR-029)
- [x] 更新 [`STATE.md`](../../STATE.md) 与本任务卡状态为 Completed
- [ ] 执行 Git commit 与 push
