"""
Camera capture using picamera2 (Pi Camera v2/v3) with OpenCV fallback.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Optional

log = logging.getLogger(__name__)


class HardwareNotAvailableError(Exception):
    pass


class CameraCapture:
    def __init__(self, config, display=None) -> None:
        self._config = config
        self._display = display
        self._backend: Optional[str] = None
        self._cv_cap = None
        self._init_hardware()

    def _init_hardware(self) -> None:
        try:
            from picamera2 import Picamera2  # noqa: F401
            self._backend = 'picamera2'
            log.info('picamera2 detected')
            return
        except Exception as e:
            log.warning('picamera2 not available: %s', e)

        try:
            import cv2
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                self._cv_cap = cap
                self._backend = 'opencv'
                log.info('OpenCV camera initialised (device 0)')
            else:
                cap.release()
        except ImportError:
            log.warning('opencv-python not installed')

    def available(self) -> bool:
        return self._backend is not None

    def capture(self, name: str = 'photo') -> dict:
        if not self.available():
            raise HardwareNotAvailableError(
                'No camera detected. Check ribbon cable or USB connection.'
            )
        dest = os.path.join(self._config.data_dir, 'camera')
        os.makedirs(dest, exist_ok=True)
        ts = int(time.time())
        filename = f'{name}_{ts}.jpg'
        path = os.path.join(dest, filename)

        if self._backend == 'picamera2':
            return self._capture_picamera2(path, filename)
        return self._capture_opencv(path, filename)

    def _capture_picamera2(self, path: str, filename: str) -> dict:
        from picamera2 import Picamera2
        cam = Picamera2()
        cfg = cam.create_still_configuration(main={'size': (1920, 1080)})
        cam.configure(cfg)
        cam.start()
        time.sleep(1.5)
        cam.capture_file(path)
        cam.stop()
        cam.close()
        log.info('picamera2 capture: %s', path)
        return {'path': path, 'filename': filename, 'backend': 'picamera2'}

    def _capture_opencv(self, path: str, filename: str) -> dict:
        import cv2
        ret, frame = self._cv_cap.read()
        if not ret:
            raise RuntimeError('Failed to grab frame from USB camera')
        cv2.imwrite(path, frame)
        log.info('OpenCV capture: %s', path)
        return {'path': path, 'filename': filename, 'backend': 'opencv'}

    def list_saved(self) -> list[str]:
        dest = os.path.join(self._config.data_dir, 'camera')
        if not os.path.isdir(dest):
            return []
        return sorted(
            (f for f in os.listdir(dest) if f.endswith('.jpg')),
            reverse=True,
        )[:20]

    def __del__(self) -> None:
        if self._cv_cap is not None:
            try:
                self._cv_cap.release()
            except Exception:
                pass
