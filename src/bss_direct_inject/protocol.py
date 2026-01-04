from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import IntEnum

STX = 0x02
ETX = 0x03
ACK = 0x06
NAK = 0x15
ESC = 0x1B

SPECIAL_BYTES = {STX, ETX, ACK, NAK, ESC}


class DiCommand(IntEnum):
    SET_SV = 0x88
    SUBSCRIBE_SV = 0x89
    UNSUBSCRIBE_SV = 0x8A
    VENUE_PRESET_RECALL = 0x8B
    PARAM_PRESET_RECALL = 0x8C
    SET_SV_PERCENT = 0x8D
    SUBSCRIBE_SV_PERCENT = 0x8E
    UNSUBSCRIBE_SV_PERCENT = 0x8F
    BUMP_SV_PERCENT = 0x90
    SET_STRING_SV = 0x91


@dataclass(frozen=True)
class DiTarget:
    node: int
    virtual_device: int
    object_id: int
    state_variable: int

    def to_bytes(self) -> bytes:
        return (
            _pack_u16(self.node)
            + _pack_u8(self.virtual_device)
            + _pack_u24(self.object_id)
            + _pack_u16(self.state_variable)
        )


class DirectInjectCodec:
    @staticmethod
    def encode(body: bytes) -> bytes:
        checksum = _checksum(body)
        escaped_body = _escape_bytes(body)
        escaped_checksum = _escape_bytes(bytes([checksum]))
        return bytes([STX]) + escaped_body + escaped_checksum + bytes([ETX])

    @staticmethod
    def decode(frame: bytes) -> bytes:
        if not frame or frame[0] != STX or frame[-1] != ETX:
            msg = "Frame must start with STX and end with ETX."
            raise ValueError(msg)
        unescaped = _unescape_bytes(frame[1:-1])
        if len(unescaped) < 2:
            msg = "Frame is too short to contain a checksum."
            raise ValueError(msg)
        body, checksum = unescaped[:-1], unescaped[-1]
        if _checksum(body) != checksum:
            msg = "Checksum does not match message body."
            raise ValueError(msg)
        return body


def build_set_sv_body(target: DiTarget, data: int) -> bytes:
    return bytes([DiCommand.SET_SV]) + target.to_bytes() + _pack_i32(data)


def build_subscribe_sv_body(target: DiTarget, rate_ms: int) -> bytes:
    return bytes([DiCommand.SUBSCRIBE_SV]) + target.to_bytes() + _pack_u32(rate_ms)


def build_unsubscribe_sv_body(target: DiTarget) -> bytes:
    return bytes([DiCommand.UNSUBSCRIBE_SV]) + target.to_bytes() + _pack_u32(0)


def build_set_sv_percent_body(target: DiTarget, percent_scaled: int) -> bytes:
    return (
        bytes([DiCommand.SET_SV_PERCENT])
        + target.to_bytes()
        + _pack_i32(percent_scaled)
    )


def build_subscribe_sv_percent_body(target: DiTarget, rate_ms: int) -> bytes:
    return (
        bytes([DiCommand.SUBSCRIBE_SV_PERCENT]) + target.to_bytes() + _pack_u32(rate_ms)
    )


def build_unsubscribe_sv_percent_body(target: DiTarget) -> bytes:
    return bytes([DiCommand.UNSUBSCRIBE_SV_PERCENT]) + target.to_bytes() + _pack_u32(0)


def build_bump_sv_percent_body(target: DiTarget, percent_scaled_delta: int) -> bytes:
    return (
        bytes([DiCommand.BUMP_SV_PERCENT])
        + target.to_bytes()
        + _pack_i32(percent_scaled_delta)
    )


def build_venue_preset_recall_body(preset_number: int) -> bytes:
    return bytes([DiCommand.VENUE_PRESET_RECALL]) + _pack_u32(preset_number)


def build_param_preset_recall_body(preset_number: int) -> bytes:
    return bytes([DiCommand.PARAM_PRESET_RECALL]) + _pack_u32(preset_number)


def build_set_string_sv_body(target: DiTarget, value: str) -> bytes:
    encoded = value.encode("ascii", errors="strict")
    if len(encoded) > 32:
        msg = "String SV values must be 32 ASCII characters or fewer."
        raise ValueError(msg)
    length = len(encoded) + 1
    data = _pack_u16(length) + encoded + b"\x00"
    return bytes([DiCommand.SET_STRING_SV]) + target.to_bytes() + data


def _escape_bytes(data: bytes) -> bytes:
    escaped = bytearray()
    for byte in data:
        if byte in SPECIAL_BYTES:
            escaped.append(ESC)
            escaped.append(byte + 0x80)
        else:
            escaped.append(byte)
    return bytes(escaped)


def _unescape_bytes(data: bytes) -> bytes:
    unescaped = bytearray()
    i = 0
    while i < len(data):
        byte = data[i]
        if byte == ESC:
            if i + 1 >= len(data):
                msg = "Escape byte at end of frame."
                raise ValueError(msg)
            unescaped.append(data[i + 1] - 0x80)
            i += 2
        else:
            unescaped.append(byte)
            i += 1
    return bytes(unescaped)


def _checksum(data: Iterable[int]) -> int:
    value = 0
    for byte in data:
        value ^= byte
    return value & 0xFF


def _pack_u8(value: int) -> bytes:
    if not 0 <= value <= 0xFF:
        msg = "Value must fit in an unsigned 8-bit field."
        raise ValueError(msg)
    return value.to_bytes(1, byteorder="big", signed=False)


def _pack_u16(value: int) -> bytes:
    if not 0 <= value <= 0xFFFF:
        msg = "Value must fit in an unsigned 16-bit field."
        raise ValueError(msg)
    return value.to_bytes(2, byteorder="big", signed=False)


def _pack_u24(value: int) -> bytes:
    if not 0 <= value <= 0xFFFFFF:
        msg = "Value must fit in an unsigned 24-bit field."
        raise ValueError(msg)
    return value.to_bytes(3, byteorder="big", signed=False)


def _pack_u32(value: int) -> bytes:
    if not 0 <= value <= 0xFFFFFFFF:
        msg = "Value must fit in an unsigned 32-bit field."
        raise ValueError(msg)
    return value.to_bytes(4, byteorder="big", signed=False)


def _pack_i32(value: int) -> bytes:
    if not -(2**31) <= value <= 2**31 - 1:
        msg = "Value must fit in a signed 32-bit field."
        raise ValueError(msg)
    return value.to_bytes(4, byteorder="big", signed=True)
