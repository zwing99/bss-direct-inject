from __future__ import annotations

import asyncio
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


class AsyncDirectInjectError(RuntimeError):
    pass


class AsyncDirectInjectNakError(AsyncDirectInjectError):
    pass


@dataclass
class AsyncDirectInjectClient:
    host: str
    port: int = 1023
    timeout: float = 1.0
    expect_ack: bool = False

    _reader: asyncio.StreamReader | None = None
    _writer: asyncio.StreamWriter | None = None

    async def connect(self) -> None:
        if self._reader is not None or self._writer is not None:
            return
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port),
            timeout=self.timeout,
        )
        self._reader = reader
        self._writer = writer

    async def close(self) -> None:
        if self._writer is None:
            return
        self._writer.close()
        await self._writer.wait_closed()
        self._reader = None
        self._writer = None

    async def __aenter__(self) -> AsyncDirectInjectClient:
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await self.close()

    async def send_body(self, body: bytes, expect_ack: bool | None = None) -> bool:
        if expect_ack is None:
            expect_ack = self.expect_ack
        writer = self._require_writer()
        frame = DirectInjectCodec.encode(body)
        writer.write(frame)
        await writer.drain()
        if not expect_ack:
            return True
        return await self._read_ack()

    async def set_sv(self, target: DiTarget, data: int) -> bool:
        return await self.send_body(build_set_sv_body(target, data))

    async def subscribe_sv(self, target: DiTarget, rate_ms: int) -> bool:
        return await self.send_body(build_subscribe_sv_body(target, rate_ms))

    async def unsubscribe_sv(self, target: DiTarget) -> bool:
        return await self.send_body(build_unsubscribe_sv_body(target))

    async def set_sv_percent(self, target: DiTarget, percent_scaled: int) -> bool:
        return await self.send_body(build_set_sv_percent_body(target, percent_scaled))

    async def subscribe_sv_percent(self, target: DiTarget, rate_ms: int) -> bool:
        return await self.send_body(build_subscribe_sv_percent_body(target, rate_ms))

    async def unsubscribe_sv_percent(self, target: DiTarget) -> bool:
        return await self.send_body(build_unsubscribe_sv_percent_body(target))

    async def bump_sv_percent(
        self, target: DiTarget, percent_scaled_delta: int
    ) -> bool:
        return await self.send_body(
            build_bump_sv_percent_body(target, percent_scaled_delta)
        )

    async def venue_preset_recall(self, preset_number: int) -> bool:
        return await self.send_body(build_venue_preset_recall_body(preset_number))

    async def param_preset_recall(self, preset_number: int) -> bool:
        return await self.send_body(build_param_preset_recall_body(preset_number))

    async def set_string_sv(self, target: DiTarget, value: str) -> bool:
        return await self.send_body(build_set_string_sv_body(target, value))

    async def read_body(self) -> bytes:
        reader = self._require_reader()
        frame = await self._read_frame(reader)
        return DirectInjectCodec.decode(frame)

    def _require_reader(self) -> asyncio.StreamReader:
        if self._reader is None:
            msg = "Client is not connected."
            raise AsyncDirectInjectError(msg)
        return self._reader

    def _require_writer(self) -> asyncio.StreamWriter:
        if self._writer is None:
            msg = "Client is not connected."
            raise AsyncDirectInjectError(msg)
        return self._writer

    async def _read_ack(self) -> bool:
        reader = self._require_reader()
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            remaining = max(0.0, deadline - time.monotonic())
            try:
                data = await asyncio.wait_for(reader.readexactly(1), timeout=remaining)
            except TimeoutError:
                break
            byte = data[0]
            if byte == ACK:
                return True
            if byte == NAK:
                msg = "Device returned NAK."
                raise AsyncDirectInjectNakError(msg)
            if byte == STX:
                frame = await self._read_frame(reader, prefix=data)
                _ = DirectInjectCodec.decode(frame)
        msg = "Timed out waiting for ACK/NAK."
        raise AsyncDirectInjectError(msg)

    async def _read_frame(
        self, reader: asyncio.StreamReader, prefix: bytes = b""
    ) -> bytes:
        buffer = bytearray(prefix)
        while True:
            if buffer and buffer[0] != STX:
                buffer.pop(0)
                continue
            chunk = await reader.readexactly(1)
            buffer.extend(chunk)
            if buffer[-1] == ETX:
                return bytes(buffer)
