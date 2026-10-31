# Task-022: 项目全量体检与潜在缺陷修复 (Full Project Audit & Defect Fixes)

- **状态**：🟢 Completed
- **目标**：
  1. 对当前跟踪的核心代码 `src/memory_benchmark` 与配置文件进行全量体检（静态检查、未定义变量、未处理边界、废弃警告）；
  2. 验证所有评测基准（LoCoMo, LongMemEval, MemBench, BEAM, HaluMem）的适配器加载与裁决；
  3. 检验 CLI 各种参数组合的边界容错性；
  4. 修复排查出的严重缺陷（如 MemBench 在限流截断时被 6 类过滤删空的崩溃 Bug）、废弃警告与异常退出机制；
  5. 跑通全量测试与契约验证。

## Checklist

- [x] 立项并挂载至 `STATE.md`
- [x] 维度 1：代码静态扫描与类型规范排查（AST 解析全部通过，无语法错误与漏导）
- [x] 维度 2：五大基准适配器加载与 6 类过滤逻辑全覆盖自测（发现并修复 MemBench 在 `--max-conversations 1` 下因前序未映射样本过早截断导致空数据集的严重崩溃 Bug）
- [x] 维度 3：CLI 与中间层边界异常处理排查（修复 `--confirm-api` 与 Fake/Real Client 的决策逻辑；支持 `KeyboardInterrupt` 优雅退出）
- [x] 维度 4：修复排查出的缺陷与警告（修复 Pydantic V2 `ConfigDict` 废弃警告；修复 MemBench 有效对话计数逻辑；补充测试回归门禁）
- [x] 维度 5：全量 `uv run pytest -q` 验收（27 passed in 11.84s, 0 warnings）与任务收口
