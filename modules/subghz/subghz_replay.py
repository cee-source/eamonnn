"""
Sub-GHz signal replay using CC1101.
"""
from __future__ import annotations

import logging
from typing import Optional

log = logging.getLogger(__name__)


class SubGHzReplay:
    def __init__(self, config) -> None:
        self._config = config
        self._cc = None

    def _get_cc(self):
        if self._cc is None:
            from modules.subghz.cc1101 import CC1101
            self._cc = CC1101(self._config)
            self._cc.open()
        return self._cc

    def replay(self, signal: dict, repeat: int = 3) -> bool:
        freq  = signal.get('frequency_mhz', self._config.getfloat('subghz', 'default_frequency', fallback=433.92))
        mod   = signal.get('modulation', self._config.get('subghz', 'default_modulation', fallback='ASK_OOK'))
        baud  = signal.get('baud', self._config.getint('subghz', 'default_baud', fallback=4800))
        pkts  = signal.get('packets', [])

        if not pkts:
            log.error('No packet data in signal')
            return False

        cc = self._get_cc()
        cc.configure(freq_mhz=freq, modulation=mod, baud=baud)

        success = True
        for _ in range(repeat):
            for pkt in pkts:
                ok = cc.transmit(bytes(pkt))
                if not ok:
                    success = False
        log.info('SubGHz replay: %d packets x%d at %.4f MHz', len(pkts), repeat, freq)
        return success

    def cleanup(self) -> None:
        if self._cc:
            self._cc.close()
