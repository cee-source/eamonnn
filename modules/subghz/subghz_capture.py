"""
Sub-GHz signal capture using CC1101.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

log = logging.getLogger(__name__)


class SubGHzCapture:
    def __init__(self, config) -> None:
        self._config = config
        self._cc = None

    def _get_cc(self):
        if self._cc is None:
            from modules.subghz.cc1101 import CC1101
            self._cc = CC1101(self._config)
            self._cc.open()
        return self._cc

    def capture(self,
                freq_mhz: Optional[float] = None,
                modulation: Optional[str] = None,
                baud: Optional[int] = None,
                duration_s: float = 3.0,
                name: str = '') -> Optional[dict]:
        freq = freq_mhz or self._config.getfloat('subghz', 'default_frequency', fallback=433.92)
        mod  = modulation or self._config.get('subghz', 'default_modulation', fallback='ASK_OOK')
        rate = baud or self._config.getint('subghz', 'default_baud', fallback=4800)

        cc = self._get_cc()
        cc.configure(freq_mhz=freq, modulation=mod, baud=rate)

        log.info('SubGHz capture: %.4f MHz %s %d baud for %.1fs', freq, mod, rate, duration_s)
        packets = cc.raw_capture(duration_s=duration_s)

        if not packets:
            log.info('No packets received')
            return None

        result = {
            'name': name,
            'frequency_mhz': freq,
            'modulation': mod,
            'baud': rate,
            'packet_count': len(packets),
            'packets': [list(p) for p in packets],
        }
        return result

    def cleanup(self) -> None:
        if self._cc:
            self._cc.close()
