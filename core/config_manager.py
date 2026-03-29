import configparser
import json
import os
from datetime import datetime
from typing import Any


class ConfigManager:
    def __init__(self, config_path: str = '/home/user/eamonnn/config.ini') -> None:
        self._path = config_path
        self._cfg = configparser.ConfigParser()
        self._cfg.read(config_path)

    def get(self, section: str, key: str, fallback: Any = None) -> str:
        return self._cfg.get(section, key, fallback=fallback)

    def getint(self, section: str, key: str, fallback: int = 0) -> int:
        return self._cfg.getint(section, key, fallback=fallback)

    def getfloat(self, section: str, key: str, fallback: float = 0.0) -> float:
        return self._cfg.getfloat(section, key, fallback=fallback)

    @property
    def data_dir(self) -> str:
        return self.get('storage', 'data_dir', fallback='/home/user/eamonnn/data')

    def save_capture(self, category: str, data: dict, prefix: str = '') -> str:
        dest = os.path.join(self.data_dir, category)
        os.makedirs(dest, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        name = f'{prefix}_{ts}.json' if prefix else f'{ts}.json'
        path = os.path.join(dest, name)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        return path

    def load_captures(self, category: str) -> list[dict]:
        dest = os.path.join(self.data_dir, category)
        if not os.path.isdir(dest):
            return []
        results = []
        for fname in sorted(os.listdir(dest)):
            if fname.endswith('.json'):
                with open(os.path.join(dest, fname)) as f:
                    try:
                        results.append({'filename': fname, 'data': json.load(f)})
                    except json.JSONDecodeError:
                        pass
        return results
