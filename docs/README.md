# 文档导航 (`docs/`)

本项目遵循极简、按需的工程文档原则：日常开发状态与任务进度统一在根目录 [`STATE.md`](../STATE.md) 维护，全局规范见根目录 [`AGENTS.md`](../AGENTS.md)。

| 路径 | 内容说明 | 何时查阅 |
| :--- | :--- | :--- |
| [`architecture.md`](architecture.md) | 核心评测 4 步主线、数据模型、目录分层与 `MemoryProvider` v3 协议 | 了解系统骨架、修改核心流程或新增模块时 |
| [`decisions.md`](decisions.md) | 核心架构决策记录（ADR：为什么这么做）与历次实战踩坑防呆清单 | 怀疑某个现有设计不合理、准备重构或编写测试时 |
| [`survey/`](survey/README.md) | 5 个 Benchmark（LoCoMo / LongMemEval / HaluMem / BEAM / MemBench）的数据结构、官方评测流程与 QA 任务聚合规则 | 核对数据集字段、评测指标或撰写论文实验章节时 |
| [`reference/integration/`](reference/integration/) | 10 个被测 Memory 方法的底层机制卡与产品接口契约 | 修改特定 Method Adapter 或查阅方法实现细节时 |
| [`reference/`](reference/) | 补充技术参考（TOML 配置与 Builder 政策、API Runtime Profile、数据集异常账等） | 调整运行配置、模型槽位或排查数据特征时 |
