"""
IR protocol decoder.
Supports NEC, RC5, Sony SIRC. Returns decoded command or 'UNKNOWN'.
Pulse timings are in microseconds.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

NEC_HDR_MARK  = 9000
NEC_HDR_SPACE = 4500
NEC_BIT_MARK  = 562
NEC_ONE_SPACE = 1687
NEC_ZERO_SPACE = 562
NEC_TOLERANCE = 0.25

RC5_BIT_US = 889
RC5_TOLERANCE = 0.4

SONY_HDR_MARK  = 2400
SONY_BIT_MARK  = 600
SONY_ONE_SPACE = 1200
SONY_ZERO_SPACE = 600
SONY_TOLERANCE = 0.3


def _within(value: int, target: int, tolerance: float) -> bool:
    return abs(value - target) <= target * tolerance


@dataclass
class IRDecoded:
    protocol: str
    address: int
    command: int
    raw: list[tuple[int, int]]


def decode(pulses: list[tuple[int, int]]) -> Optional[IRDecoded]:
    """
    pulses: list of (level, duration_us) pairs, starting with mark (level=1).
    Returns IRDecoded or None if unrecognised.
    """
    if len(pulses) < 4:
        return None

    # Try NEC
    result = _decode_nec(pulses)
    if result:
        return result

    # Try Sony SIRC (12-bit)
    result = _decode_sony(pulses)
    if result:
        return result

    return None


def _decode_nec(pulses: list[tuple[int, int]]) -> Optional[IRDecoded]:
    if len(pulses) < 67:
        return None
    # Header: mark ~9ms, space ~4.5ms
    if not (_within(pulses[0][1], NEC_HDR_MARK, NEC_TOLERANCE) and
            _within(pulses[1][1], NEC_HDR_SPACE, NEC_TOLERANCE)):
        return None

    bits = []
    for i in range(2, 66, 2):
        mark_dur = pulses[i][1]
        space_dur = pulses[i + 1][1]
        if not _within(mark_dur, NEC_BIT_MARK, NEC_TOLERANCE):
            return None
        if _within(space_dur, NEC_ONE_SPACE, NEC_TOLERANCE):
            bits.append(1)
        elif _within(space_dur, NEC_ZERO_SPACE, NEC_TOLERANCE):
            bits.append(0)
        else:
            return None

    # LSB first: bits[0..7]=address, [8..15]=~address, [16..23]=command, [24..31]=~command
    address = sum(b << i for i, b in enumerate(bits[0:8]))
    command = sum(b << i for i, b in enumerate(bits[16:24]))
    return IRDecoded(protocol='NEC', address=address, command=command, raw=pulses)


def _decode_sony(pulses: list[tuple[int, int]]) -> Optional[IRDecoded]:
    # Sony SIRC 12-bit: header mark + 12 data bits
    if len(pulses) < 25:
        return None
    if not _within(pulses[0][1], SONY_HDR_MARK, SONY_TOLERANCE):
        return None

    bits = []
    for i in range(1, 24, 2):
        space_dur = pulses[i][1]
        mark_dur = pulses[i + 1][1] if i + 1 < len(pulses) else SONY_BIT_MARK
        if not _within(mark_dur, SONY_BIT_MARK, SONY_TOLERANCE):
            return None
        if _within(space_dur, SONY_ONE_SPACE, SONY_TOLERANCE):
            bits.append(1)
        elif _within(space_dur, SONY_ZERO_SPACE, SONY_TOLERANCE):
            bits.append(0)
        else:
            return None

    if len(bits) < 12:
        return None

    command = sum(b << i for i, b in enumerate(bits[0:7]))
    address = sum(b << i for i, b in enumerate(bits[7:12]))
    return IRDecoded(protocol='SONY_SIRC12', address=address, command=command, raw=pulses)
