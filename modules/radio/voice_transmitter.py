"""
Voice radio transmitter using rpitx.
Turns GPIO4 (pin 7) into a low-power FM/AM/SSB transmitter.
Attach a 20cm wire to GPIO4 as an antenna.

Modes:
  FM   - Wideband FM, ~75kHz deviation, tunable to any FM frequency
         Receive on any FM radio or phone app
  NFM  - Narrow FM, ~5kHz deviation (walkie-talkie style)
  AM   - Amplitude modulation
  SSB  - Single sideband (USB/LSB), used in amateur radio HF bands
  SSTV - Slow scan TV (sends images over radio, bonus feature)

Audio input:
  - USB microphone (recommended, plug & play)
  - I2S microphone (INMP441 / SPH0645 on I2S pins)
  - Audio file (.wav) playback over radio

Requires: rpitx installed via setup.sh
  git clone https://github.com/F5OEO/rpitx
  cd rpitx && ./install.sh

Legal note:
  Low-power transmission for personal/experimental use.
  Keep antenna short (20cm). Range ~10-50m.
  Do not transmit on occupied/emergency frequencies.
  In most countries, Part 15 / ISM rules allow low-power experimentation.

Reference: https://github.com/F5OEO/rpitx
"""
from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import threading
import time
from typing import Optional

log = logging.getLogger(__name__)

RPITX_PATH = '/usr/local/bin/rpitx'
PIFM_PATH  = '/usr/local/bin/pifm'          # fallback

# FM broadcast band: 87.5 – 108.0 MHz
FM_MIN_MHZ = 76.0
FM_MAX_MHZ = 108.0

# Preset frequencies (clear-ish gaps common in many areas)
PRESET_FREQUENCIES = {
    'FM 87.9':   87.9,
    'FM 88.1':   88.1,
    'FM 99.9':   99.9,
    'FM 107.7':  107.7,
    'Custom':    None,
}

MODES = {
    'FM':   'Wide FM (broadcast quality)',
    'NFM':  'Narrow FM (walkie-talkie)',
    'AM':   'Amplitude Modulation',
    'USB':  'Single Sideband (Upper)',
    'LSB':  'Single Sideband (Lower)',
}

# Sample rates expected by rpitx per mode
SAMPLE_RATES = {
    'FM':  48000,
    'NFM': 48000,
    'AM':  48000,
    'USB': 48000,
    'LSB': 48000,
}


class VoiceTransmitter:
    def __init__(self, config=None) -> None:
        self._config = config
        self._proc: Optional[subprocess.Popen] = None
        self._arecord_proc: Optional[subprocess.Popen] = None
        self._transmitting = False
        self._freq_mhz: float = 100.0
        self._mode: str = 'FM'

    # -----------------------------------------------------------------------
    # Availability checks
    # -----------------------------------------------------------------------

    def rpitx_available(self) -> bool:
        return os.path.exists(RPITX_PATH) or os.path.exists(PIFM_PATH)

    def mic_available(self) -> bool:
        """Check if a recording device is present."""
        try:
            result = subprocess.run(
                ['arecord', '-l'], capture_output=True, text=True, timeout=3
            )
            return 'card' in result.stdout.lower()
        except FileNotFoundError:
            return False

    def _get_rpitx(self) -> Optional[str]:
        for path in [RPITX_PATH, PIFM_PATH, 'rpitx']:
            if os.path.exists(path):
                return path
            try:
                result = subprocess.run(['which', path.split('/')[-1]],
                                        capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    return result.stdout.strip()
            except Exception:
                pass
        return None

    # -----------------------------------------------------------------------
    # Core transmit functions
    # -----------------------------------------------------------------------

    def transmit_live(self,
                      freq_mhz: float,
                      mode: str = 'FM',
                      mic_device: str = 'default') -> bool:
        """
        Live voice transmission: captures from microphone and pipes to rpitx.
        Runs until stop() is called.
        """
        rpitx = self._get_rpitx()
        if not rpitx:
            raise RuntimeError(
                'rpitx not found.\n'
                'Run: git clone https://github.com/F5OEO/rpitx && cd rpitx && sudo ./install.sh'
            )

        if self._transmitting:
            log.warning('Already transmitting, stop first')
            return False

        freq_hz = int(freq_mhz * 1_000_000)
        sample_rate = SAMPLE_RATES.get(mode.upper(), 48000)

        log.info('Starting live TX: %.3f MHz %s (mic: %s)', freq_mhz, mode, mic_device)

        # arecord pipes raw PCM audio to rpitx stdin
        arecord_cmd = [
            'arecord',
            '-D', mic_device,
            '-r', str(sample_rate),
            '-c', '1',               # mono
            '-f', 'S16_LE',          # 16-bit signed little-endian
            '-t', 'raw',             # raw PCM, no header
        ]

        rpitx_cmd = [
            'sudo', rpitx,
            '-m', mode.upper(),
            '-i', '-',               # read from stdin
            '-f', str(freq_hz),
            '-s', str(sample_rate),
        ]

        try:
            self._arecord_proc = subprocess.Popen(
                arecord_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            self._proc = subprocess.Popen(
                rpitx_cmd,
                stdin=self._arecord_proc.stdout,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._arecord_proc.stdout.close()
            self._transmitting = True
            self._freq_mhz = freq_mhz
            self._mode = mode
            log.info('TX started: %.3f MHz %s', freq_mhz, mode)
            return True
        except Exception as e:
            log.error('TX start failed: %s', e)
            self.stop()
            return False

    def transmit_file(self,
                      wav_path: str,
                      freq_mhz: float,
                      mode: str = 'FM') -> bool:
        """
        Transmit a .wav audio file over the air.
        Converts to raw PCM and pipes to rpitx.
        """
        rpitx = self._get_rpitx()
        if not rpitx:
            raise RuntimeError('rpitx not found')

        if not os.path.exists(wav_path):
            raise FileNotFoundError(f'Audio file not found: {wav_path}')

        freq_hz = int(freq_mhz * 1_000_000)
        sample_rate = SAMPLE_RATES.get(mode.upper(), 48000)

        log.info('Transmitting file: %s -> %.3f MHz %s', wav_path, freq_mhz, mode)

        # Convert wav to raw PCM with ffmpeg or sox
        converter = self._find_converter()
        if converter == 'ffmpeg':
            convert_cmd = [
                'ffmpeg', '-i', wav_path,
                '-ar', str(sample_rate),
                '-ac', '1',
                '-f', 's16le',
                '-'
            ]
        elif converter == 'sox':
            convert_cmd = [
                'sox', wav_path,
                '-r', str(sample_rate),
                '-c', '1',
                '-e', 'signed-integer',
                '-b', '16',
                '-t', 'raw',
                '-'
            ]
        else:
            # Try aplay raw fallback
            convert_cmd = ['cat', wav_path]

        rpitx_cmd = [
            'sudo', rpitx,
            '-m', mode.upper(),
            '-i', '-',
            '-f', str(freq_hz),
            '-s', str(sample_rate),
        ]

        try:
            convert_proc = subprocess.Popen(
                convert_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
            )
            self._proc = subprocess.Popen(
                rpitx_cmd,
                stdin=convert_proc.stdout,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            convert_proc.stdout.close()
            self._transmitting = True
            self._proc.wait()  # block until file finishes
            self._transmitting = False
            log.info('File transmission complete')
            return True
        except Exception as e:
            log.error('File TX failed: %s', e)
            self.stop()
            return False

    def record_then_transmit(self,
                              freq_mhz: float,
                              record_s: float = 5.0,
                              mode: str = 'FM',
                              mic_device: str = 'default') -> bool:
        """
        Record audio for record_s seconds, then immediately transmit it.
        Good for recording a message and broadcasting it.
        """
        tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        tmp.close()
        wav_path = tmp.name

        log.info('Recording %.1fs of audio...', record_s)
        record_cmd = [
            'arecord',
            '-D', mic_device,
            '-d', str(int(record_s)),
            '-r', '48000',
            '-c', '1',
            '-f', 'S16_LE',
            wav_path,
        ]
        try:
            subprocess.run(record_cmd, check=True, capture_output=True, timeout=record_s + 5)
            log.info('Recording saved: %s', wav_path)
        except subprocess.CalledProcessError as e:
            log.error('Recording failed: %s', e)
            return False

        result = self.transmit_file(wav_path, freq_mhz, mode)
        os.unlink(wav_path)
        return result

    # -----------------------------------------------------------------------
    # Stop
    # -----------------------------------------------------------------------

    def stop(self) -> None:
        if self._arecord_proc:
            try:
                self._arecord_proc.terminate()
                self._arecord_proc.wait(timeout=2)
            except Exception:
                pass
            self._arecord_proc = None

        if self._proc:
            try:
                subprocess.run(['sudo', 'kill', str(self._proc.pid)],
                               capture_output=True, timeout=2)
                self._proc.wait(timeout=2)
            except Exception:
                pass
            self._proc = None

        # Make sure GPIO4 stops transmitting
        try:
            subprocess.run(['sudo', 'pkill', '-f', 'rpitx'],
                           capture_output=True, timeout=2)
        except Exception:
            pass

        self._transmitting = False
        log.info('TX stopped')

    @property
    def is_transmitting(self) -> bool:
        return self._transmitting

    @property
    def current_freq(self) -> float:
        return self._freq_mhz

    @property
    def current_mode(self) -> str:
        return self._mode

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _find_converter(self) -> Optional[str]:
        for tool in ['ffmpeg', 'sox']:
            try:
                result = subprocess.run(['which', tool], capture_output=True,
                                        text=True, timeout=2)
                if result.returncode == 0:
                    return tool
            except Exception:
                pass
        return None

    def get_status(self) -> dict:
        return {
            'transmitting':  self._transmitting,
            'frequency_mhz': self._freq_mhz,
            'mode':          self._mode,
            'rpitx_found':   self.rpitx_available(),
            'mic_found':     self.mic_available(),
        }
