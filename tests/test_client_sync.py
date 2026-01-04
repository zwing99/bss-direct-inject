import socket
from typing import cast

import pytest

from bss_direct_inject.client import (
    DirectInjectClient,
    DirectInjectError,
    DirectInjectNakError,
)
from bss_direct_inject.protocol import ACK, DirectInjectCodec


class FakeSocket:
    def __init__(self, data: bytes) -> None:
        self._buffer = bytearray(data)

    def recv(self, size: int) -> bytes:
        if not self._buffer:
            return b""
        chunk = self._buffer[:size]
        del self._buffer[:size]
        return bytes(chunk)

    def sendall(self, data: bytes) -> None:
        self.sent = data

    def settimeout(self, timeout: float) -> None:
        self.timeout = timeout

    def close(self) -> None:
        self.closed = True


def test_read_ack_success() -> None:
    client = DirectInjectClient("127.0.0.1")
    client._socket = FakeSocket(bytes([ACK]))  # type: ignore[assignment]
    assert client._read_ack() is True


def test_read_ack_handles_nak() -> None:
    client = DirectInjectClient("127.0.0.1")
    client._socket = FakeSocket(bytes([0x15]))  # type: ignore[assignment]
    with pytest.raises(DirectInjectNakError):
        client._read_ack()


def test_read_ack_skips_frame_then_reads_ack() -> None:
    client = DirectInjectClient("127.0.0.1")
    body = b"\x88\x00"
    frame = DirectInjectCodec.encode(body)
    data = frame + bytes([ACK])
    client._socket = FakeSocket(data)  # type: ignore[assignment]
    assert client._read_ack() is True


def test_read_frame_requires_stx() -> None:
    client = DirectInjectClient("127.0.0.1")
    body = b"\x88\x01"
    frame = DirectInjectCodec.encode(body)
    junked = b"\x00\x01" + frame
    sock = FakeSocket(junked)
    assert client._read_frame(cast(socket.socket, sock)) == frame


def test_send_body_requires_connection() -> None:
    client = DirectInjectClient("127.0.0.1")
    with pytest.raises(DirectInjectError):
        client.send_body(b"\x88\x00", expect_ack=False)


def test_send_body_writes_frame_without_ack() -> None:
    client = DirectInjectClient("127.0.0.1")
    sock = FakeSocket(b"")
    client._socket = sock  # type: ignore[assignment]
    assert client.send_body(b"\x88\x00", expect_ack=False) is True
    assert sock.sent.startswith(bytes([0x02]))


def test_read_body_decodes_frame() -> None:
    client = DirectInjectClient("127.0.0.1")
    body = b"\x88\x00"
    frame = DirectInjectCodec.encode(body)
    client._socket = FakeSocket(frame)  # type: ignore[assignment]
    assert client.read_body() == body
