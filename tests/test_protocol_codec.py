import pytest

from bss_direct_inject.protocol import (
    ACK,
    ESC,
    ETX,
    NAK,
    STX,
    DirectInjectCodec,
)


def test_encode_decode_roundtrip_with_special_bytes() -> None:
    body = bytes([0x88, STX, ETX, ACK, NAK, ESC, 0x42])
    frame = DirectInjectCodec.encode(body)
    assert frame[0] == STX
    assert frame[-1] == ETX
    assert DirectInjectCodec.decode(frame) == body


def test_decode_rejects_bad_checksum() -> None:
    body = bytes([0x88, 0x01, 0x02, 0x03])
    frame = DirectInjectCodec.encode(body)
    tampered = frame[:-2] + bytes([frame[-2] ^ 0xFF]) + frame[-1:]
    with pytest.raises(ValueError, match="Checksum"):
        DirectInjectCodec.decode(tampered)


def test_encode_escapes_checksum_when_needed() -> None:
    body = bytes([STX])
    frame = DirectInjectCodec.encode(body)
    assert frame == bytes([STX, ESC, STX + 0x80, ESC, STX + 0x80, ETX])


def test_decode_rejects_missing_framing() -> None:
    with pytest.raises(ValueError, match="STX"):
        DirectInjectCodec.decode(b"\x00\x01\x02")


def test_decode_rejects_short_frame() -> None:
    with pytest.raises(ValueError, match="short"):
        DirectInjectCodec.decode(bytes([STX, 0x88, ETX]))


def test_decode_rejects_escape_at_end() -> None:
    with pytest.raises(ValueError, match="Escape"):
        DirectInjectCodec.decode(bytes([STX, ESC, ETX]))
