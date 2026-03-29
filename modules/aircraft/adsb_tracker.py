"""
ADS-B aircraft tracker using RTL-SDR + dump1090.
Decodes Mode S transponder signals at 1090 MHz.
Shows nearby aircraft: callsign, altitude, speed, heading, distance.

Requires:
  RTL-SDR USB dongle + sudo apt install dump1090-mutability
  OR: git clone https://github.com/antirez/dump1090 && make

dump1090 runs as a subprocess and outputs JSON we parse live.
"""
from __future__ import annotations

import json
import logging
import math
import os
import socket
import subprocess
import threading
import time
from typing import Optional

log = logging.getLogger(__name__)

DUMP1090_FREQ   = 1090_000_000   # 1090 MHz
DUMP1090_PORT   = 30003          # SBS BaseStation output port
DUMP1090_JSON   = '/run/dump1090-mutability/aircraft.json'

# Home position for distance calculation (set in config or auto-detected)
DEFAULT_LAT = 40.7128   # New York as fallback
DEFAULT_LON = -74.0060


class Aircraft:
    __slots__ = ('icao', 'callsign', 'altitude_ft', 'speed_kts',
                 'heading', 'lat', 'lon', 'vrate', 'last_seen', 'msgs')

    def __init__(self, icao: str) -> None:
        self.icao       = icao
        self.callsign   = ''
        self.altitude_ft: Optional[int] = None
        self.speed_kts: Optional[float] = None
        self.heading: Optional[float] = None
        self.lat: Optional[float] = None
        self.lon: Optional[float] = None
        self.vrate: Optional[int] = None   # ft/min vertical rate
        self.last_seen  = time.time()
        self.msgs       = 0

    def distance_nm(self, home_lat: float, home_lon: float) -> Optional[float]:
        if self.lat is None or self.lon is None:
            return None
        R = 3440.065  # nautical miles
        dlat = math.radians(self.lat - home_lat)
        dlon = math.radians(self.lon - home_lon)
        a = (math.sin(dlat/2)**2 +
             math.cos(math.radians(home_lat)) *
             math.cos(math.radians(self.lat)) *
             math.sin(dlon/2)**2)
        return R * 2 * math.asin(math.sqrt(a))

    def summary(self, home_lat: float, home_lon: float) -> str:
        cs   = (self.callsign or self.icao).strip().ljust(8)
        alt  = f'{self.altitude_ft:5d}ft' if self.altitude_ft else '    ???'
        spd  = f'{int(self.speed_kts):3d}kt' if self.speed_kts else ' ???'
        dist = self.distance_nm(home_lat, home_lon)
        dst  = f'{dist:5.1f}nm' if dist is not None else '  ???nm'
        hdg  = f'{int(self.heading):3d}°' if self.heading else '???'
        return f'{cs} {alt} {spd} {dst} {hdg}'


class ADSBTracker:
    def __init__(self, config=None) -> None:
        self._config   = config
        self._aircraft: dict[str, Aircraft] = {}
        self._lock     = threading.Lock()
        self._proc: Optional[subprocess.Popen] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._running  = False
        self._home_lat = DEFAULT_LAT
        self._home_lon = DEFAULT_LON
        if config:
            self._home_lat = config.getfloat('location', 'lat', fallback=DEFAULT_LAT)
            self._home_lon = config.getfloat('location', 'lon', fallback=DEFAULT_LON)

    # -----------------------------------------------------------------------
    # dump1090 management
    # -----------------------------------------------------------------------

    def dump1090_available(self) -> bool:
        for cmd in ['dump1090', 'dump1090-mutability', 'dump1090-fa']:
            try:
                r = subprocess.run(['which', cmd], capture_output=True, timeout=2)
                if r.returncode == 0:
                    return True
            except Exception:
                pass
        return False

    def _find_dump1090(self) -> Optional[str]:
        for cmd in ['dump1090-mutability', 'dump1090-fa', 'dump1090']:
            try:
                r = subprocess.run(['which', cmd], capture_output=True,
                                   text=True, timeout=2)
                if r.returncode == 0:
                    return r.stdout.strip()
            except Exception:
                pass
        return None

    def start(self) -> bool:
        if self._running:
            return True

        dump1090 = self._find_dump1090()
        if not dump1090:
            log.error('dump1090 not found')
            return False

        cmd = [dump1090, '--net', '--quiet']
        try:
            self._proc = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            time.sleep(1.5)   # let dump1090 initialise
            self._running = True
            self._reader_thread = threading.Thread(
                target=self._read_sbs, daemon=True
            )
            self._reader_thread.start()
            log.info('ADS-B tracker started')
            return True
        except Exception as e:
            log.error('Failed to start dump1090: %s', e)
            return False

    def stop(self) -> None:
        self._running = False
        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=3)
            except Exception:
                pass
            self._proc = None
        log.info('ADS-B tracker stopped')

    # -----------------------------------------------------------------------
    # SBS BaseStation format reader (port 30003)
    # -----------------------------------------------------------------------

    def _read_sbs(self) -> None:
        """Connect to dump1090's SBS output and parse aircraft messages."""
        while self._running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect(('127.0.0.1', DUMP1090_PORT))
                log.debug('Connected to dump1090 SBS port')

                buf = ''
                while self._running:
                    try:
                        data = sock.recv(1024).decode('ascii', errors='ignore')
                        if not data:
                            break
                        buf += data
                        while '\n' in buf:
                            line, buf = buf.split('\n', 1)
                            self._parse_sbs(line.strip())
                    except socket.timeout:
                        self._expire_aircraft()
                        continue
                sock.close()
            except ConnectionRefusedError:
                log.debug('dump1090 not ready yet, retrying...')
                time.sleep(2)
            except Exception as e:
                log.debug('SBS reader error: %s', e)
                time.sleep(2)

    def _parse_sbs(self, line: str) -> None:
        """
        Parse SBS BaseStation format:
        MSG,<type>,<session>,<aircraft>,<icao>,<flight>,<date>,<time>,
            <date2>,<time2>,<callsign>,<alt>,<speed>,<track>,<lat>,<lon>,
            <vrate>,<squawk>,<alert>,<emergency>,<spi>,<onground>
        """
        if not line.startswith('MSG'):
            return
        parts = line.split(',')
        if len(parts) < 22:
            return

        icao = parts[4].strip().upper()
        if not icao:
            return

        with self._lock:
            if icao not in self._aircraft:
                self._aircraft[icao] = Aircraft(icao)
            ac = self._aircraft[icao]
            ac.last_seen = time.time()
            ac.msgs += 1

            msg_type = parts[1].strip()

            if msg_type == '1':   # callsign
                ac.callsign = parts[10].strip()
            elif msg_type in ('2', '3', '4'):
                if parts[11]: ac.altitude_ft = int(parts[11])
                if parts[12]: ac.speed_kts   = float(parts[12])
                if parts[13]: ac.heading     = float(parts[13])
                if parts[14]: ac.lat         = float(parts[14])
                if parts[15]: ac.lon         = float(parts[15])
                if parts[16]: ac.vrate       = int(parts[16])

    def _expire_aircraft(self, max_age_s: float = 60.0) -> None:
        now = time.time()
        with self._lock:
            expired = [icao for icao, ac in self._aircraft.items()
                       if now - ac.last_seen > max_age_s]
            for icao in expired:
                del self._aircraft[icao]

    # -----------------------------------------------------------------------
    # Query
    # -----------------------------------------------------------------------

    def get_aircraft(self, max_distance_nm: float = 200.0) -> list[Aircraft]:
        """Return list of aircraft sorted by distance."""
        self._expire_aircraft()
        with self._lock:
            acs = list(self._aircraft.values())

        result = []
        for ac in acs:
            dist = ac.distance_nm(self._home_lat, self._home_lon)
            if dist is None or dist <= max_distance_nm:
                result.append(ac)

        result.sort(key=lambda a: (
            a.distance_nm(self._home_lat, self._home_lon) or 9999
        ))
        return result

    def get_count(self) -> int:
        with self._lock:
            return len(self._aircraft)

    def set_home(self, lat: float, lon: float) -> None:
        self._home_lat = lat
        self._home_lon = lon

    @property
    def is_running(self) -> bool:
        return self._running
