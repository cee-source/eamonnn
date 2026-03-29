"""
RFID reader/writer using MFRC522 (RC522) over SPI.
Supports Mifare Classic 1K card read, write, and full dump.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

log = logging.getLogger(__name__)

MIFARE_CLASSIC_1K_SECTORS = 16
MIFARE_CLASSIC_1K_BLOCKS = 64
DEFAULT_KEY = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]


class HardwareNotAvailableError(Exception):
    pass


class RFIDReader:
    def __init__(self, config, display=None) -> None:
        self._config = config
        self._display = display
        self._reader = None
        self._init_hardware()

    def _init_hardware(self) -> None:
        try:
            from mfrc522 import SimpleMFRC522
            self._reader = SimpleMFRC522()
            log.info('MFRC522 RFID reader initialised')
        except Exception as e:
            log.warning('MFRC522 not available: %s', e)
            self._reader = None

    def _require_hardware(self) -> None:
        if self._reader is None:
            raise HardwareNotAvailableError(
                'MFRC522 not found. Check SPI wiring and spidev.'
            )

    def scan_card(self, timeout_s: float = 10.0) -> Optional[dict]:
        self._require_hardware()
        log.info('Waiting for RFID card (timeout=%.1fs)...', timeout_s)
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                uid, text = self._reader.read_no_block()
                if uid:
                    result = {
                        'uid': uid,
                        'uid_hex': hex(uid),
                        'text': text.strip() if text else '',
                        'type': 'MIFARE_CLASSIC',
                    }
                    log.info('Card detected: UID=%s', result['uid_hex'])
                    return result
            except Exception as e:
                log.debug('Scan error: %s', e)
            time.sleep(0.1)
        log.info('Card scan timed out')
        return None

    def read_text(self, timeout_s: float = 10.0) -> Optional[str]:
        self._require_hardware()
        log.info('Reading text from card...')
        try:
            _, text = self._reader.read()
            return text.strip() if text else ''
        except Exception as e:
            log.error('Read error: %s', e)
            return None

    def write_text(self, text: str, timeout_s: float = 10.0) -> bool:
        self._require_hardware()
        log.info('Writing text to card: %r', text)
        try:
            self._reader.write(text)
            log.info('Write successful')
            return True
        except Exception as e:
            log.error('Write error: %s', e)
            return False

    def dump_card(self, timeout_s: float = 15.0) -> Optional[dict]:
        """Full sector dump using low-level MFRC522 access."""
        self._require_hardware()
        try:
            from mfrc522 import MFRC522
        except ImportError:
            raise HardwareNotAvailableError('mfrc522 library required for dump')

        rdr = MFRC522()
        log.info('Waiting for card to dump...')
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            status, tag_type = rdr.MFRC522_Request(rdr.PICC_REQIDL)
            if status != rdr.MI_OK:
                time.sleep(0.1)
                continue

            status, uid = rdr.MFRC522_Anticoll()
            if status != rdr.MI_OK:
                time.sleep(0.1)
                continue

            rdr.MFRC522_SelectTag(uid)
            sectors = {}

            for block in range(MIFARE_CLASSIC_1K_BLOCKS):
                sector = block // 4
                if sector not in sectors:
                    status = rdr.MFRC522_Auth(
                        rdr.PICC_AUTHENT1A, block, DEFAULT_KEY, uid
                    )
                    if status != rdr.MI_OK:
                        sectors[sector] = {'error': 'auth_failed'}
                        continue

                data = rdr.MFRC522_Read(block)
                if data:
                    if sector not in sectors or 'error' in sectors.get(sector, {}):
                        sectors[sector] = {'blocks': {}}
                    sectors[sector]['blocks'][block] = [hex(b) for b in data]

            rdr.MFRC522_StopCrypto1()
            dump = {
                'uid': uid,
                'uid_hex': ''.join(f'{b:02X}' for b in uid),
                'sectors': sectors,
            }
            log.info('Card dump complete: UID=%s', dump['uid_hex'])
            return dump

        log.info('Dump timed out waiting for card')
        return None

    def scan_and_display(self) -> None:
        if self._display:
            self._display.draw_message(['Scan Card', 'Hold card near reader...'])
        card = self.scan_card()
        if card:
            saved = self._config.save_capture('rfid', card, prefix=f'uid_{card["uid_hex"][2:]}')
            lines = [
                'Card Found!',
                f'UID: {card["uid_hex"]}',
                f'Type: {card["type"]}',
                f'Text: {card["text"][:20]}' if card["text"] else 'No text data',
                '',
                f'Saved: {saved.split("/")[-1]}',
            ]
        else:
            lines = ['No card detected', 'Timed out after 10s']

        if self._display:
            self._display.draw_message(lines)
            time.sleep(3)
        else:
            print('\n'.join(lines))

    def list_saved(self) -> None:
        captures = self._config.load_captures('rfid')
        if not captures:
            lines = ['No saved cards']
        else:
            lines = [f'Saved cards ({len(captures)}):'] + [
                c['filename'][:30] for c in captures
            ]
        if self._display:
            self._display.draw_message(lines)
            time.sleep(3)
        else:
            print('\n'.join(lines))
