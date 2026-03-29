import logging
import os
from datetime import datetime


def setup_logging(debug: bool = False, log_dir: str = '/home/user/eamonnn/data') -> None:
    level = logging.DEBUG if debug else logging.INFO
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f'piflip_{datetime.now().strftime("%Y%m%d")}.log')

    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ]
    )
