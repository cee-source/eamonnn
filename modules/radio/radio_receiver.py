"""
FM/AM radio receiver using RTL-SDR dongle.
Requires: RTL-SDR USB dongle (RTL2832U chip, ~£10 on Amazon)
          rtl-sdr package: sudo apt install rtl-sdr

Audio output options (Pi Zero 2W has no headphone jack):
  - USB audio adapter (~£3) — plug headphones/speaker into this
  - I2S DAC/amp board (MAX98357A) — better quality
  - Bluetooth speaker — pair via bluetoothctl
  - PWM audio on GPIO18 (low quality, no extra hardware)

Pipeline: RTL-SDR dongle -> rtl_fm -> aplay -> speaker/headphones
"""
from __future__ import annotations

import logging
import subprocess
import time
from typing import Optional

log = logging.getLogger(__name__)

# FM broadcast presets
FM_PRESETS = {
    'BBC Radio 1':    87.7,
    'BBC Radio 2':    88.0,
    'BBC Radio 4':    93.5,
    'Custom':         None,
}

RECEIVE_MODES = {
    'WFM':  'Wide FM (broadcast radio)',
    'FM':   'Narrow FM (walkie-talkies)',
    'AM':   'AM medium wave',
    'USB':  'Single sideband upper',
    'LSB':  'Single sideband lower',
    'RAW':  'Raw IQ data',
}

# Audio output devices
AUDIO_DEVICES = {
    'default':    'System default',
    'plughw:1,0': 'USB audio adapter',
    'plughw:0,0': 'PWM (GPIO18, low quality)',
}


class RadioReceiver:
    def __init__(self, config=None) -> None:
        self._config = config
        self._proc_rtl: Optional[subprocess.Popen] = None
        self._proc_play: Optional[subprocess.Popen] = None
        self._receiving = False
        self._freq_mhz: float = 100.0
        self._mode: str = 'WFM'
        self._volume: int = 80    # 0-100
        self._squelch: int = 0    # 0 = off, higher = cut weak signals

    # -----------------------------------------------------------------------
    # Hardware checks
    # -----------------------------------------------------------------------

    def rtlsdr_available(self) -> bool:
        try:
            result = subprocess.run(
                ['rtl_test', '-t'],
                capture_output=True, text=True, timeout=3
            )
            return 'Found' in result.stdout or result.returncode == 0
        except FileNotFoundError:
            return False

    def audio_output_available(self) -> bool:
        try:
            result = subprocess.run(
                ['aplay', '-l'], capture_output=True, text=True, timeout=3
            )
            return 'card' in result.stdout.lower()
        except FileNotFoundError:
            return False

    # -----------------------------------------------------------------------
    # Receive
    # -----------------------------------------------------------------------

    def start(self,
              freq_mhz: float,
              mode: str = 'WFM',
              audio_device: str = 'default',
              gain: int = 40,
              squelch: int = 0) -> bool:
        """
        Start receiving radio.
        Pipes rtl_fm -> aplay for live audio output.
        """
        if self._receiving:
            log.warning('Already receiving, stop first')
            return False

        freq_hz = int(freq_mhz * 1_000_000)
        sample_rate = 200_000 if mode == 'WFM' else 24_000
        resample_rate = 48_000

        rtl_cmd = [
            'rtl_fm',
            '-f', str(freq_hz),
            '-M', mode.lower(),
            '-s', str(sample_rate),
            '-r', str(resample_rate),
            '-g', str(gain),
        ]
        if squelch > 0:
            rtl_cmd += ['-l', str(squelch)]

        aplay_cmd = [
            'aplay',
            '-D', audio_device,
            '-r', str(resample_rate),
            '-f', 'S16_LE',
            '-c', '1',
            '-t', 'raw',
        ]

        log.info('Starting RX: %.3f MHz %s -> %s', freq_mhz, mode, audio_device)

        try:
            self._proc_rtl = subprocess.Popen(
                rtl_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            self._proc_play = subprocess.Popen(
                aplay_cmd,
                stdin=self._proc_rtl.stdout,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._proc_rtl.stdout.close()
            self._receiving = True
            self._freq_mhz = freq_mhz
            self._mode = mode
            log.info('RX started: %.3f MHz %s', freq_mhz, mode)
            return True
        except FileNotFoundError:
            log.error('rtl_fm or aplay not found')
            self.stop()
            return False
        except Exception as e:
            log.error('RX start failed: %s', e)
            self.stop()
            return False

    def tune(self, freq_mhz: float) -> bool:
        """Change frequency while receiving — restarts the pipeline."""
        if not self._receiving:
            return False
        mode = self._mode
        self.stop()
        time.sleep(0.3)
        return self.start(freq_mhz, mode=mode)

    def stop(self) -> None:
        for proc in [self._proc_play, self._proc_rtl]:
            if proc:
                try:
                    proc.terminate()
                    proc.wait(timeout=2)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass

        self._proc_rtl = None
        self._proc_play = None
        self._receiving = False
        log.info('RX stopped')

    # -----------------------------------------------------------------------
    # FM scan — find active stations
    # -----------------------------------------------------------------------

    def scan_fm_band(self,
                     start_mhz: float = 87.5,
                     end_mhz: float = 108.0,
                     step_mhz: float = 0.1,
                     dwell_s: float = 0.3,
                     progress_cb=None) -> list[dict]:
        """
        Scan the FM band and return frequencies with strong signals.
        Uses rtl_power for signal strength measurement.
        """
        log.info('Scanning FM band %.1f–%.1f MHz', start_mhz, end_mhz)

        start_hz = int(start_mhz * 1e6)
        end_hz   = int(end_mhz   * 1e6)
        step_hz  = int(step_mhz  * 1e6)

        cmd = [
            'rtl_power',
            '-f', f'{start_hz}:{end_hz}:{step_hz}',
            '-i', str(dwell_s),
            '-1',   # one sweep only
            '-',    # output to stdout
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except FileNotFoundError:
            log.error('rtl_power not found')
            return []
        except subprocess.TimeoutExpired:
            log.error('FM scan timed out')
            return []

        stations = []
        for line in result.stdout.splitlines():
            parts = line.strip().split(',')
            if len(parts) < 6:
                continue
            try:
                freq_start = float(parts[2])
                freq_step  = float(parts[4])
                powers     = [float(x) for x in parts[6:]]
                for i, power in enumerate(powers):
                    freq = (freq_start + i * freq_step) / 1e6
                    if power > -40:  # signal threshold dBm
                        stations.append({
                            'freq_mhz': round(freq, 1),
                            'power_dbm': round(power, 1),
                        })
            except (ValueError, IndexError):
                continue

        # Sort by signal strength
        stations.sort(key=lambda s: s['power_dbm'], reverse=True)
        log.info('FM scan found %d stations', len(stations))
        return stations

    # -----------------------------------------------------------------------
    # Properties
    # -----------------------------------------------------------------------

    @property
    def is_receiving(self) -> bool:
        return self._receiving

    @property
    def current_freq(self) -> float:
        return self._freq_mhz

    @property
    def current_mode(self) -> str:
        return self._mode

    def get_status(self) -> dict:
        return {
            'receiving':     self._receiving,
            'frequency_mhz': self._freq_mhz,
            'mode':          self._mode,
            'rtlsdr_found':  self.rtlsdr_available(),
            'audio_found':   self.audio_output_available(),
        }
