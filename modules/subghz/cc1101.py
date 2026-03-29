"""
CC1101 Sub-GHz transceiver driver.
Full SPI register-level driver — no external Python library required.
Supports ASK/OOK, 2-FSK, GFSK, MSK modulation.
Frequency range: 300–348 MHz, 387–464 MHz, 779–928 MHz.

Reference: CC1101 datasheet SWRS061I (Texas Instruments)
"""
from __future__ import annotations

import logging
import math
import struct
import time
from typing import Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Register map (selected registers from CC1101 datasheet Table 45)
# ---------------------------------------------------------------------------
REG_IOCFG2   = 0x00
REG_IOCFG1   = 0x01
REG_IOCFG0   = 0x02
REG_FIFOTHR  = 0x03
REG_SYNC1    = 0x04
REG_SYNC0    = 0x05
REG_PKTLEN   = 0x06
REG_PKTCTRL1 = 0x07
REG_PKTCTRL0 = 0x08
REG_ADDR     = 0x09
REG_CHANNR   = 0x0A
REG_FSCTRL1  = 0x0B
REG_FSCTRL0  = 0x0C
REG_FREQ2    = 0x0D
REG_FREQ1    = 0x0E
REG_FREQ0    = 0x0F
REG_MDMCFG4  = 0x10
REG_MDMCFG3  = 0x11
REG_MDMCFG2  = 0x12
REG_MDMCFG1  = 0x13
REG_MDMCFG0  = 0x14
REG_DEVIATN  = 0x15
REG_MCSM2    = 0x16
REG_MCSM1    = 0x17
REG_MCSM0    = 0x18
REG_FOCCFG   = 0x19
REG_BSCFG    = 0x1A
REG_AGCCTRL2 = 0x1B
REG_AGCCTRL1 = 0x1C
REG_AGCCTRL0 = 0x1D
REG_WOREVT1  = 0x1E
REG_WOREVT0  = 0x1F
REG_WORCTRL  = 0x20
REG_FREND1   = 0x21
REG_FREND0   = 0x22
REG_FSCAL3   = 0x23
REG_FSCAL2   = 0x24
REG_FSCAL1   = 0x25
REG_FSCAL0   = 0x26
REG_RCCTRL1  = 0x27
REG_RCCTRL0  = 0x28
REG_FSTEST   = 0x29
REG_TEST2    = 0x2C
REG_TEST1    = 0x2D
REG_TEST0    = 0x2E

# Status registers (read with burst bit set)
REG_PARTNUM     = 0x30
REG_VERSION     = 0x31
REG_FREQEST     = 0x32
REG_LQI         = 0x33
REG_RSSI        = 0x34
REG_MARCSTATE   = 0x35
REG_TXBYTES     = 0x3A
REG_RXBYTES     = 0x3B

# FIFO
REG_TXFIFO      = 0x3F
REG_RXFIFO      = 0x3F

# Strobe commands
SRES   = 0x30   # Reset
SFSTXON = 0x31  # Enable freq synth, cal
SXOFF  = 0x32   # Power down
SCAL   = 0x33   # Cal freq synth
SRX    = 0x34   # Enable RX
STX    = 0x35   # Enable TX
SIDLE  = 0x36   # Idle state
SWOR   = 0x38   # Wake on radio
SPWD   = 0x39   # Power down
SFRX   = 0x3A   # Flush RX FIFO
SFTX   = 0x3B   # Flush TX FIFO
SNOP   = 0x3D   # No operation

# SPI access flags
READ_SINGLE  = 0x80
READ_BURST   = 0xC0
WRITE_BURST  = 0x40

XOSC_FREQ = 26_000_000   # 26 MHz crystal

# Modulation modes (MDMCFG2[4:3])
MOD_2FSK  = 0x00
MOD_GFSK  = 0x01
MOD_ASK   = 0x03   # ASK/OOK
MOD_4FSK  = 0x04
MOD_MSK   = 0x07

MODULATION_MAP = {
    '2FSK':    MOD_2FSK,
    'GFSK':    MOD_GFSK,
    'ASK_OOK': MOD_ASK,
    '4FSK':    MOD_4FSK,
    'MSK':     MOD_MSK,
}


class CC1101:
    def __init__(self, config) -> None:
        self._bus = config.getint('hardware', 'spi_bus', fallback=0)
        self._ce = config.getint('hardware', 'cc1101_ce_pin', fallback=7)
        self._spi = None
        self._ce_index = 1 if self._ce == 7 else 0  # CE0=GPIO8, CE1=GPIO7

    def open(self) -> None:
        import spidev
        self._spi = spidev.SpiDev()
        self._spi.open(self._bus, self._ce_index)
        self._spi.max_speed_hz = 6_000_000
        self._spi.mode = 0
        self.reset()
        self._verify_chip()
        log.info('CC1101 opened on SPI%d CE%d', self._bus, self._ce_index)

    def close(self) -> None:
        if self._spi:
            self.strobe(SIDLE)
            self._spi.close()
            self._spi = None

    # -----------------------------------------------------------------------
    # Low-level SPI access
    # -----------------------------------------------------------------------

    def _write_reg(self, addr: int, value: int) -> None:
        self._spi.xfer2([addr & 0x3F, value & 0xFF])

    def _write_burst(self, addr: int, data: list[int]) -> None:
        self._spi.xfer2([addr | WRITE_BURST] + list(data))

    def _read_reg(self, addr: int) -> int:
        result = self._spi.xfer2([addr | READ_SINGLE, 0x00])
        return result[1]

    def _read_burst(self, addr: int, length: int) -> list[int]:
        cmd = [addr | READ_BURST] + [0x00] * length
        return self._spi.xfer2(cmd)[1:]

    def _read_status(self, addr: int) -> int:
        result = self._spi.xfer2([addr | READ_BURST, 0x00])
        return result[1]

    def strobe(self, cmd: int) -> int:
        result = self._spi.xfer2([cmd])
        return result[0]

    # -----------------------------------------------------------------------
    # Chip management
    # -----------------------------------------------------------------------

    def reset(self) -> None:
        self.strobe(SRES)
        time.sleep(0.01)
        log.debug('CC1101 reset')

    def _verify_chip(self) -> None:
        partnum = self._read_status(REG_PARTNUM)
        version = self._read_status(REG_VERSION)
        if partnum != 0x00:
            raise RuntimeError(f'CC1101 not found (PARTNUM=0x{partnum:02X}, expected 0x00)')
        log.info('CC1101 verified: PARTNUM=0x%02X VERSION=0x%02X', partnum, version)

    def get_rssi_dbm(self) -> float:
        raw = self._read_status(REG_RSSI)
        if raw >= 128:
            return (raw - 256) / 2.0 - 74
        return raw / 2.0 - 74

    # -----------------------------------------------------------------------
    # Configuration
    # -----------------------------------------------------------------------

    def set_frequency(self, mhz: float) -> None:
        freq_word = int(mhz * 1e6 * (1 << 16) / XOSC_FREQ)
        self._write_reg(REG_FREQ2, (freq_word >> 16) & 0xFF)
        self._write_reg(REG_FREQ1, (freq_word >> 8) & 0xFF)
        self._write_reg(REG_FREQ0, freq_word & 0xFF)
        log.debug('CC1101 frequency set to %.4f MHz (word=0x%06X)', mhz, freq_word)

    def set_modulation(self, mod: str) -> None:
        mod_val = MODULATION_MAP.get(mod.upper())
        if mod_val is None:
            raise ValueError(f'Unknown modulation: {mod}. Options: {list(MODULATION_MAP)}')
        current = self._read_reg(REG_MDMCFG2)
        new_val = (current & 0xE7) | ((mod_val & 0x07) << 3)  # bits [5:4] wait, [4:3] actually
        # MDMCFG2[6:4] = MOD_FORMAT
        new_val = (current & 0x8F) | ((mod_val & 0x07) << 4)
        self._write_reg(REG_MDMCFG2, new_val)
        log.debug('CC1101 modulation set to %s (0x%02X)', mod, mod_val)

    def set_data_rate(self, baud: int) -> None:
        """Set symbol rate. Computes MDMCFG4[3:0] (CHANBW) + MDMCFG3 (DRATE_M)."""
        # DRATE = (256 + DRATE_M) * 2^DRATE_E * Fxosc / 2^28
        drate_e = max(0, min(15, int(math.log2(baud * (1 << 28) / XOSC_FREQ / 256))))
        drate_m = int(round(baud * (1 << 28) / XOSC_FREQ / (1 << drate_e) - 256))
        drate_m = max(0, min(255, drate_m))
        mdmcfg4 = (self._read_reg(REG_MDMCFG4) & 0xF0) | (drate_e & 0x0F)
        self._write_reg(REG_MDMCFG4, mdmcfg4)
        self._write_reg(REG_MDMCFG3, drate_m)
        actual = (256 + drate_m) * (1 << drate_e) * XOSC_FREQ / (1 << 28)
        log.debug('CC1101 data rate set to ~%d baud (DRATE_E=%d DRATE_M=%d actual=%.0f)',
                  baud, drate_e, drate_m, actual)

    def configure(self, freq_mhz: float, modulation: str, baud: int) -> None:
        self.strobe(SIDLE)
        self.set_frequency(freq_mhz)
        self.set_modulation(modulation)
        self.set_data_rate(baud)
        # Packet control: variable length, no CRC for raw capture
        self._write_reg(REG_PKTCTRL0, 0x00)  # fixed length, no whitening
        self._write_reg(REG_PKTCTRL1, 0x04)  # append RSSI+LQI
        # Default PA table for ASK/OOK
        if modulation.upper() == 'ASK_OOK':
            self._write_reg(REG_FREND0, 0x11)  # PA table index 1 for OOK "1"
        else:
            self._write_reg(REG_FREND0, 0x10)
        log.info('CC1101 configured: %.4f MHz %s %d baud', freq_mhz, modulation, baud)

    # -----------------------------------------------------------------------
    # TX / RX
    # -----------------------------------------------------------------------

    def transmit(self, data: bytes) -> bool:
        if len(data) > 60:
            log.error('Packet too large (%d bytes, max 60)', len(data))
            return False
        self.strobe(SIDLE)
        self.strobe(SFTX)
        self._write_reg(REG_PKTLEN, len(data))
        self._write_burst(REG_TXFIFO, list(data))
        self.strobe(STX)

        deadline = time.time() + 2.0
        while time.time() < deadline:
            marcstate = self._read_status(REG_MARCSTATE) & 0x1F
            if marcstate == 0x01:  # IDLE — TX complete
                log.debug('CC1101 TX complete (%d bytes)', len(data))
                return True
            time.sleep(0.001)

        self.strobe(SIDLE)
        log.error('CC1101 TX timeout')
        return False

    def receive(self, timeout_ms: int = 500) -> Optional[bytes]:
        self.strobe(SIDLE)
        self.strobe(SFRX)
        self.strobe(SRX)

        deadline = time.time() + timeout_ms / 1000.0
        while time.time() < deadline:
            rx_bytes = self._read_status(REG_RXBYTES)
            if rx_bytes & 0x80:
                log.warning('CC1101 RX FIFO overflow, flushing')
                self.strobe(SIDLE)
                self.strobe(SFRX)
                return None
            if rx_bytes > 0:
                length = rx_bytes - 2  # last 2 bytes are RSSI + LQI status
                if length <= 0:
                    time.sleep(0.001)
                    continue
                data = self._read_burst(REG_RXFIFO, length)
                self.strobe(SIDLE)
                log.debug('CC1101 RX: %d bytes', length)
                return bytes(data)
            time.sleep(0.001)

        self.strobe(SIDLE)
        return None

    def raw_capture(self, duration_s: float = 2.0) -> list[bytes]:
        """Capture raw packets for duration_s seconds."""
        packets = []
        deadline = time.time() + duration_s
        self.strobe(SIDLE)
        self.strobe(SFRX)
        self.strobe(SRX)

        while time.time() < deadline:
            rx_bytes = self._read_status(REG_RXBYTES)
            if rx_bytes & 0x80:
                self.strobe(SIDLE)
                self.strobe(SFRX)
                self.strobe(SRX)
                continue
            if rx_bytes > 2:
                length = rx_bytes - 2
                pkt = self._read_burst(REG_RXFIFO, length)
                packets.append(bytes(pkt))
                self.strobe(SFRX)
                self.strobe(SRX)
            time.sleep(0.005)

        self.strobe(SIDLE)
        log.info('CC1101 raw capture: %d packets in %.1fs', len(packets), duration_s)
        return packets
