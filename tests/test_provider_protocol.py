"""核心协议契约测试 (`MemoryProvider` & `Result[T]`)。

验证：
1. 仿 Spring Boot 的泛型 `Result[T]` 成功 (`code=200`) 与失败 (`code != 200`) 契约；
2. `IngestRequest` 以 `Session`（内含 `turns: list[Turn]`）为粒度并强制拦截私有评分键泄漏；
3. `RetrieveRequest` 与 `RetrievePayload(formatted_memory)` 契约；
4. `MemoryProvider` 抽象接口仅包含 `ingest` 与 `retrieve` 两个方法；
5. `HttpMemoryProvider` 通过标准 JSON 请求/响应完成远程调用与错误处理。
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from memory_benchmark.core import (
    DataLeakageError,
    HttpMemoryProvider,
    IngestRequest,
    MemoryProvider,
    MockMemoryProvider,
    Result,
    RetrievePayload,
    RetrieveRequest,
    Session,
    Turn,
)


def _sample_session() -> Session:
    return Session(
        session_id="sess-1",
        session_time="2026-05-01T10:00:00",
        turns=[
            Turn(
                turn_id="t1",
                speaker="Alice",
                content="I moved to Seattle last month.",
                normalized_role="user",
            ),
            Turn(
                turn_id="t2",
                speaker="Assistant",
                content="Got it! How do you like Seattle?",
                normalized_role="assistant",
            ),
        ],
    )


def test_result_envelope_ok_and_fail_contracts() -> None:
    """验证泛型 Result[T] 的成功与异常状态封装（对齐 Spring Boot Result<T>）。"""
    ok_res = Result.ok(RetrievePayload(formatted_memory="Alice lives in Seattle."), latency_ms=12.5)
    assert ok_res.code == 200
    assert ok_res.is_success is True
    assert ok_res.data == RetrievePayload(formatted_memory="Alice lives in Seattle.")
    assert ok_res.latency_ms == 12.5
    assert ok_res.to_dict() == {
        "code": 200,
        "message": "ok",
        "data": {"formatted_memory": "Alice lives in Seattle."},
        "latency_ms": 12.5,
    }

    fail_res: Result[RetrievePayload] = Result.fail(code=504, message="Gateway Timeout", latency_ms=60000.0)
    assert fail_res.code == 504
    assert fail_res.is_success is False
    assert fail_res.data is None


def test_memory_provider_has_only_ingest_and_retrieve_methods() -> None:
    """验证中间层接口 MemoryProvider 仅暴露 ingest 与 retrieve 两个抽象方法。"""
    abstract_methods = set(getattr(MemoryProvider, "__abstractmethods__", set()))
    assert abstract_methods == {"ingest", "retrieve"}

    public_methods = [
        name
        for name, _ in inspect.getmembers(MemoryProvider, predicate=inspect.isfunction)
        if not name.startswith("_")
    ]
    assert sorted(public_methods) == ["ingest", "retrieve"]


def test_ingest_and_retrieve_requests_reject_private_keys() -> None:
    """验证 IngestRequest 与 RetrieveRequest 严禁携带 gold_answer 等私有标签。"""
    session = _sample_session()
    req = IngestRequest(isolation_key="run1_conv1", session=session)
    assert req.session_id == "sess-1"
    assert len(req.turns) == 2

    with pytest.raises(DataLeakageError):
        IngestRequest(
            isolation_key="run1_conv1",
            session=session,
            metadata={"gold_answer": "Seattle"},
        )

    with pytest.raises(DataLeakageError):
        RetrieveRequest(
            isolation_key="run1_conv1",
            query="Where does Alice live?",
            metadata={"evidence": ["t1"]},
        )


def test_mock_memory_provider_round_trip() -> None:
    """验证 MockMemoryProvider 按 isolation_key 隔离存储 Session 并检索 formatted_memory。"""
    provider = MockMemoryProvider()
    ingest_res = provider.ingest(
        IngestRequest(isolation_key="iso-A", session=_sample_session())
    )
    assert ingest_res.code == 200
    assert ingest_res.is_success

    ret_res = provider.retrieve(
        RetrieveRequest(isolation_key="iso-A", query="Where did Alice move?")
    )
    assert ret_res.code == 200
    assert ret_res.data is not None
    assert "Seattle" in ret_res.data.formatted_memory

    other_res = provider.retrieve(
        RetrieveRequest(isolation_key="iso-B", query="Where did Alice move?")
    )
    assert other_res.code == 200
    assert other_res.data is not None
    assert "Seattle" not in other_res.data.formatted_memory


def test_http_memory_provider_transport_and_error_handling() -> None:
    """验证 HttpMemoryProvider 发送标准 POST /ingest 与 /retrieve 请求并解析 Result[T]。"""
    captured_calls: list[tuple[str, dict[str, Any], float | None]] = []

    def fake_transport(
        url: str, payload: dict[str, Any], timeout: float | None
    ) -> dict[str, Any]:
        captured_calls.append((url, payload, timeout))
        if url.endswith("/ingest"):
            return {"code": 200, "message": "ok", "data": None, "latency_ms": 150.0}
        return {
            "code": 200,
            "message": "ok",
            "data": {"formatted_memory": "Server memory: Alice moved to Seattle."},
            "latency_ms": 42.0,
        }

    client = HttpMemoryProvider(
        base_url="http://localhost:9000",
        timeout_seconds=1800.0,
        transport=fake_transport,
    )
    in_res = client.ingest(IngestRequest(isolation_key="iso-1", session=_sample_session()))
    assert in_res.code == 200
    assert in_res.latency_ms == 150.0
    assert captured_calls[0][0] == "http://localhost:9000/ingest"
    assert captured_calls[0][1]["isolation_key"] == "iso-1"
    assert len(captured_calls[0][1]["session"]["turns"]) == 2
    assert captured_calls[0][2] == 1800.0

    ret_res = client.retrieve(
        RetrieveRequest(isolation_key="iso-1", query="Where does Alice live?")
    )
    assert ret_res.code == 200
    assert ret_res.data is not None
    assert ret_res.data.formatted_memory == "Server memory: Alice moved to Seattle."
    assert ret_res.latency_ms == 42.0


def test_default_urllib_transport_override_false_code_200_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """验证 HTTP 状态码为 500 时，即使 JSON body 含有 code: 200，也坚决返回 500 失败。"""
    import io
    import urllib.error
    from memory_benchmark.core.provider_protocol import _default_urllib_transport

    def fake_urlopen(req: Any, timeout: float | None = None) -> Any:
        # 模拟外部服务抛出 HTTP 500，但 body 里是个假 200
        fp = io.BytesIO(b'{"code": 200, "message": "misreported ok", "data": null}')
        raise urllib.error.HTTPError(
            url="http://memory.local/ingest",
            code=500,
            msg="Internal Server Error",
            hdrs={},  # type: ignore[arg-type]
            fp=fp,
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    res = _default_urllib_transport("http://memory.local/ingest", {"isolation_key": "k"}, timeout_seconds=5.0)
    assert res["code"] == 500
    assert "code" in res


def test_default_urllib_transport_retries_on_429(monkeypatch: pytest.MonkeyPatch) -> None:
    """验证当远端返回 429 限流时，transport 会进行指数退避重试。"""
    import io
    import urllib.error
    from memory_benchmark.core.provider_protocol import _default_urllib_transport

    attempts = 0

    def fake_urlopen(req: Any, timeout: float | None = None) -> Any:
        nonlocal attempts
        attempts += 1
        fp = io.BytesIO(b'{"code": 429, "message": "rate limited"}')
        raise urllib.error.HTTPError(
            url="http://memory.local/ingest",
            code=429,
            msg="Too Many Requests",
            hdrs={},  # type: ignore[arg-type]
            fp=fp,
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("time.sleep", lambda s: None)  # 加快测试
    res = _default_urllib_transport("http://memory.local/ingest", {"isolation_key": "k"}, timeout_seconds=5.0, max_retries=3)
    assert attempts == 3
    assert res["code"] == 429


def test_examples_minimal_memory_server_real_http_socket_roundtrip() -> None:
    """验证 examples/memory_server.py 能够作为真实的 HTTP 记忆服务响应 Ingest 与 Retrieve。"""
    import threading
    from http.server import ThreadingHTTPServer
    import sys
    from pathlib import Path
    
    # 动态导入 examples/memory_server.py
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
    try:
        import memory_server
        server = ThreadingHTTPServer(("127.0.0.1", 0), memory_server.MemoryServerHandler)
        port = server.server_port
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        client = HttpMemoryProvider(base_url=f"http://127.0.0.1:{port}", timeout_seconds=5.0)

        # 1. Ingest
        sess = Session(
            session_id="s1",
            turns=[
                Turn(turn_id="t1", speaker="User", content="My favorite color is green."),
                Turn(turn_id="t2", speaker="Assistant", content="Green is a calming color."),
            ],
        )
        ingest_res = client.ingest(
            IngestRequest(
                isolation_key="user-test-key",
                session=sess,
                idempotency_key="user-test-key:s1",
            )
        )
        assert ingest_res.code == 200
        assert ingest_res.is_success
        assert ingest_res.latency_ms is not None

        # 2. Retrieve
        ret_res = client.retrieve(
            RetrieveRequest(
                isolation_key="user-test-key",
                query="What color do I like?",
            )
        )
        assert ret_res.code == 200
        assert ret_res.is_success
        assert ret_res.data is not None
        assert "My favorite color is green." in ret_res.data.formatted_memory
        assert ret_res.latency_ms is not None
    finally:
        server.shutdown()
        server.server_close()
        sys.path.pop(0)
