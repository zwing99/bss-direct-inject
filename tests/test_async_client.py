import asyncio

import pytest

from bss_direct_inject.async_client import (
    AsyncDirectInjectClient,
    AsyncDirectInjectNakError,
)
from bss_direct_inject.protocol import ACK, NAK, DirectInjectCodec, DiTarget


async def _run_server(handler):
    server = await asyncio.start_server(handler, "127.0.0.1", 0)
    host, port = server.sockets[0].getsockname()[:2]
    return server, host, port


async def _read_frame(reader: asyncio.StreamReader) -> bytes:
    buffer = bytearray()
    while True:
        byte = await reader.readexactly(1)
        buffer.extend(byte)
        if byte == b"\x03":
            return bytes(buffer)


@pytest.mark.asyncio
async def test_send_body_ack() -> None:
    target = DiTarget(
        node=0x0001, virtual_device=0x03, object_id=0x000100, state_variable=0x0000
    )

    async def handler(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        frame = await _read_frame(reader)
        _ = DirectInjectCodec.decode(frame)
        writer.write(bytes([ACK]))
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    server, host, port = await _run_server(handler)
    async with server:
        async with AsyncDirectInjectClient(host, port=port) as client:
            assert await client.set_sv(target, data=0) is True


@pytest.mark.asyncio
async def test_send_body_nak() -> None:
    async def handler(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        _ = await _read_frame(reader)
        writer.write(bytes([NAK]))
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    server, host, port = await _run_server(handler)
    async with server:
        async with AsyncDirectInjectClient(host, port=port) as client:
            with pytest.raises(AsyncDirectInjectNakError):
                await client.send_body(b"\x88\x00")


@pytest.mark.asyncio
async def test_read_body() -> None:
    body = b"\x88\x01\x02"
    frame = DirectInjectCodec.encode(body)

    async def handler(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        writer.write(frame)
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    server, host, port = await _run_server(handler)
    async with server:
        async with AsyncDirectInjectClient(host, port=port) as client:
            assert await client.read_body() == body
