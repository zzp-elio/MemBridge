# Task-020: 通用 LLM 环境变量，Git 只跟踪评测端

- **状态**：🟢 Completed
- **目标**：答题和裁判改为读取 `API_KEY`、`BASE_URL`、`MODEL_NAME`。依赖只保留评测代码用到的包。Git 只跟踪 `src/`、`configs/`、`README.md`、`.env.example`、`pyproject.toml`、`uv.lock`、`.gitignore`。

## Checklist

- [x] `configs/application.yaml` 与报错信息
- [x] 本地 `.env` 与 `.env.example`
- [x] LightMem 服务端改为优先读这三个变量
- [x] 去掉未使用的 `requests`，显式加入 `pydantic`
- [x] `.gitignore` 白名单
- [x] `uv run pytest -q`
