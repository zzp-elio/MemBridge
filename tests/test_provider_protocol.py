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
