"""MemBridge 最小记忆服务参考实现 (Minimal Memory Server Example)。

本脚本仅使用 Python 标准库（无需安装 FastAPI 或 Flask），完整实现 MemBridge 的
标准 C/S 接口协议（POST /ingest 与 POST /retrieve），可作为自研记忆系统的起步模板。

启动方式：
    python examples/memory_server.py [--port 8000]
"""

from __future__ import annotations

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class InMemoryStore:
    """基于内存字典的多会话隔离存储，线程安全。"""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.turns_by_key: dict[str, list[str]] = {}
        self.seen_idempotency_keys: set[str] = set()

    def ingest(self, isolation_key: str, turns: list[dict[str, Any]], idempotency_key: str | None) -> float:
        start = time.perf_counter()
        with self.lock:
            if idempotency_key and idempotency_key in self.seen_idempotency_keys:
                return (time.perf_counter() - start) * 1000.0
            bucket = self.turns_by_key.setdefault(isolation_key, [])
            for turn in turns:
                speaker = turn.get("speaker") or "speaker"
                content = turn.get("content") or ""
                bucket.append(f"{speaker}: {content}")
            if idempotency_key:
                self.seen_idempotency_keys.add(idempotency_key)
        return (time.perf_counter() - start) * 1000.0

    def retrieve(self, isolation_key: str, query: str) -> tuple[str, float]:
        start = time.perf_counter()
        with self.lock:
            stored = list(self.turns_by_key.get(isolation_key, []))
        # 参考实现采用朴素全部拼接；真实系统可在此接入向量检索、知识图谱或 LLM 提炼
        context = "\n".join(stored)
        return context, (time.perf_counter() - start) * 1000.0


STORE = InMemoryStore()


class MemoryServerHandler(BaseHTTPRequestHandler):
    """处理 MemBridge 标准接口协议的 HTTP Handler。"""

    def _send_json(self, status_code: int, data: dict[str, Any]) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in ("/", "/health"):
            self._send_json(200, {"code": 200, "message": "Memory Server Ready", "data": None})
        else:
            self._send_json(404, {"code": 404, "message": "Not Found", "data": None})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            self._send_json(400, {"code": 400, "message": "Invalid JSON body", "data": None})
            return

        if self.path == "/ingest":
            isolation_key = payload.get("isolation_key", "default")
            session = payload.get("session", {})
            turns = session.get("turns", [])
            idempotency_key = self.headers.get("Idempotency-Key") or payload.get("idempotency_key")

            latency_ms = STORE.ingest(isolation_key, turns, idempotency_key)
            print(f"[POST /ingest] key={isolation_key} turns={len(turns)} ({latency_ms:.2f}ms)")
            self._send_json(200, {
                "code": 200,
                "message": "ok",
                "data": None,
                "latency_ms": round(latency_ms, 3),
            })

        elif self.path == "/retrieve":
            isolation_key = payload.get("isolation_key", "default")
            query = payload.get("query", "")
            context, latency_ms = STORE.retrieve(isolation_key, query)
            print(f"[POST /retrieve] key={isolation_key} query={query[:30]!r} ({latency_ms:.2f}ms)")
            self._send_json(200, {
                "code": 200,
                "message": "ok",
                "data": {
                    "formatted_memory": context,
                },
                "latency_ms": round(latency_ms, 3),
            })
        else:
            self._send_json(404, {"code": 404, "message": f"Unknown endpoint {self.path}", "data": None})

    def log_message(self, format: str, *args: Any) -> None:
        # 静默默认请求日志，只打印我们在 do_POST 中显式输出的高亮日志
        pass


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), MemoryServerHandler)
    print("=" * 65)
    print(f"🚀 MemBridge 参考记忆服务已启动: http://{host}:{port}")
    print("   支持接口: POST /ingest, POST /retrieve, GET /health")
    print("   按 Ctrl+C 可随时停止服务")
    print("=" * 65)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止。")
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MemBridge Minimal Memory Server")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址 (默认 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="监听端口 (默认 8000)")
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)
