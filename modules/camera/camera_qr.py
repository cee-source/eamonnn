"""
QR / barcode scanner using pyzbar + OpenCV or picamera2.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

log = logging.getLogger(__name__)


class QRScanner:
    def __init__(self) -> None:
        self._ok = False
        try:
            import pyzbar.pyzbar  # noqa: F401
            import cv2            # noqa: F401
            self._ok = True
        except ImportError as e:
            log.warning('QR scanning unavailable: %s', e)

    def available(self) -> bool:
        return self._ok

    def scan(self, timeout_s: float = 10.0) -> Optional[list[dict]]:
        if not self._ok:
            return None
        import cv2
        from pyzbar.pyzbar import decode

        # Try USB / V4L camera first
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            return self._scan_cap(cap, decode, timeout_s)

        # Fall back to picamera2
        try:
            return self._scan_picamera2(decode, timeout_s)
        except Exception as e:
            log.error('QR scan error: %s', e)
            return None

    def _scan_cap(self, cap, decode, timeout_s: float) -> Optional[list[dict]]:
        import cv2
        deadline = time.time() + timeout_s
        try:
            while time.time() < deadline:
                ret, frame = cap.read()
                if not ret:
                    break
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                codes = decode(gray)
                if codes:
                    return [
                        {'type': c.type, 'data': c.data.decode('utf-8', errors='replace')}
                        for c in codes
                    ]
                time.sleep(0.05)
        finally:
            cap.release()
        return None

    def _scan_picamera2(self, decode, timeout_s: float) -> Optional[list[dict]]:
        import cv2
        from picamera2 import Picamera2
        cam = Picamera2()
        cfg = cam.create_preview_configuration(
            main={'size': (640, 480), 'format': 'RGB888'}
        )
        cam.configure(cfg)
        cam.start()
        time.sleep(1.0)
        deadline = time.time() + timeout_s
        try:
            while time.time() < deadline:
                frame = cam.capture_array()
                gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
                codes = decode(gray)
                if codes:
                    return [
                        {'type': c.type, 'data': c.data.decode('utf-8', errors='replace')}
                        for c in codes
                    ]
                time.sleep(0.1)
        finally:
            cam.stop()
            cam.close()
        return None
