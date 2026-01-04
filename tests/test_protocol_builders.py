import pytest

from bss_direct_inject.protocol import (
    DiCommand,
    DiTarget,
    build_bump_sv_percent_body,
    build_param_preset_recall_body,
    build_set_string_sv_body,
    build_set_sv_body,
    build_set_sv_percent_body,
    build_subscribe_sv_body,
    build_unsubscribe_sv_body,
    build_venue_preset_recall_body,
)


def test_target_bytes_are_big_endian() -> None:
    target = DiTarget(
        node=0x1234, virtual_device=0x03, object_id=0x00ABCD, state_variable=0x0F0E
    )
    assert target.to_bytes() == bytes([0x12, 0x34, 0x03, 0x00, 0xAB, 0xCD, 0x0F, 0x0E])


def test_set_sv_body_layout() -> None:
    target = DiTarget(
        node=0x0001, virtual_device=0x03, object_id=0x000100, state_variable=0x0000
    )
    body = build_set_sv_body(target, data=0)
    assert body[0] == DiCommand.SET_SV
    assert len(body) == 1 + 8 + 4


def test_subscribe_bodies_have_rate_or_zero() -> None:
    target = DiTarget(
        node=0x0001, virtual_device=0x03, object_id=0x000100, state_variable=0x0000
    )
    subscribe = build_subscribe_sv_body(target, rate_ms=50)
    unsubscribe = build_unsubscribe_sv_body(target)
    assert subscribe[0] == DiCommand.SUBSCRIBE_SV
    assert unsubscribe[0] == DiCommand.UNSUBSCRIBE_SV
    assert subscribe[-4:] == bytes([0x00, 0x00, 0x00, 0x32])
    assert unsubscribe[-4:] == bytes([0x00, 0x00, 0x00, 0x00])


def test_percent_commands_share_payload_size() -> None:
    target = DiTarget(
        node=0x0002, virtual_device=0x03, object_id=0x000101, state_variable=0x0001
    )
    set_percent = build_set_sv_percent_body(target, percent_scaled=65536)
    bump_percent = build_bump_sv_percent_body(target, percent_scaled_delta=-65536)
    assert len(set_percent) == len(bump_percent) == 1 + 8 + 4


def test_preset_recall_payloads() -> None:
    venue = build_venue_preset_recall_body(3)
    param = build_param_preset_recall_body(7)
    assert venue[0] == DiCommand.VENUE_PRESET_RECALL
    assert param[0] == DiCommand.PARAM_PRESET_RECALL
    assert venue[-1] == 0x03
    assert param[-1] == 0x07


def test_string_sv_body_includes_length_and_null() -> None:
    target = DiTarget(
        node=0x0001, virtual_device=0x03, object_id=0x000100, state_variable=0x0002
    )
    body = build_set_string_sv_body(target, "Soundweb")
    assert body[0] == DiCommand.SET_STRING_SV
    assert body[-1] == 0x00
    assert body[1 + 8 : 1 + 10] == bytes([0x00, 0x09])


def test_string_sv_rejects_non_ascii() -> None:
    target = DiTarget(
        node=0x0001, virtual_device=0x03, object_id=0x000100, state_variable=0x0002
    )
    with pytest.raises(UnicodeEncodeError):
        build_set_string_sv_body(target, "café")


def test_string_sv_rejects_overlong_value() -> None:
    target = DiTarget(
        node=0x0001, virtual_device=0x03, object_id=0x000100, state_variable=0x0002
    )
    with pytest.raises(ValueError, match="32"):
        build_set_string_sv_body(target, "a" * 33)


def test_target_byte_ranges_validate_on_encode() -> None:
    with pytest.raises(ValueError, match="16-bit"):
        DiTarget(
            node=0x1_0000,
            virtual_device=0x03,
            object_id=0x000100,
            state_variable=0x0002,
        ).to_bytes()
    with pytest.raises(ValueError, match="8-bit"):
        DiTarget(
            node=0x0001, virtual_device=0x1FF, object_id=0x000100, state_variable=0x0002
        ).to_bytes()
    with pytest.raises(ValueError, match="24-bit"):
        DiTarget(
            node=0x0001,
            virtual_device=0x03,
            object_id=0x1_000000,
            state_variable=0x0002,
        ).to_bytes()
    with pytest.raises(ValueError, match="16-bit"):
        DiTarget(
            node=0x0001,
            virtual_device=0x03,
            object_id=0x000100,
            state_variable=0x1_0000,
        ).to_bytes()


def test_set_sv_rejects_out_of_range_data() -> None:
    target = DiTarget(
        node=0x0001, virtual_device=0x03, object_id=0x000100, state_variable=0x0002
    )
    with pytest.raises(ValueError, match="32-bit"):
        build_set_sv_body(target, data=2**31)
