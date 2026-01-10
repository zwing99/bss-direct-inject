from __future__ import annotations

import socket
import time
from dataclasses import dataclass

from .protocol import (
    ACK,
    ETX,
    NAK,
    STX,
    DirectInjectCodec,
    DiTarget,
    build_bump_sv_percent_body,
    build_param_preset_recall_body,
    build_set_string_sv_body,
    build_set_sv_body,
    build_set_sv_percent_body,
    build_subscribe_sv_body,
    build_subscribe_sv_percent_body,
    build_unsubscribe_sv_body,
    build_unsubscribe_sv_percent_body,
    build_venue_preset_recall_body,
)


class DirectInjectError(RuntimeError):
    pass


class DirectInjectNakError(DirectInjectError):
    pass


@dataclass
class DirectInjectClient:
    host: str
    port: int = 1023
    timeout: float = 1.0
    expect_ack: bool = False

    _socket: socket.socket | None = None

    def connect(self) -> None:
        if self._socket is not None:
            return
        sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        sock.settimeout(self.timeout)
        self._socket = sock

    def close(self) -> None:
        if self._socket is None:
            return
        self._socket.close()
        self._socket = None

    def __enter__(self) -> DirectInjectClient:
        self.connect()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def send_body(self, body: bytes, expect_ack: bool | None = None) -> bool:
        if expect_ack is None:
            expect_ack = self.expect_ack
        sock = self._require_socket()
        frame = DirectInjectCodec.encode(body)
        sock.sendall(frame)
        if not expect_ack:
            return True
        return self._read_ack()

    def set_sv(self, target: DiTarget, data: int) -> bool:
        return self.send_body(build_set_sv_body(target, data))

    def subscribe_sv(self, target: DiTarget, rate_ms: int) -> bool:
        return self.send_body(build_subscribe_sv_body(target, rate_ms))

    def unsubscribe_sv(self, target: DiTarget) -> bool:
        return self.send_body(build_unsubscribe_sv_body(target))

    def set_sv_percent(self, target: DiTarget, percent_scaled: int) -> bool:
        return self.send_body(build_set_sv_percent_body(target, percent_scaled))

    def subscribe_sv_percent(self, target: DiTarget, rate_ms: int) -> bool:
        return self.send_body(build_subscribe_sv_percent_body(target, rate_ms))

    def unsubscribe_sv_percent(self, target: DiTarget) -> bool:
        return self.send_body(build_unsubscribe_sv_percent_body(target))

    def bump_sv_percent(self, target: DiTarget, percent_scaled_delta: int) -> bool:
        return self.send_body(build_bump_sv_percent_body(target, percent_scaled_delta))

    def venue_preset_recall(self, preset_number: int) -> bool:
        return self.send_body(build_venue_preset_recall_body(preset_number))

    def param_preset_recall(self, preset_number: int) -> bool:
        return self.send_body(build_param_preset_recall_body(preset_number))

    def set_string_sv(self, target: DiTarget, value: str) -> bool:
        return self.send_body(build_set_string_sv_body(target, value))

    def read_body(self) -> bytes:
        sock = self._require_socket()
        frame = self._read_frame(sock)
        return DirectInjectCodec.decode(frame)

    def _require_socket(self) -> socket.socket:
        if self._socket is None:
            msg = "Client is not connected."
            raise DirectInjectError(msg)
        return self._socket

    def _read_ack(self) -> bool:
        sock = self._require_socket()
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            data = sock.recv(1)
            if not data:
                continue
            byte = data[0]
            if byte == ACK:
                return True
            if byte == NAK:
                msg = "Device returned NAK."
                raise DirectInjectNakError(msg)
            if byte == STX:
                frame = self._read_frame(sock, prefix=data)
                _ = DirectInjectCodec.decode(frame)
        msg = "Timed out waiting for ACK/NAK."
        raise DirectInjectError(msg)

    def _read_frame(self, sock: socket.socket, prefix: bytes = b"") -> bytes:
        buffer = bytearray(prefix)
        while True:
            if buffer and buffer[0] != STX:
                buffer.pop(0)
                continue
            chunk = sock.recv(1)
            if not chunk:
                continue
            buffer.extend(chunk)
            if buffer[-1] == ETX:
                return bytes(buffer)
