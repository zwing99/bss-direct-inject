## bss-direct-inject

Helpers for the Soundweb London Direct Inject (DI) protocol, focused on BLU devices like the BLU-100.

## Quick start

```python
import asyncio

from bss_direct_inject import AsyncDirectInjectClient, DiTarget

target = DiTarget(
    node=0x0000,
    virtual_device=0x03,
    object_id=0x000100,
    state_variable=0x0000,
)

async def main() -> None:
    async with AsyncDirectInjectClient("192.168.1.50") as client:
        await client.set_sv(target, data=0)


asyncio.run(main())
```

Synchronous usage is also available via `DirectInjectClient`.

## Protocol notes

- TCP DI messaging uses port `1023` on Soundweb London devices.
- Message framing is `STX` + body + checksum + `ETX`, with escaping for special bytes.
- Checksums are XOR of the body bytes before escaping.
- `node` is the 16-bit HiQnet node address. Use `0` when directly connected to the target device.
- `virtual_device` is typically `0x03` for audio processing objects.
- `object_id` is a 24-bit object address (from the full HiQnet address in London Architect).
- `state_variable` is a 16-bit SV identifier.
- Percent-based SV values use fixed-point scaling: `percent * 65536`.

## Development

Use `just` for common tasks (via `uv run`):

```sh
just fmt
just lint
just typecheck
```
